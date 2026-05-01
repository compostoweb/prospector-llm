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
    - mail_received     → classifica intent via ReplyParser → salva Interaction
    - new_relation      → marca conexão LinkedIn aceita
    - account status    → log informativo
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
import re
import uuid
from datetime import UTC, datetime
from email.utils import parseaddr
from typing import Any, cast

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_llm_registry, get_session_no_auth
from core.config import settings
from integrations.llm import LLMRegistry
from models.cadence import Cadence
from models.cadence_step import CadenceStep
from models.email_account import EmailAccount
from models.enums import Intent
from models.interaction import Interaction
from models.lead import Lead
from models.linkedin_account import LinkedInAccount
from services.account_audit_log_service import record_account_audit_log
from services.email_event_service import classify_inbound_email_event, record_email_bounce
from services.inbound_message_service import (
    find_lead_by_sender as _svc_find_lead_by_sender,
)
from services.inbound_message_service import (
    process_inbound_reply,
    resolve_unipile_account_context,
)
from services.linkedin_account_service import parse_hosted_linkedin_auth_state

logger = structlog.get_logger()

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# Canais de mensagem que o Unipile pode reportar
_LINKEDIN_ACCOUNT_TYPE = "LINKEDIN"
_EMAIL_ACCOUNT_TYPE = "GMAIL"
_ACCOUNT_STATUS_EVENTS = {
    "ok",
    "error",
    "stopped",
    "credentials",
    "connecting",
    "deleted",
    "creation_success",
    "reconnected",
    "sync_success",
}


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

    event_type = _extract_event_type(payload)
    logger.info("webhook.unipile.received", event_type=event_type)

    if event_type in {"message_received", "mail_received"}:
        await _handle_message_received(payload, db, registry)
    elif event_type in {"new_relation", "relation_created"}:
        await _handle_relation_created(payload, db)
    elif event_type in _ACCOUNT_STATUS_EVENTS:
        await _handle_account_status(payload, event_type, db)
    elif event_type in {"message_read", "chat_read", "message_seen", "read_receipt"}:
        await _handle_chat_read(payload)
    else:
        # Log para descobrir novos eventos da Unipile (ex: chat_read, typing, etc.)
        logger.info(
            "webhook.unipile.unhandled",
            event_type=event_type,
            payload_keys=list(payload.keys()),
        )

    return {"status": "ok"}


