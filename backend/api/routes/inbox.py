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
from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_effective_tenant_id, get_llm_registry, get_session_flexible
from core.config import settings
from integrations.llm import LLMRegistry
from integrations.s3_client import S3Client
from integrations.unipile_client import unipile_client
from models.enums import Channel, InteractionDirection, LeadSource, LeadStatus, ManualTaskStatus, StepStatus
from models.interaction import Interaction
from models.lead import Lead
from models.lead_tag import LeadTag
from models.manual_task import ManualTask
from models.cadence_step import CadenceStep
from models.cadence import Cadence
from schemas.inbox import (
    AddReactionRequest,
    AddTagRequest,
    CadenceHistoryItem,
    CadenceHistoryResponse,
    ChatAttendeeSchema,
    ChatMessageSchema,
    ChatMessagesResponse,
    ConversationLeadResponse,
    ConversationListResponse,
    ConversationSchema,
    LeadTagSchema,
    QuickCreateLeadRequest,
    RecentActivityItem,
    RecentActivityResponse,
    SendMessageRequest,
    SuggestReplyRequest,
    SuggestReplyResponse,
)
from services.conversation_assistant import ConversationAssistant

logger = structlog.get_logger()

router = APIRouter(prefix="/inbox", tags=["Inbox"])


@router.post("/sync")
async def sync_inbox(
    _tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
) -> dict:
    """Dispara resync da conta LinkedIn na Unipile e invalida caches."""
    account_id = settings.UNIPILE_ACCOUNT_ID_LINKEDIN or ""
    if not account_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Conta LinkedIn não configurada",
        )
    ok = await unipile_client.sync_account(account_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao sincronizar conta LinkedIn",
        )
    return {"status": "sync_started"}


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    filter: str = Query(default="all", description="all | unread"),
    search: str = Query(default="", description="Buscar por nome do contato"),
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
        unread_only=(filter == "unread"),
    )

    search_lower = search.strip().lower()

    conversations: list[ConversationSchema] = []
    for chat in result["items"]:
        # Tenta vincular attendee a lead no sistema
        lead_info = await _find_lead_for_chat(chat.attendees, tenant_id, db)

        # Client-side search filter by attendee name or lead name
        if search_lower:
            name_match = False
            for a in chat.attendees:
                if search_lower in (a.name or "").lower():
                    name_match = True
                    break
            if lead_info.get("lead_name") and search_lower in lead_info["lead_name"].lower():
                name_match = True
            if not name_match:
                continue

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

    # Faz upload para S3 para gerar URL pública acessível pela Unipile
    audio_bytes = await audio.read()
    s3 = S3Client()
    filename = audio.filename or "voice.mp3"
    _key, audio_url = s3.upload_audio(
        data=audio_bytes,
        tenant_id=str(tenant_id),
        filename=filename,
        content_type=audio.content_type or "audio/mpeg",
    )

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


