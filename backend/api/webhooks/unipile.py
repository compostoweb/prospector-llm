"""
api/webhooks/unipile.py

Webhook receptor para eventos Unipile (LinkedIn + Gmail inbound).

Endpoint:
  POST /webhooks/unipile

Segurança:
  - Valida assinatura HMAC-SHA256 no header X-Unipile-Signature
  - Rejeita requisições sem assinatura válida com HTTP 401
  - Falha na validação é logada mas não revela o secret

Eventos tratados:
  - message_received  → classifica intent via ReplyParser → salva Interaction
  - account_connected → log informativo
  - (outros eventos)  → ignorados silenciosamente

Fluxo message_received:
  1. Extrai texto + unipile_message_id + account_id do payload
  2. Identifica o lead pelo linkedin_profile_id ou pelo remetente do e-mail
  3. Chama ReplyParser.classify() para detectar intenção
  4. Salva Interaction inbound no banco
  5. Se intent == INTEREST → notifica (placeholder extensível)
  6. Se intent == NOT_INTERESTED → arquiva o lead
"""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_llm_registry, get_session_no_auth
from core.config import settings
from integrations.llm import LLMRegistry
from models.cadence import Cadence
from models.cadence_step import CadenceStep
from models.enums import Channel, Intent, InteractionDirection, LeadStatus
from models.interaction import Interaction
from models.lead import Lead
from services.llm_config import resolve_tenant_llm_config
from services.reply_parser import ReplyParser

logger = structlog.get_logger()

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# Canais de mensagem que o Unipile pode reportar
_LINKEDIN_ACCOUNT_TYPE = "LINKEDIN"
_EMAIL_ACCOUNT_TYPE = "GMAIL"


@router.post("/unipile", status_code=status.HTTP_200_OK)
async def unipile_webhook(
    request: Request,
    db: AsyncSession = Depends(get_session_no_auth),
    registry: LLMRegistry = Depends(get_llm_registry),
) -> dict:
    """
    Recebe eventos da Unipile e processa mensagens inbound.
    Sempre retorna 200 para evitar reenvio agressivo da Unipile.
    """
    body = await request.body()

    # ── Validação de assinatura ───────────────────────────────────────
    signature_header = request.headers.get("X-Unipile-Signature", "")
    if not _verify_signature(body, signature_header):
        logger.warning("webhook.unipile.invalid_signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Assinatura inválida",
        )

    try:
        payload = json.loads(body)
    except Exception:  # noqa: BLE001
        logger.warning("webhook.unipile.invalid_json")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload inválido",
        )

    event_type: str = payload.get("event", "")
    logger.info("webhook.unipile.received", event_type=event_type)

    if event_type == "message_received":
        await _handle_message_received(payload, db, registry)
    elif event_type == "relation_created":
        await _handle_relation_created(payload, db)
    elif event_type == "account_connected":
        logger.info(
            "webhook.unipile.account_connected",
            account_id=payload.get("account_id"),
        )
    # Outros eventos são ignorados silenciosamente

    return {"status": "ok"}


# ── Handlers ──────────────────────────────────────────────────────────