@router.post("/unipile/hosted-auth", status_code=status.HTTP_200_OK)
async def unipile_hosted_auth_webhook(
    request: Request,
    db: AsyncSession = Depends(get_session_no_auth),
) -> dict:
    """Recebe callback do Hosted Auth Wizard e registra contas LinkedIn Unipile."""
    body = await request.body()

    signature_header = request.headers.get("X-Unipile-Signature", "")
    custom_auth_header = request.headers.get("Unipile-Auth", "")
    if not _verify_signature(body, signature_header, custom_auth_header):
        logger.warning("webhook.unipile.hosted_auth.invalid_signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Assinatura inválida",
        )

    try:
        payload = json.loads(body)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload inválido",
        ) from exc

    account_id = str(payload.get("account_id") or "").strip()
    state = str(payload.get("name") or "").strip()
    hosted_status = str(payload.get("status") or "").lower()
    if not account_id or not state:
        logger.warning("webhook.unipile.hosted_auth.missing_fields")
        return {"status": "ignored"}
    if hosted_status not in {"creation_success", "reconnected"}:
        logger.info(
            "webhook.unipile.hosted_auth.non_success",
            hosted_status=hosted_status or None,
            account_id=account_id,
        )
        return {"status": "ignored"}

    try:
        auth_state = parse_hosted_linkedin_auth_state(state)
    except ValueError as exc:
        logger.warning("webhook.unipile.hosted_auth.invalid_state", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Estado Hosted Auth inválido",
        ) from exc

    now = datetime.now(UTC)
    result = await db.execute(
        select(LinkedInAccount).where(
            LinkedInAccount.tenant_id == auth_state.tenant_id,
            LinkedInAccount.unipile_account_id == account_id,
        )
    )
    account = result.scalar_one_or_none()
    if account is None:
        account = LinkedInAccount(
            tenant_id=auth_state.tenant_id,
            display_name=auth_state.display_name,
            linkedin_username=auth_state.linkedin_username,
            owner_user_id=auth_state.user_id,
            created_by_user_id=auth_state.user_id,
            provider_type="unipile",
            unipile_account_id=account_id,
            supports_inmail=auth_state.supports_inmail,
            provider_status="connected",
            connected_at=now,
            last_status_at=now,
        )
        db.add(account)
    else:
        account.display_name = auth_state.display_name
        account.linkedin_username = auth_state.linkedin_username
        account.owner_user_id = auth_state.user_id
        account.supports_inmail = auth_state.supports_inmail
        account.is_active = True
        account.provider_status = "connected"
        account.health_error = None
        account.connected_at = account.connected_at or now
        account.disconnected_at = None
        account.reconnect_required_at = None
        account.last_status_at = now

    await db.flush()
    await record_account_audit_log(
        db,
        tenant_id=auth_state.tenant_id,
        account_type="linkedin",
        account_id=account.id,
        external_account_id=account.unipile_account_id,
        provider_type=account.provider_type,
        event_type="reconnected" if hosted_status == "reconnected" else "connected",
        actor_user_id=auth_state.user_id,
        provider_status=account.provider_status,
        message="Callback Hosted Auth da Unipile processado.",
        event_metadata={"hosted_status": hosted_status},
    )
    await db.commit()
    logger.info(
        "webhook.unipile.hosted_auth.account_connected",
        tenant_id=str(auth_state.tenant_id),
        account_id=account_id,
        owner_user_id=str(auth_state.user_id) if auth_state.user_id else None,
    )
    return {"status": "ok"}


# ── Handlers ──────────────────────────────────────────────────────────


async def _handle_account_status(
    payload: dict,
    event_type: str,
    db: AsyncSession,
) -> None:
    account_status = _extract_account_status_payload(payload)
    account_id = _extract_account_status_account_id(payload, account_status)
    account_type = _normalize_account_status_type(
        _extract_account_status_account_type(payload, account_status)
    )
    normalized_status = (event_type or "").strip().lower()

    if not account_id:
        logger.warning("webhook.unipile.account_status.no_account_id", status=normalized_status)
        return

    updated_count = 0
    if account_type in {None, _LINKEDIN_ACCOUNT_TYPE}:
        linkedin_result = await db.execute(
            select(LinkedInAccount).where(
                LinkedInAccount.unipile_account_id == account_id,
                LinkedInAccount.provider_type == "unipile",
            )
        )
        for linkedin_account in linkedin_result.scalars().all():
            previous_status = linkedin_account.provider_status
            previous_error = linkedin_account.health_error
            _apply_unipile_account_status(
                linkedin_account,
                normalized_status,
                account_status,
                payload,
            )
            await record_account_audit_log(
                db,
                tenant_id=linkedin_account.tenant_id,
                account_type="linkedin",
                account_id=linkedin_account.id,
                external_account_id=linkedin_account.unipile_account_id,
                provider_type=linkedin_account.provider_type,
                event_type=f"status_{normalized_status or 'unknown'}",
                actor_user_id=linkedin_account.owner_user_id,
                provider_status=linkedin_account.provider_status,
                message=linkedin_account.health_error,
                event_metadata={
                    "previous_status": previous_status,
                    "previous_error": previous_error,
                    "account_type": account_type,
                },
            )
            updated_count += 1

    if account_type in {None, _EMAIL_ACCOUNT_TYPE}:
        email_result = await db.execute(
            select(EmailAccount).where(
                EmailAccount.unipile_account_id == account_id,
                EmailAccount.provider_type == "unipile_gmail",
            )
        )
        for email_account in email_result.scalars().all():
            previous_status = email_account.provider_status
            previous_error = email_account.health_error
            _apply_unipile_account_status(email_account, normalized_status, account_status, payload)
            await record_account_audit_log(
                db,
                tenant_id=email_account.tenant_id,
                account_type="email",
                account_id=email_account.id,
                external_account_id=email_account.unipile_account_id,
                provider_type=email_account.provider_type,
                event_type=f"status_{normalized_status or 'unknown'}",
                actor_user_id=email_account.owner_user_id,
                provider_status=email_account.provider_status,
                message=email_account.health_error,
                event_metadata={
                    "previous_status": previous_status,
                    "previous_error": previous_error,
                    "account_type": account_type,
                },
            )
            updated_count += 1

    if updated_count == 0:
        logger.info(
            "webhook.unipile.account_status.account_not_found",
            account_id=account_id,
            account_type=account_type,
            status=normalized_status,
        )
        return

    await db.commit()
    logger.info(
        "webhook.unipile.account_status.updated",
        account_id=account_id,
        account_type=account_type,
        status=normalized_status,
        updated_count=updated_count,
    )


