"""
api/routes/inbox.py

Rotas REST para a UniBox LinkedIn — conversas, mensagens, sugestões LLM.

A UniBox é um proxy enriquecido sobre a Unipile Chat API.
Para cada conversa, tentamos vincular o participante a um lead existente.

Endpoints:
  GET    /inbox/conversations                      — listar conversas
  GET    /inbox/conversations/{chat_id}/messages    — histórico de mensagens
  POST   /inbox/conversations/{chat_id}/send        — enviar texto
  POST   /inbox/conversations/{chat_id}/send-voice  — enviar voice note
  POST   /inbox/conversations/{chat_id}/suggest     — sugerir resposta LLM
  GET    /inbox/conversations/{chat_id}/lead        — dados do lead vinculado
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_effective_tenant_id, get_llm_registry, get_session_flexible
from core.config import settings
from integrations.llm import LLMRegistry
from integrations.unipile_client import unipile_client
from models.enums import Channel, InteractionDirection, LeadSource, LeadStatus, ManualTaskStatus
from models.interaction import Interaction
from models.lead import Lead
from models.manual_task import ManualTask
from schemas.inbox import (
    ChatAttendeeSchema,
    ChatMessageSchema,
    ChatMessagesResponse,
    ConversationLeadResponse,
    ConversationListResponse,
    ConversationSchema,
    QuickCreateLeadRequest,
    SendMessageRequest,
    SuggestReplyRequest,
    SuggestReplyResponse,
)
from services.conversation_assistant import ConversationAssistant

logger = structlog.get_logger()

router = APIRouter(prefix="/inbox", tags=["Inbox"])


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
) -> ConversationListResponse:
    """Lista conversas LinkedIn com enriquecimento de dados do lead."""
    account_id = settings.UNIPILE_ACCOUNT_ID_LINKEDIN or ""
    if not account_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Conta LinkedIn não configurada",
        )

    result = await unipile_client.list_chats(
        account_id=account_id,
        cursor=cursor,
        limit=limit,
    )

    conversations: list[ConversationSchema] = []
    for chat in result["items"]:
        # Tenta vincular attendee a lead no sistema
        lead_info = await _find_lead_for_chat(chat.attendees, tenant_id, db)

        conversations.append(
            ConversationSchema(
                chat_id=chat.chat_id,
                attendees=[
                    ChatAttendeeSchema(
                        id=a.id,
                        name=a.name,
                        profile_url=a.profile_url,
                        profile_picture_url=a.profile_picture_url,
                    )
                    for a in chat.attendees
                ],
                last_message_text=chat.last_message_text,
                last_message_at=chat.last_message_at,
                unread_count=chat.unread_count,
                has_lead=lead_info.get("has_lead", False),
                lead_id=lead_info.get("lead_id"),
                lead_name=lead_info.get("lead_name"),
                lead_company=lead_info.get("lead_company"),
                lead_status=lead_info.get("lead_status"),
            )
        )

    return ConversationListResponse(
        items=conversations,
        cursor=result.get("cursor"),
    )


@router.get("/conversations/{chat_id}/messages", response_model=ChatMessagesResponse)
async def get_chat_messages(
    chat_id: str,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=30, ge=1, le=100),
) -> ChatMessagesResponse:
    """Obtém mensagens de um chat específico."""
    result = await unipile_client.get_chat_messages(
        chat_id=chat_id,
        cursor=cursor,
        limit=limit,
    )

    messages = [
        ChatMessageSchema(
            id=msg.id,
            sender_id=msg.sender_id,
            sender_name=msg.sender_name,
            text=msg.text,
            timestamp=msg.timestamp,
            is_own=msg.is_own,
            attachments=msg.attachments,
        )
        for msg in result["items"]
    ]

    return ChatMessagesResponse(items=messages, cursor=result.get("cursor"))


@router.post("/conversations/{chat_id}/send", response_model=ChatMessageSchema)
async def send_message(
    chat_id: str,
    body: SendMessageRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ChatMessageSchema:
    """Envia mensagem texto em conversa existente."""
    # Obtém detalhes do chat para pegar o attendee
    chat = await unipile_client.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat não encontrado")

    account_id = chat.account_id or settings.UNIPILE_ACCOUNT_ID_LINKEDIN or ""

    # Envia via Unipile
    attendee_ids = [a.id for a in chat.attendees]
    if not attendee_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sem destinatário")

    result = await unipile_client.send_linkedin_dm(
        account_id=account_id,
        linkedin_profile_id=attendee_ids[0],
        message=body.text,
    )

    # Registra Interaction outbound se lead existe
    lead = await _find_lead_by_attendees(chat.attendees, tenant_id, db)
    if lead:
        interaction = Interaction(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            lead_id=lead.id,
            channel=Channel.LINKEDIN_DM,
            direction=InteractionDirection.OUTBOUND,
            content_text=body.text,
            unipile_message_id=result.message_id,
            created_at=datetime.now(tz=timezone.utc),
        )
        db.add(interaction)
        await db.commit()

    return ChatMessageSchema(
        id=result.message_id,
        sender_id="me",
        sender_name="Eu",
        text=body.text,
        timestamp=datetime.now(tz=timezone.utc).isoformat(),
        is_own=True,
    )


@router.post("/conversations/{chat_id}/send-voice")
async def send_voice(
    chat_id: str,
    audio: UploadFile = File(...),
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> dict:
    """Envia voice note (áudio gravado pelo microfone ou TTS)."""
    chat = await unipile_client.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat não encontrado")

    account_id = chat.account_id or settings.UNIPILE_ACCOUNT_ID_LINKEDIN or ""
    attendee_ids = [a.id for a in chat.attendees]
    if not attendee_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sem destinatário")

    # Salva áudio temporariamente no Redis
    from core.redis_client import redis_client
    audio_bytes = await audio.read()
    audio_key = f"voice:inbox:{chat_id}:{uuid.uuid4()}"
    await redis_client.set(audio_key, audio_bytes, ex=3600)

    audio_url = f"/api/audio/temp/{audio_key}"

    result = await unipile_client.send_linkedin_voice_note(
        account_id=account_id,
        linkedin_profile_id=attendee_ids[0],
        audio_url=audio_url,
    )

    # Registra Interaction outbound se lead existe
    lead = await _find_lead_by_attendees(chat.attendees, tenant_id, db)
    if lead:
        interaction = Interaction(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            lead_id=lead.id,
            channel=Channel.LINKEDIN_DM,
            direction=InteractionDirection.OUTBOUND,
            content_audio_url=audio_url,
            unipile_message_id=result.message_id,
            created_at=datetime.now(tz=timezone.utc),
        )
        db.add(interaction)
        await db.commit()

    return {"message_id": result.message_id, "status": "sent"}


@router.post("/conversations/{chat_id}/suggest", response_model=SuggestReplyResponse)
async def suggest_reply(
    chat_id: str,
    body: SuggestReplyRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
    registry: LLMRegistry = Depends(get_llm_registry),
) -> SuggestReplyResponse:
    """Gera sugestão de resposta via LLM com base no histórico e dados do lead."""
    # Busca mensagens recentes do chat
    messages_result = await unipile_client.get_chat_messages(
        chat_id=chat_id,
        limit=15,
    )

    chat_messages = [
        {
            "sender_name": msg.sender_name,
            "text": msg.text,
            "is_own": msg.is_own,
        }
        for msg in messages_result["items"]
    ]

    # Busca dados do lead se existir
    chat = await unipile_client.get_chat(chat_id)
    lead_data: dict | None = None
    if chat:
        lead = await _find_lead_by_attendees(chat.attendees, tenant_id, db)
        if lead:
            lead_data = {
                "name": lead.name,
                "company": lead.company,
                "job_title": lead.job_title,
                "segment": lead.segment,
                "industry": lead.industry,
            }

    assistant = ConversationAssistant(registry)
    suggested = await assistant.suggest_reply(
        chat_messages=chat_messages,
        lead_data=lead_data,
        tone=body.tone,
    )

    return SuggestReplyResponse(suggested_text=suggested, tone=body.tone)


@router.get("/conversations/{chat_id}/lead", response_model=ConversationLeadResponse)
async def get_conversation_lead(
    chat_id: str,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ConversationLeadResponse:
    """Retorna dados do lead vinculado à conversa (se existir) + dados do contato Unipile."""
    chat = await unipile_client.get_chat(chat_id)
    if not chat:
        return ConversationLeadResponse(has_lead=False)

    # Sempre extraímos dados do attendee (mesmo sem lead no sistema)
    first_att = chat.attendees[0] if chat.attendees else None
    attendee_name = first_att.name if first_att else None
    attendee_profile_url = first_att.profile_url if first_att else None
    attendee_profile_picture_url = first_att.profile_picture_url if first_att else None
    attendee_id = first_att.id if first_att else None

    lead = await _find_lead_by_attendees(chat.attendees, tenant_id, db)
    if not lead:
        return ConversationLeadResponse(
            has_lead=False,
            attendee_name=attendee_name,
            attendee_profile_url=attendee_profile_url,
            attendee_profile_picture_url=attendee_profile_picture_url,
            attendee_id=attendee_id,
        )

    # Conta tarefas pendentes do lead
    pending_count_result = await db.execute(
        select(func.count())
        .where(ManualTask.lead_id == lead.id)
        .where(ManualTask.status.in_([
            ManualTaskStatus.PENDING,
            ManualTaskStatus.CONTENT_GENERATED,
        ]))
    )
    pending_count = pending_count_result.scalar() or 0

    return ConversationLeadResponse(
        has_lead=True,
        lead_id=lead.id,
        name=lead.name,
        company=lead.company,
        job_title=lead.job_title,
        linkedin_url=lead.linkedin_url,
        email_corporate=lead.email_corporate,
        email_personal=lead.email_personal,
        phone=lead.phone,
        city=lead.city,
        segment=lead.segment,
        industry=lead.industry,
        score=lead.score,
        status=lead.status,
        notes=lead.notes,
        pending_tasks_count=pending_count,
        attendee_name=attendee_name,
        attendee_profile_url=attendee_profile_url,
        attendee_profile_picture_url=attendee_profile_picture_url,
        attendee_id=attendee_id,
    )


@router.post("/conversations/{chat_id}/create-lead", response_model=ConversationLeadResponse)
async def quick_create_lead(
    chat_id: str,
    body: QuickCreateLeadRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ConversationLeadResponse:
    """Cria lead rápido a partir de contato do inbox."""
    # Verifica se já existe lead vinculado
    chat = await unipile_client.get_chat(chat_id)
    if chat:
        existing = await _find_lead_by_attendees(chat.attendees, tenant_id, db)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Já existe um lead vinculado a este contato",
            )

    lead = Lead(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name=body.name,
        linkedin_url=body.linkedin_url,
        linkedin_profile_id=body.linkedin_profile_id,
        company=body.company,
        job_title=body.job_title,
        source=LeadSource.MANUAL,
        status=LeadStatus.RAW,
    )
    db.add(lead)
    await db.commit()
    await db.refresh(lead)

    logger.info(
        "inbox.lead_created",
        lead_id=str(lead.id),
        chat_id=chat_id,
        tenant_id=str(tenant_id),
    )

    first_att = chat.attendees[0] if chat and chat.attendees else None
    return ConversationLeadResponse(
        has_lead=True,
        lead_id=lead.id,
        name=lead.name,
        company=lead.company,
        job_title=lead.job_title,
        linkedin_url=lead.linkedin_url,
        status=lead.status,
        pending_tasks_count=0,
        attendee_name=first_att.name if first_att else None,
        attendee_profile_url=first_att.profile_url if first_att else None,
        attendee_profile_picture_url=first_att.profile_picture_url if first_att else None,
        attendee_id=first_att.id if first_att else None,
    )


@router.post("/conversations/{chat_id}/send-crm")
async def send_to_crm(
    chat_id: str,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> dict:
    """Envia contato/lead para o CRM (Pipedrive)."""
    from integrations.pipedrive_client import PipedriveClient

    if not settings.PIPEDRIVE_API_TOKEN or not settings.PIPEDRIVE_DOMAIN:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Pipedrive não configurado",
        )

    pipedrive = PipedriveClient(settings)

    chat = await unipile_client.get_chat(chat_id)
    if not chat or not chat.attendees:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat não encontrado",
        )

    # Tenta encontrar lead vinculado para dados mais ricos
    lead = await _find_lead_by_attendees(chat.attendees, tenant_id, db)

    name = lead.name if lead else (chat.attendees[0].name or "Contato LinkedIn")
    email = (lead.email_corporate or lead.email_personal) if lead else None

    person_id = await pipedrive.find_or_create_person(
        name=name,
        email=email,
        linkedin_url=lead.linkedin_url if lead else chat.attendees[0].profile_url,
    )

    if not person_id:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao criar contato no Pipedrive",
        )

    deal_id = await pipedrive.create_deal(
        title=f"Prospecção - {name}",
        person_id=person_id,
        stage_id=settings.PIPEDRIVE_STAGE_INTEREST if hasattr(settings, "PIPEDRIVE_STAGE_INTEREST") else None,
    )

    logger.info(
        "inbox.sent_to_crm",
        person_id=person_id,
        deal_id=deal_id,
        chat_id=chat_id,
        tenant_id=str(tenant_id),
    )

    return {
        "person_id": person_id,
        "deal_id": deal_id,
        "status": "sent",
    }


# ── Helpers ───────────────────────────────────────────────────────────

async def _find_lead_for_chat(
    attendees: list,
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> dict:
    """Tenta vincular um attendee do chat a um lead no sistema."""
    lead = await _find_lead_by_attendees(attendees, tenant_id, db)
    if lead:
        return {
            "has_lead": True,
            "lead_id": lead.id,
            "lead_name": lead.name,
            "lead_company": lead.company,
            "lead_status": lead.status,
        }
    return {"has_lead": False}


async def _find_lead_by_attendees(
    attendees: list,
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> Lead | None:
    """Busca lead pelo profile_id ou profile_url dos attendees."""
    for att in attendees:
        att_id = att.id if hasattr(att, "id") else att.get("id", "")
        if att_id:
            result = await db.execute(
                select(Lead).where(
                    Lead.tenant_id == tenant_id,
                    Lead.linkedin_profile_id == att_id,
                )
            )
            lead = result.scalar_one_or_none()
            if lead:
                return lead

        # Tenta por URL do perfil
        att_url = att.profile_url if hasattr(att, "profile_url") else att.get("profile_url", "")
        if att_url:
            result = await db.execute(
                select(Lead).where(
                    Lead.tenant_id == tenant_id,
                    Lead.linkedin_url == att_url,
                )
            )
            lead = result.scalar_one_or_none()
            if lead:
                return lead

    return None