async def _handle_relation_created(
    payload: dict,
    db: AsyncSession,
) -> None:
    """
    Processa aceite de conexão LinkedIn.
    Atualiza lead.linkedin_connection_status e cria ManualTasks se cadência semi-manual.
    """
    relation = payload.get("relation") or payload
    profile_id: str = (
        relation.get("linkedin_profile_id")
        or relation.get("provider_id")
        or relation.get("profile_id")
        or ""
    )
    if not profile_id:
        logger.warning("webhook.unipile.relation_created.no_profile_id")
        return

    result = await db.execute(select(Lead).where(Lead.linkedin_profile_id == profile_id.strip()))
    lead = result.scalar_one_or_none()
    if not lead:
        logger.info(
            "webhook.unipile.relation_created.lead_not_found",
            profile_id=profile_id,
        )
        return

    if lead.linkedin_connection_status == "connected":
        logger.debug(
            "webhook.unipile.relation_created.already_connected",
            lead_id=str(lead.id),
        )
        return

    lead.linkedin_connection_status = "connected"
    lead.linkedin_connected_at = datetime.now(tz=UTC)

    logger.info(
        "webhook.unipile.relation_created.connected",
        lead_id=str(lead.id),
        profile_id=profile_id,
    )

    # Se lead está em cadência semi-manual, criar ManualTasks
    step_result = await db.execute(
        select(CadenceStep.cadence_id).where(CadenceStep.lead_id == lead.id).limit(1)
    )
    cadence_id = step_result.scalar_one_or_none()

    if cadence_id:
        cad_result = await db.execute(select(Cadence).where(Cadence.id == cadence_id))
        cadence = cad_result.scalar_one_or_none()

        if cadence and cadence.mode == "semi_manual":
            from services.manual_task_service import ManualTaskService

            task_service = ManualTaskService()
            await task_service.create_tasks_for_lead(lead, cadence, db)
            logger.info(
                "webhook.unipile.relation_created.tasks_created",
                lead_id=str(lead.id),
                cadence_id=str(cadence.id),
            )

    await db.commit()

    # Broadcast WebSocket para atualizar UI em tempo real
    from api.routes.ws import broadcast_event

    await broadcast_event(
        str(lead.tenant_id),
        {
            "type": "connection_accepted",
            "lead_id": str(lead.id),
            "lead_name": lead.name,
            "profile_id": profile_id,
        },
    )


async def _handle_message_received(
    payload: dict,
    db: AsyncSession,
    registry: LLMRegistry,
) -> None:
    """
    Processa um evento message_received da Unipile.
    Identifica o lead, classifica a intent e salva a Interaction.
    """
    message = payload.get("message") or payload
    unipile_message_id: str = message.get("id") or message.get("message_id") or ""
    sender_id: str = message.get("sender_id") or message.get("from") or ""
    text_content: str = _extract_text(message)
    account_id: str = message.get("account_id") or ""

    if not text_content:
        logger.debug("webhook.unipile.empty_message", message_id=unipile_message_id)
        return

    # ── Idempotência: ignora mensagem já processada ────────────────
    if unipile_message_id:
        existing = await db.execute(
            select(Interaction.id)
            .where(Interaction.unipile_message_id == unipile_message_id)
            .limit(1)
        )
        if existing.scalar_one_or_none() is not None:
            logger.debug(
                "webhook.unipile.duplicate_message",
                message_id=unipile_message_id,
            )
            return

    # Tenta encontrar o lead pelo sender_id (linkedin_profile_id ou e-mail)
    lead = await _find_lead_by_sender(sender_id, db)
    if not lead:
        logger.info(
            "webhook.unipile.lead_not_found",
            sender_id=sender_id,
            message_id=unipile_message_id,
        )
        return

    # ── Classifica intenção ───────────────────────────────────────────
    llm_config = await resolve_tenant_llm_config(db, lead.tenant_id)
    parser = ReplyParser(
        registry=registry,
        provider=llm_config.provider,
        model=llm_config.model,
    )
    classification = await parser.classify(
        reply_text=text_content,
        lead_name=lead.name,
    )

    intent_str: str = (classification.get("intent") or "NEUTRAL").upper()
    try:
        intent = Intent[intent_str]
    except KeyError:
        intent = Intent.NEUTRAL

    # ── Detecta canal pela conta Unipile ─────────────────────────────
    channel = _detect_channel(account_id)

    # ── Salva Interaction inbound ─────────────────────────────────────
    interaction = Interaction(
        id=uuid.uuid4(),
        tenant_id=lead.tenant_id,
        lead_id=lead.id,
        channel=channel,
        direction=InteractionDirection.INBOUND,
        content_text=text_content,
        intent=intent,
        unipile_message_id=unipile_message_id or None,
        created_at=datetime.now(tz=UTC),
    )
    db.add(interaction)

    # ── Ações por intenção ────────────────────────────────────────────
    if intent == Intent.NOT_INTERESTED:
        lead.status = LeadStatus.ARCHIVED
        logger.info(
            "webhook.unipile.lead_archived",
            lead_id=str(lead.id),
            reason="NOT_INTERESTED",
        )
    elif intent == Intent.INTEREST:
        lead.status = LeadStatus.CONVERTED
        logger.info(
            "webhook.unipile.lead_converted",
            lead_id=str(lead.id),
            classification=classification,
        )

    await db.commit()

    # ── Notificação via Resend (interesse ou objeção) ─────────────
    if intent in (Intent.INTEREST, Intent.OBJECTION):
        from services.notification import send_reply_notification

        await send_reply_notification(
            lead=lead,
            intent=intent.value,
            reply_text=text_content,
            tenant_id=lead.tenant_id,
            db=db,
        )

    logger.info(
        "webhook.unipile.processed",
        lead_id=str(lead.id),
        intent=intent.value,
        confidence=classification.get("confidence"),
        summary=classification.get("summary"),
    )

    # Broadcast WebSocket para atualizar inbox em tempo real
    from api.routes.ws import broadcast_event

    await broadcast_event(
        str(lead.tenant_id),
        {
            "type": "new_message",
            "lead_id": str(lead.id),
            "lead_name": lead.name,
            "channel": channel.value,
            "intent": intent.value,
            "text_preview": text_content[:100],
        },
    )