@router.post("/conversations/{chat_id}/send-attachments")
async def send_attachments(
    chat_id: str,
    text: str = "",
    files: list[UploadFile] = File(...),
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> dict:
    """Envia mensagem com anexos (imagens, documentos, etc.)."""
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nenhum arquivo enviado")

    chat = await unipile_client.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat não encontrado")

    account_id = chat.account_id or settings.UNIPILE_ACCOUNT_ID_LINKEDIN or ""
    attendee_ids = [a.id for a in chat.attendees]
    if not attendee_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sem destinatário")

    attachments: list[tuple[str, bytes, str]] = []
    for f in files:
        file_bytes = await f.read()
        attachments.append((f.filename or "file", file_bytes, f.content_type or "application/octet-stream"))

    result = await unipile_client.send_linkedin_dm_with_attachments(
        account_id=account_id,
        linkedin_profile_id=attendee_ids[0],
        message=text,
        attachments=attachments,
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
            content_text=text or None,
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
    attendee_headline = first_att.headline if first_att else None
    attendee_location = first_att.location if first_att else None
    attendee_email = first_att.email if first_att else None
    attendee_connections_count = first_att.connections_count if first_att else None
    attendee_shared_connections_count = first_att.shared_connections_count if first_att else None
    attendee_is_premium = first_att.is_premium if first_att else False
    attendee_websites = list(first_att.websites) if first_att else []

    lead = await _find_lead_by_attendees(chat.attendees, tenant_id, db)
    if not lead:
        return ConversationLeadResponse(
            has_lead=False,
            attendee_name=attendee_name,
            attendee_profile_url=attendee_profile_url,
            attendee_profile_picture_url=attendee_profile_picture_url,
            attendee_id=attendee_id,
            attendee_headline=attendee_headline,
            attendee_location=attendee_location,
            attendee_email=attendee_email,
            attendee_connections_count=attendee_connections_count,
            attendee_shared_connections_count=attendee_shared_connections_count,
            attendee_is_premium=attendee_is_premium,
            attendee_websites=attendee_websites,
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
        attendee_headline=attendee_headline,
        attendee_location=attendee_location,
        attendee_email=attendee_email,
        attendee_connections_count=attendee_connections_count,
        attendee_shared_connections_count=attendee_shared_connections_count,
        attendee_is_premium=attendee_is_premium,
        attendee_websites=attendee_websites,
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


@router.post("/conversations/{chat_id}/messages/{message_id}/reactions")
async def add_reaction(
    chat_id: str,
    message_id: str,
    body: AddReactionRequest,
) -> dict:
    """Adiciona reação emoji a uma mensagem."""
    success = await unipile_client.add_reaction(
        message_id=message_id,
        emoji=body.emoji,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao adicionar reação via Unipile",
        )
    logger.info(
        "inbox.reaction_added",
        chat_id=chat_id,
        message_id=message_id,
        emoji=body.emoji,
    )
    return {"status": "ok", "message_id": message_id, "emoji": body.emoji}


@router.delete("/conversations/{chat_id}/messages/{message_id}/reactions")
async def remove_reaction(
    chat_id: str,
    message_id: str,
    body: AddReactionRequest,
) -> dict:
    """Remove reação emoji de uma mensagem."""
    success = await unipile_client.remove_reaction(
        message_id=message_id,
        emoji=body.emoji,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao remover reação via Unipile",
        )
    logger.info(
        "inbox.reaction_removed",
        chat_id=chat_id,
        message_id=message_id,
        emoji=body.emoji,
    )
    return {"status": "ok", "message_id": message_id, "emoji": body.emoji}


# ── Helpers ───────────────────────────────────────────────────────────
# ── Recent Activity ───────────────────────────────────────────────────

@router.get(
    "/conversations/{chat_id}/activity",
    response_model=RecentActivityResponse,
)
async def get_lead_recent_activity(
    chat_id: str,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> RecentActivityResponse:
    """Retorna últimas interações do lead vinculado à conversa."""
    chat = await unipile_client.get_chat(chat_id)
    if not chat:
        return RecentActivityResponse(items=[])

    lead = await _find_lead_by_attendees(chat.attendees, tenant_id, db)
    if not lead:
        return RecentActivityResponse(items=[])

    result = await db.execute(
        select(Interaction)
        .where(
            Interaction.lead_id == lead.id,
            Interaction.tenant_id == tenant_id,
        )
        .order_by(Interaction.created_at.desc())
        .limit(10)
    )
    interactions = result.scalars().all()

    return RecentActivityResponse(
        items=[
            RecentActivityItem(
                id=i.id,
                channel=i.channel.value,
                direction=i.direction.value,
                content_preview=i.content_text[:120] if i.content_text else None,
                intent=i.intent.value if i.intent else None,
                created_at=i.created_at,
            )
            for i in interactions
        ]
    )


# ── Cadence History ──────────────────────────────────────────────────

@router.get(
    "/conversations/{chat_id}/cadences",
    response_model=CadenceHistoryResponse,
)
async def get_lead_cadence_history(
    chat_id: str,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> CadenceHistoryResponse:
    """Retorna cadências em que o lead participou/participa."""
    chat = await unipile_client.get_chat(chat_id)
    if not chat:
        return CadenceHistoryResponse(items=[])

    lead = await _find_lead_by_attendees(chat.attendees, tenant_id, db)
    if not lead:
        return CadenceHistoryResponse(items=[])

    # Busca cadências distintas em que o lead tem steps
    result = await db.execute(
        select(
            Cadence.id,
            Cadence.name,
            Cadence.mode,
            Cadence.is_active,
            func.count(CadenceStep.id).label("total_steps"),
            func.count(CadenceStep.id).filter(
                CadenceStep.status.in_([StepStatus.SENT, StepStatus.REPLIED])
            ).label("completed_steps"),
            func.max(CadenceStep.sent_at).label("last_step_at"),
        )
        .join(CadenceStep, CadenceStep.cadence_id == Cadence.id)
        .where(
            CadenceStep.lead_id == lead.id,
            CadenceStep.tenant_id == tenant_id,
        )
        .group_by(Cadence.id, Cadence.name, Cadence.mode, Cadence.is_active)
        .order_by(func.max(CadenceStep.sent_at).desc().nulls_last())
    )
    rows = result.all()

    return CadenceHistoryResponse(
        items=[
            CadenceHistoryItem(
                cadence_id=row.id,
                cadence_name=row.name,
                mode=row.mode,
                total_steps=row.total_steps,
                completed_steps=row.completed_steps,
                last_step_at=row.last_step_at,
                is_active=row.is_active,
            )
            for row in rows
        ]
    )


# ── Tags ──────────────────────────────────────────────────────────────

@router.get(
    "/conversations/{chat_id}/tags",
    response_model=list[LeadTagSchema],
)
async def get_lead_tags(
    chat_id: str,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> list[LeadTagSchema]:
    """Retorna tags do lead vinculado à conversa."""
    chat = await unipile_client.get_chat(chat_id)
    if not chat:
        return []

    lead = await _find_lead_by_attendees(chat.attendees, tenant_id, db)
    if not lead:
        return []

    result = await db.execute(
        select(LeadTag).where(
            LeadTag.lead_id == lead.id,
            LeadTag.tenant_id == tenant_id,
        )
    )
    tags = result.scalars().all()
    return [LeadTagSchema(id=t.id, name=t.name, color=t.color) for t in tags]


@router.post(
    "/conversations/{chat_id}/tags",
    response_model=LeadTagSchema,
    status_code=status.HTTP_201_CREATED,
)
async def add_lead_tag(
    chat_id: str,
    body: AddTagRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> LeadTagSchema:
    """Adiciona tag a um lead a partir da conversa do inbox."""
    chat = await unipile_client.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat não encontrado")

    lead = await _find_lead_by_attendees(chat.attendees, tenant_id, db)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não vinculado a esta conversa")

    # Verifica duplicata
    existing = await db.execute(
        select(LeadTag).where(
            LeadTag.lead_id == lead.id,
            LeadTag.name == body.name,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Tag já existe para este lead")

    tag = LeadTag(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        lead_id=lead.id,
        name=body.name,
        color=body.color,
    )
    db.add(tag)
    await db.commit()
    await db.refresh(tag)

    return LeadTagSchema(id=tag.id, name=tag.name, color=tag.color)


@router.delete(
    "/conversations/{chat_id}/tags/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def remove_lead_tag(
    chat_id: str,
    tag_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> Response:
    """Remove tag de um lead."""
    result = await db.execute(
        select(LeadTag).where(
            LeadTag.id == tag_id,
            LeadTag.tenant_id == tenant_id,
        )
    )
    tag = result.scalar_one_or_none()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag não encontrada")

    await db.delete(tag)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── Internal helpers ──────────────────────────────────────────────────
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
