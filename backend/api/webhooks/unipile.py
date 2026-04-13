"""
api/webhooks/unipile.py

Webhook receptor para eventos Unipile (LinkedIn + Gmail inbound).

Endpoint:
  POST /webhooks/unipile

Segurança:
    - Valida assinatura HMAC-SHA256 no header X-Unipile-Signature
    - Aceita header customizado Unipile-Auth para webhooks criados via API
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
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_llm_registry, get_session_no_auth
from core.config import settings
from integrations.llm import LLMRegistry
from models.cadence import Cadence
from models.cadence_step import CadenceStep
from models.enums import Channel, Intent, InteractionDirection, LeadStatus, StepStatus
from models.interaction import Interaction
from models.lead import Lead
from models.lead_email import LeadEmail
from models.tenant import Tenant, TenantIntegration
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
    custom_auth_header = request.headers.get("Unipile-Auth", "")
    if not _verify_signature(body, signature_header, custom_auth_header):
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
    account_id: str = relation.get("account_id") or payload.get("account_id") or ""
    if not profile_id:
        logger.warning("webhook.unipile.relation_created.no_profile_id")
        return

    tenant_id = await _resolve_tenant_id_for_unipile_account(account_id, db)
    if tenant_id is None:
        logger.warning(
            "webhook.unipile.relation_created.tenant_unresolved",
            account_id=account_id or None,
            profile_id=profile_id,
        )
        return

    result = await db.execute(
        select(Lead).where(
            Lead.tenant_id == tenant_id,
            Lead.linkedin_profile_id == profile_id.strip(),
        )
    )
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
        select(CadenceStep.cadence_id)
        .where(
            CadenceStep.lead_id == lead.id,
            CadenceStep.tenant_id == lead.tenant_id,
        )
        .limit(1)
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

    if account_id:
        from integrations.unipile_client import unipile_client

        await unipile_client.invalidate_inbox_cache(account_id)

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
    tenant_id = await _resolve_tenant_id_for_unipile_account(account_id, db)
    if tenant_id is None:
        logger.warning(
            "webhook.unipile.tenant_unresolved",
            account_id=account_id or None,
            sender_id=sender_id or None,
            message_id=unipile_message_id or None,
        )
        return

    lead = await _find_lead_by_sender(sender_id, tenant_id, db)
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
        tenant_id=str(lead.tenant_id),
        lead_id=str(lead.id),
        channel=_detect_channel(account_id).value,
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

    await _mark_latest_step_replied(
        lead_id=lead.id,
        tenant_id=lead.tenant_id,
        channel=channel,
        db=db,
    )

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


def _verify_signature(body: bytes, signature_header: str, custom_auth_header: str = "") -> bool:
    """
    Valida o webhook da Unipile.
    Aceita:
      - X-Unipile-Signature: sha256=<hex_digest>
      - Unipile-Auth: <secret>
    """
    secret = (settings.UNIPILE_WEBHOOK_SECRET or "").strip()
    if not secret or secret == "...":
        if settings.ENV == "prod":
            logger.error("webhook.unipile.no_secret_in_prod")
            return False
        logger.warning("webhook.unipile.no_secret_configured")
        return True

    if custom_auth_header and hmac.compare_digest(custom_auth_header, secret):
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


async def _resolve_tenant_id_for_unipile_account(
    account_id: str,
    db: AsyncSession,
) -> uuid.UUID | None:
    """
    Resolve o tenant pela conta Unipile configurada.
    Se houver apenas um tenant ativo, faz fallback seguro para ambiente MVP.
    """
    normalized_account_id = account_id.strip()

    if normalized_account_id:
        result = await db.execute(
            select(TenantIntegration.tenant_id).where(
                or_(
                    TenantIntegration.unipile_linkedin_account_id == normalized_account_id,
                    TenantIntegration.unipile_gmail_account_id == normalized_account_id,
                )
            )
        )
        tenant_ids = list(dict.fromkeys(result.scalars().all()))
        if len(tenant_ids) == 1:
            return tenant_ids[0]
        if len(tenant_ids) > 1:
            logger.error(
                "webhook.unipile.account_ambiguous",
                account_id=normalized_account_id,
                tenant_count=len(tenant_ids),
            )
            return None

        known_global_accounts = {
            value
            for value in (
                settings.UNIPILE_ACCOUNT_ID_LINKEDIN or "",
                settings.UNIPILE_ACCOUNT_ID_GMAIL or "",
            )
            if value
        }
        if known_global_accounts and normalized_account_id not in known_global_accounts:
            logger.warning(
                "webhook.unipile.unknown_account",
                account_id=normalized_account_id,
            )
            return None

    active_tenants_result = await db.execute(
        select(Tenant.id)
        .where(Tenant.is_active.is_(True))
        .order_by(Tenant.created_at.asc())
        .limit(2)
    )
    active_tenants = active_tenants_result.scalars().all()
    if len(active_tenants) == 1:
        return active_tenants[0]
    return None


async def _find_lead_by_sender(
    sender_id: str,
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> Lead | None:
    """
    Localiza o lead pelo sender_id do Unipile.
    Tenta: linkedin_profile_id → e-mail corporativo → e-mail pessoal.
    """
    if not sender_id:
        return None

    # Normaliza para comparar corretamente (case-insensitive)
    sender_normalized = sender_id.strip()

    # Tenta como linkedin_profile_id
    result = await db.execute(
        select(Lead).where(
            Lead.tenant_id == tenant_id,
            Lead.linkedin_profile_id == sender_normalized,
        )
    )
    lead = result.scalar_one_or_none()
    if lead:
        return lead

    # Tenta como e-mail (formato sender para Gmail)
    if "@" in sender_normalized:
        sender_lower = sender_normalized.lower()
        result = await db.execute(
            select(Lead).where(
                Lead.tenant_id == tenant_id,
                func.lower(Lead.email_corporate) == sender_lower,
            )
        )
        lead = result.scalar_one_or_none()
        if lead:
            return lead

        result = await db.execute(
            select(Lead).where(
                Lead.tenant_id == tenant_id,
                func.lower(Lead.email_personal) == sender_lower,
            )
        )
        lead = result.scalar_one_or_none()
        if lead:
            return lead

        result = await db.execute(
            select(Lead)
            .join(LeadEmail, LeadEmail.lead_id == Lead.id)
            .where(
                Lead.tenant_id == tenant_id,
                LeadEmail.email == sender_lower,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    return None


async def _mark_latest_step_replied(
    lead_id: uuid.UUID,
    tenant_id: uuid.UUID,
    channel: Channel,
    db: AsyncSession,
) -> None:
    """Marca o step enviado mais recente do mesmo canal como respondido."""
    result = await db.execute(
        select(CadenceStep)
        .where(
            CadenceStep.lead_id == lead_id,
            CadenceStep.tenant_id == tenant_id,
            CadenceStep.channel == channel,
            CadenceStep.status == StepStatus.SENT,
        )
        .order_by(CadenceStep.sent_at.desc().nulls_last(), CadenceStep.scheduled_at.desc())
        .limit(1)
    )
    latest_step = result.scalar_one_or_none()
    if latest_step is not None:
        latest_step.status = StepStatus.REPLIED


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