# ── Helpers ───────────────────────────────────────────────────────────


def _verify_signature(body: bytes, signature_header: str) -> bool:
    """
    Valida a assinatura HMAC-SHA256 do webhook Unipile.
    A Unipile envia: X-Unipile-Signature: sha256=<hex_digest>
    """
    secret = (settings.UNIPILE_WEBHOOK_SECRET or "").strip()
    if not secret or secret == "...":
        if settings.ENV == "prod":
            logger.error("webhook.unipile.no_secret_in_prod")
            return False
        logger.warning("webhook.unipile.no_secret_configured")
        return True

    expected_prefix = "sha256="
    if not signature_header.startswith(expected_prefix):
        return False

    received_digest = signature_header[len(expected_prefix) :]
    expected_digest = hmac.new(
        secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(received_digest, expected_digest)


async def _find_lead_by_sender(sender_id: str, db: AsyncSession) -> Lead | None:
    """
    Localiza o lead pelo sender_id do Unipile.
    Tenta: linkedin_profile_id → e-mail corporativo → e-mail pessoal.
    """
    if not sender_id:
        return None

    # Normaliza para comparar corretamente (case-insensitive)
    sender_normalized = sender_id.strip()

    # Tenta como linkedin_profile_id
    result = await db.execute(select(Lead).where(Lead.linkedin_profile_id == sender_normalized))
    lead = result.scalar_one_or_none()
    if lead:
        return lead

    # Tenta como e-mail (formato sender para Gmail)
    if "@" in sender_normalized:
        sender_lower = sender_normalized.lower()
        result = await db.execute(select(Lead).where(Lead.email_corporate == sender_lower))
        lead = result.scalar_one_or_none()
        if lead:
            return lead

        result = await db.execute(select(Lead).where(Lead.email_personal == sender_lower))
        return result.scalar_one_or_none()

    return None


def _extract_text(message: dict) -> str:
    """Extrai o texto do corpo da mensagem Unipile — trata formatos variados."""
    # Formato LinkedIn
    if text := message.get("text"):
        return str(text).strip()
    # Formato e-mail
    if body := message.get("body"):
        return str(body).strip()
    # Array de partes
    parts = message.get("parts") or []
    if isinstance(parts, list) and parts:
        for part in parts:
            if isinstance(part, dict) and part.get("type") == "text":
                return str(part.get("content", "")).strip()
    return ""


def _detect_channel(account_id: str) -> Channel:
    """Detecta o canal pelo ID da conta Unipile."""
    linkedin_account = settings.UNIPILE_ACCOUNT_ID_LINKEDIN or ""
    gmail_account = settings.UNIPILE_ACCOUNT_ID_GMAIL or ""

    if account_id == gmail_account:
        return Channel.EMAIL
    # Default para LinkedIn DM (inbound sempre é DM, nunca connect)
    return Channel.LINKEDIN_DM