def _apply_unipile_account_status(
    account: LinkedInAccount | EmailAccount,
    normalized_status: str,
    account_status: dict,
    payload: dict,
) -> None:
    now = datetime.now(UTC)
    account.last_status_at = now

    if normalized_status in {"ok", "reconnected", "sync_success", "creation_success"}:
        account.provider_status = "connected" if normalized_status == "creation_success" else "ok"
        account.is_active = True
        account.health_error = None
        account.connected_at = account.connected_at or now
        account.disconnected_at = None
        account.reconnect_required_at = None
        return

    if normalized_status == "connecting":
        account.provider_status = "connecting"
        account.is_active = True
        account.health_error = None
        return

    account.provider_status = normalized_status or "error"
    account.is_active = True
    account.health_error = _extract_account_status_error(account_status, payload, normalized_status)
    account.disconnected_at = account.disconnected_at or now
    account.reconnect_required_at = account.reconnect_required_at or now


def _extract_account_status_payload(payload: dict) -> dict:
    account_status = payload.get("AccountStatus")
    if isinstance(account_status, dict):
        return cast(dict[str, Any], account_status)
    return {}


def _extract_account_status_account_id(payload: dict, account_status: dict) -> str:
    account = account_status.get("account") or payload.get("account")
    account_id = ""
    if isinstance(account, dict):
        account_id = str(account.get("id") or account.get("account_id") or "").strip()
    return str(
        account_status.get("account_id") or payload.get("account_id") or account_id or ""
    ).strip()


def _extract_account_status_account_type(payload: dict, account_status: dict) -> str | None:
    account = account_status.get("account") or payload.get("account")
    if isinstance(account, dict):
        account_type = account.get("type") or account.get("account_type") or account.get("provider")
        if account_type:
            return str(account_type)
    for source in (account_status, payload):
        account_type = source.get("account_type") or source.get("type") or source.get("provider")
        if account_type:
            return str(account_type)
    return None


def _normalize_account_status_type(account_type: str | None) -> str | None:
    normalized = (account_type or "").strip().upper()
    if normalized in {"LINKEDIN", "LINKEDIN_RECRUITER", "LINKEDIN_SALES_NAVIGATOR"}:
        return _LINKEDIN_ACCOUNT_TYPE
    if normalized in {"GMAIL", "GOOGLE", "EMAIL", "MAIL"}:
        return _EMAIL_ACCOUNT_TYPE
    return normalized or None


