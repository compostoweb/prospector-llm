"""
api/webhooks/sendpulse.py

Webhook do SendPulse para métricas e mudanças de estado do funil inbound.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_session_no_auth
from core.config import settings
from models.content_lead_magnet import ContentLeadMagnet
from models.content_lm_email_event import ContentLMEmailEvent
from models.content_lm_lead import ContentLMLead
from services.content.lead_magnet_service import normalize_email

logger = structlog.get_logger()

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

_EVENT_ALIASES = {
    "email_subscribed": "subscribe",
    "subscribed": "subscribe",
    "subscribe": "subscribe",
    "email_opened": "open",
    "opened": "open",
    "open": "open",
    "email_clicked": "click",
    "clicked": "click",
    "click": "click",
    "email_unsubscribed": "unsubscribe",
    "unsubscribed": "unsubscribe",
    "unsubscribe": "unsubscribe",
    "automation_completed": "sequence_completed",
    "completed": "sequence_completed",
    "sequence_completed": "sequence_completed",
}


@router.post("/sendpulse", status_code=status.HTTP_200_OK)
async def sendpulse_webhook(
    request: Request,
    db: AsyncSession = Depends(get_session_no_auth),
) -> dict:
    body = await request.body()
    signature_header = request.headers.get("X-SendPulse-Signature") or request.headers.get("X-Signature", "")
    if not _verify_signature(body, signature_header):
        logger.warning("webhook.sendpulse.invalid_signature")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Assinatura inválida")

    try:
        payload = json.loads(body)
    except Exception as exc:  # noqa: BLE001
        logger.warning("webhook.sendpulse.invalid_json", error=str(exc))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payload inválido")

    payload_hash = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    duplicate_check = await db.execute(
        select(ContentLMEmailEvent.id).where(
            ContentLMEmailEvent.provider == "sendpulse",
            ContentLMEmailEvent.payload_hash == payload_hash,
        )
    )
    if duplicate_check.scalar_one_or_none() is not None:
        return {"status": "duplicate"}

    event_type = _normalize_event_type(payload)
    email = _extract_email(payload)
    list_id = _extract_list_id(payload)
    subscriber_id = _extract_subscriber_id(payload)
    link_url = _extract_link_url(payload)
    event_timestamp = _extract_event_timestamp(payload)

    lm_lead = await _find_lm_lead(
        db,
        email=email,
        list_id=list_id,
        subscriber_id=subscriber_id,
    )
    lead_magnet = await _find_lead_magnet(db, list_id=list_id, lm_lead=lm_lead)

    if lm_lead is None and lead_magnet is None:
        logger.info("webhook.sendpulse.ignored", event_type=event_type, email=email, list_id=list_id)
        return {"status": "ignored"}

    tenant_id = lm_lead.tenant_id if lm_lead else lead_magnet.tenant_id
    event = ContentLMEmailEvent(
        tenant_id=tenant_id,
        lead_magnet_id=lead_magnet.id if lead_magnet else (lm_lead.lead_magnet_id if lm_lead else None),
        lm_lead_id=lm_lead.id if lm_lead else None,
        provider="sendpulse",
        provider_event_id=subscriber_id,
        payload_hash=payload_hash,
        event_type=event_type,
        event_timestamp=event_timestamp,
        link_url=link_url,
        payload=payload,
        processed_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )
    db.add(event)

    if lm_lead is not None:
        _apply_event_to_lm_lead(lm_lead, event_type=event_type, link_url=link_url)

    await db.commit()
    logger.info("webhook.sendpulse.processed", event_type=event_type, lm_lead_id=str(lm_lead.id) if lm_lead else None)
    return {"status": "ok"}


def _verify_signature(body: bytes, signature_header: str) -> bool:
    secret = settings.SENDPULSE_WEBHOOK_SECRET
    if not secret:
        if settings.ENV == "dev":
            logger.warning("webhook.sendpulse.secret_not_configured")
            return True
        return False
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, signature_header)


def _canonical_json(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _normalize_event_type(payload: dict) -> str:
    raw = str(payload.get("event") or payload.get("event_type") or payload.get("type") or "unknown")
    normalized = raw.strip().lower()
    return _EVENT_ALIASES.get(normalized, normalized)


def _extract_email(payload: dict) -> str | None:
    candidate = payload.get("email")
    if candidate is None and isinstance(payload.get("subscriber"), dict):
        candidate = payload["subscriber"].get("email")
    if candidate is None and isinstance(payload.get("data"), dict):
        candidate = payload["data"].get("email")
    return normalize_email(str(candidate)) if candidate else None


def _extract_list_id(payload: dict) -> str | None:
    for key in ("list_id", "book_id", "addressbook_id"):
        value = payload.get(key)
        if value:
            return str(value)
    if isinstance(payload.get("data"), dict):
        for key in ("list_id", "book_id", "addressbook_id"):
            value = payload["data"].get(key)
            if value:
                return str(value)
    return None


def _extract_subscriber_id(payload: dict) -> str | None:
    for key in ("subscriber_id", "id", "contact_id", "event_id"):
        value = payload.get(key)
        if value:
            return str(value)
    if isinstance(payload.get("subscriber"), dict):
        for key in ("subscriber_id", "id", "contact_id"):
            value = payload["subscriber"].get(key)
            if value:
                return str(value)
    return None


def _extract_link_url(payload: dict) -> str | None:
    for key in ("link", "url", "link_url"):
        value = payload.get(key)
        if value:
            return str(value)
    if isinstance(payload.get("data"), dict):
        for key in ("link", "url", "link_url"):
            value = payload["data"].get(key)
            if value:
                return str(value)
    return None


def _extract_event_timestamp(payload: dict) -> datetime | None:
    raw_value = payload.get("event_timestamp") or payload.get("timestamp") or payload.get("created_at")
    if raw_value is None:
        return None
    try:
        value = str(raw_value).replace("Z", "+00:00")
        return datetime.fromisoformat(value)
    except ValueError:
        return None


async def _find_lm_lead(
    db: AsyncSession,
    *,
    email: str | None,
    list_id: str | None,
    subscriber_id: str | None,
) -> ContentLMLead | None:
    if subscriber_id:
        result = await db.execute(
            select(ContentLMLead).where(ContentLMLead.sendpulse_subscriber_id == subscriber_id)
        )
        lm_lead = result.scalar_one_or_none()
        if lm_lead is not None:
            return lm_lead

    if email:
        stmt = select(ContentLMLead).where(ContentLMLead.email == email)
        if list_id:
            stmt = stmt.where(ContentLMLead.sendpulse_list_id == list_id)
        result = await db.execute(stmt.order_by(ContentLMLead.created_at.desc()))
        return result.scalars().first()

    return None


async def _find_lead_magnet(
    db: AsyncSession,
    *,
    list_id: str | None,
    lm_lead: ContentLMLead | None,
) -> ContentLeadMagnet | None:
    if lm_lead is not None:
        result = await db.execute(
            select(ContentLeadMagnet).where(ContentLeadMagnet.id == lm_lead.lead_magnet_id)
        )
        return result.scalar_one_or_none()

    if list_id:
        result = await db.execute(
            select(ContentLeadMagnet).where(ContentLeadMagnet.sendpulse_list_id == list_id)
        )
        return result.scalar_one_or_none()

    return None


def _apply_event_to_lm_lead(
    lm_lead: ContentLMLead,
    *,
    event_type: str,
    link_url: str | None,
) -> None:
    if event_type in {"subscribe", "open"} and lm_lead.sequence_status == "pending":
        lm_lead.sequence_status = "active"
    elif event_type == "unsubscribe":
        lm_lead.sequence_status = "unsubscribed"
    elif event_type == "sequence_completed":
        lm_lead.sequence_status = "completed"
        lm_lead.sequence_completed = True
    elif event_type == "click" and link_url and "diagnostico" in link_url.lower():
        lm_lead.converted_via_email = True