def _extract_account_status_error(
    account_status: dict,
    payload: dict,
    normalized_status: str,
) -> str:
    for source in (account_status, payload):
        for key in ("error", "error_message", "reason", "details", "description"):
            value = source.get(key)
            if value:
                return str(value)[:1000]
    return f"Status Unipile: {normalized_status or 'error'}"


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
        or relation.get("user_provider_id")
        or relation.get("provider_id")
        or relation.get("profile_id")
        or ""
    )
    account_id: str = relation.get("account_id") or payload.get("account_id") or ""
    account_type = _extract_account_type(relation, payload)
    if not profile_id:
        logger.warning("webhook.unipile.relation_created.no_profile_id")
        return

    account_context = await resolve_unipile_account_context(
        account_id,
        db,
        account_type=account_type or _LINKEDIN_ACCOUNT_TYPE,
    )
    if account_context is None:
        logger.warning(
            "webhook.unipile.relation_created.tenant_unresolved",
            account_id=account_id or None,
            account_type=account_type or None,
            profile_id=profile_id,
        )
        return
    tenant_id = account_context.tenant_id

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


async def _handle_chat_read(payload: dict) -> None:
    """
    Propaga leitura de mensagem detectada no LinkedIn para o inbox do Prospector.
    Invalida cache Redis do chat e faz broadcast WS para todos os tenants com a conta.
    """
    chat_id: str = (
        payload.get("chat_id")
        or payload.get("chatId")
        or (payload.get("chat") or {}).get("id")
        or ""
    )
    account_id: str = payload.get("account_id") or ""

    if not chat_id:
        logger.warning("webhook.unipile.chat_read.no_chat_id", payload_keys=list(payload.keys()))
        return

    # Invalida cache Redis para que a próxima query retorne unread_count atualizado
    if account_id:
        from integrations.unipile_client import unipile_client

        await unipile_client.invalidate_inbox_cache(account_id, chat_id=chat_id)

    # Broadcast WS para todos os tenants conectados (sem isolamento de tenant aqui,
    # pois não temos o tenant_id no payload — o frontend filtra pelo chat_id)
    from api.routes.ws import broadcast_all_tenants

    await broadcast_all_tenants({"type": "inbox.chat_read", "chat_id": chat_id})
    logger.info("webhook.unipile.chat_read", chat_id=chat_id, account_id=account_id or None)


async def _handle_message_received(
    payload: dict,
    db: AsyncSession,
    registry: LLMRegistry,
) -> None:
    """
    Processa um evento message_received da Unipile.
    Identifica o lead, classifica a intent e salva a Interaction.
    """
    message = _extract_message_payload(payload)
    unipile_message_id = (
        str(message.get("id") or "")
        or str(message.get("message_id") or "")
        or str(payload.get("message_id") or "")
        or str(payload.get("email_id") or "")
    )
    sender_id = _extract_message_sender_id(payload, message)
    text_content: str = _extract_text(message)
    subject = _extract_subject(message, payload)
    account_id = _extract_message_account_id(payload, message)
    account_type = _extract_account_type(message, payload)
    reply_to_message_ids = _extract_reply_reference_ids(message, payload)
    provider_thread_id = _extract_provider_thread_id(message, payload)

    if _is_outbound_message_event(payload):
        logger.debug(
            "webhook.unipile.outbound_message_ignored",
            message_id=unipile_message_id or None,
            account_id=account_id or None,
        )
        return

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
    account_context = await resolve_unipile_account_context(
        account_id,
        db,
        account_type=account_type,
        sender_id=sender_id,
    )
    if account_context is None:
        logger.warning(
            "webhook.unipile.tenant_unresolved",
            account_id=account_id or None,
            account_type=account_type or None,
            sender_id=sender_id or None,
            message_id=unipile_message_id or None,
        )
        return
    tenant_id = account_context.tenant_id

    if await _is_outbound_email_event(
        payload,
        db,
        tenant_id=tenant_id,
        sender_id=sender_id,
    ):
        logger.debug(
            "webhook.unipile.outbound_mail_ignored",
            tenant_id=str(tenant_id),
            sender_id=sender_id or None,
            message_id=unipile_message_id or None,
            account_id=account_id or None,
        )
        return

    if account_context.channel.value == "email":
        inbound_email_event = classify_inbound_email_event(
            from_email=sender_id,
            subject=subject,
            body=text_content,
        )
        if inbound_email_event.kind == "ignored":
            return
        if inbound_email_event.kind == "bounce":
            if inbound_email_event.matched_email:
                await record_email_bounce(
                    db,
                    tenant_id,
                    inbound_email_event.matched_email,
                    source="unipile_mail_received",
                    bounce_type=inbound_email_event.bounce_type or "hard",
                )
            else:
                logger.info(
                    "webhook.unipile.mail_bounce_unmatched",
                    tenant_id=str(tenant_id),
                    sender_id=sender_id or None,
                    message_id=unipile_message_id or None,
                    subject=subject or None,
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

    result = await process_inbound_reply(
        db=db,
        registry=registry,
        tenant_id=lead.tenant_id,
        lead=lead,
        channel=account_context.channel,
        reply_text=text_content,
        external_message_id=unipile_message_id or None,
        reply_to_message_ids=reply_to_message_ids,
        provider_thread_id=provider_thread_id,
        inbound_subject=subject or None,
    )

    if result.intent == Intent.NOT_INTERESTED:
        logger.info(
            "webhook.unipile.lead_archived",
            lead_id=str(lead.id),
            reason="NOT_INTERESTED",
        )
    elif result.intent == Intent.INTEREST:
        logger.info(
            "webhook.unipile.lead_converted",
            lead_id=str(lead.id),
            classification=result.classification,
        )

    logger.info(
        "webhook.unipile.processed",
        lead_id=str(lead.id),
        intent=result.intent.value,
        confidence=result.classification.get("confidence"),
        summary=result.classification.get("summary"),
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
        else:
            logger.error("webhook.unipile.no_secret_configured")
        return False

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
    account_context = await resolve_unipile_account_context(account_id, db)
    if account_context is None:
        return None
    return account_context.tenant_id


async def _find_lead_by_sender(
    sender_id: str,
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> Lead | None:
    return await _svc_find_lead_by_sender(sender_id, tenant_id, db)


def _extract_text(message: dict) -> str:
    """Extrai o texto do corpo da mensagem Unipile — trata formatos variados."""
    message_text = message.get("message")
    if isinstance(message_text, str) and message_text.strip():
        return message_text.strip()
    if text := message.get("text"):
        return str(text).strip()
    if body_plain := message.get("body_plain"):
        return str(body_plain).strip()
    # Formato e-mail
    if body := message.get("body"):
        return str(body).strip()
    # Array de partes
    parts = message.get("parts") or []
    if isinstance(parts, list) and parts:
        for part in parts:
            if isinstance(part, dict) and part.get("type") == "text":
                return str(part.get("content", "")).strip()
    if text := message.get("subject"):
        return str(text).strip()
    return ""


def _extract_subject(message: dict, payload: dict) -> str:
    return str(message.get("subject") or payload.get("subject") or "").strip()


def _extract_event_type(payload: dict) -> str:
    event = payload.get("event")
    if isinstance(event, str) and event.strip():
        normalized_event = event.strip().lower()
        if normalized_event in {
            "account_status",
            "account_status_changed",
            "account_status_updated",
        }:
            status_value = _extract_account_status_value(payload)
            if status_value:
                return status_value
        return normalized_event

    account_status = payload.get("AccountStatus")
    if isinstance(account_status, dict):
        status_value = _extract_account_status_value(payload)
        if status_value:
            return status_value

    return ""


def _extract_account_status_value(payload: dict) -> str:
    account_status = payload.get("AccountStatus")
    status_sources = [account_status, payload] if isinstance(account_status, dict) else [payload]
    for source in status_sources:
        if not isinstance(source, dict):
            continue
        for key in ("message", "status", "account_status"):
            value = source.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip().lower()
    return ""


def _extract_message_payload(payload: dict) -> dict:
    message = payload.get("message")
    if isinstance(message, dict):
        return message
    return payload


def _extract_message_sender_id(payload: dict, message: dict) -> str:
    raw_sender = payload.get("sender")
    if isinstance(raw_sender, dict):
        sender = cast(dict[str, Any], raw_sender)
    else:
        sender = {}

    raw_from_attendee = payload.get("from_attendee")
    if isinstance(raw_from_attendee, dict):
        from_attendee = cast(dict[str, Any], raw_from_attendee)
    else:
        from_attendee = {}

    return str(
        sender.get("attendee_provider_id")
        or from_attendee.get("identifier")
        or message.get("sender_id")
        or message.get("from")
        or payload.get("sender_id")
        or payload.get("from")
        or ""
    ).strip()


def _extract_message_account_id(payload: dict, message: dict) -> str:
    return str(message.get("account_id") or payload.get("account_id") or "").strip()


def _extract_account_type(*payloads: dict) -> str:
    for payload in payloads:
        if not isinstance(payload, dict):
            continue

        account_type = payload.get("account_type")
        if account_type:
            return str(account_type).strip()

        account = payload.get("account")
        if isinstance(account, dict) and account.get("type"):
            return str(account["type"]).strip()

    return ""


def _extract_reply_reference_ids(message: dict, payload: dict) -> list[str]:
    values: list[str] = []
    for candidate in (
        message.get("reply_to_message_id"),
        payload.get("reply_to_message_id"),
        message.get("in_reply_to"),
        payload.get("in_reply_to"),
        message.get("references"),
        payload.get("references"),
    ):
        if isinstance(candidate, str) and candidate.strip():
            values.append(candidate.strip())

    headers = message.get("headers") or payload.get("headers") or []
    if isinstance(headers, dict):
        headers = [headers]
    if isinstance(headers, list):
        for header in headers:
            if not isinstance(header, dict):
                continue
            name = str(header.get("name") or header.get("key") or "").strip().lower()
            value = str(header.get("value") or "").strip()
            if not value:
                continue
            if name in {"in-reply-to", "references"}:
                values.append(value)

    references: list[str] = []
    for value in values:
        matches = re.findall(r"<[^>]+>", value)
        if matches:
            references.extend(matches)
            continue
        for token in value.split():
            cleaned = token.strip()
            if cleaned:
                references.append(cleaned)

    return list(dict.fromkeys(references))


def _extract_provider_thread_id(message: dict, payload: dict) -> str | None:
    for candidate in (
        message.get("thread_id"),
        payload.get("thread_id"),
        message.get("threadId"),
        payload.get("threadId"),
        message.get("conversation_id"),
        payload.get("conversation_id"),
        payload.get("chat_id"),
    ):
        if candidate is None:
            continue
        normalized = str(candidate).strip()
        if normalized:
            return normalized
    return None


def _is_outbound_message_event(payload: dict) -> bool:
    event_type = _extract_event_type(payload)
    if event_type != "message_received":
        return False

    raw_sender = payload.get("sender")
    if isinstance(raw_sender, dict):
        sender = cast(dict[str, Any], raw_sender)
    else:
        sender = {}

    raw_account_info = payload.get("account_info")
    if isinstance(raw_account_info, dict):
        account_info = cast(dict[str, Any], raw_account_info)
    else:
        account_info = {}

    sender_provider_id = str(sender.get("attendee_provider_id") or "").strip()
    account_user_id = str(account_info.get("user_id") or "").strip()
    return bool(sender_provider_id and account_user_id and sender_provider_id == account_user_id)


async def _is_outbound_email_event(
    payload: dict,
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    sender_id: str,
) -> bool:
    if _extract_event_type(payload) != "mail_received":
        return False

    normalized_sender = _normalize_email_identity(sender_id)
    if not normalized_sender:
        return False

    result = await db.execute(
        select(EmailAccount.id)
        .where(
            EmailAccount.tenant_id == tenant_id,
            EmailAccount.is_active.is_(True),
            func.lower(EmailAccount.email_address) == normalized_sender,
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


def _normalize_email_identity(value: str | None) -> str:
    _display_name, address = parseaddr(value or "")
    normalized = (address or value or "").strip().lower()
    return normalized
