"""
api/routes/content/sendpulse_test.py

Endpoints de diagnóstico da integração SendPulse.
Todos autenticados — uso exclusivo do painel administrativo.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

import structlog
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_effective_tenant_id, get_session_flexible
from api.webhooks.sendpulse import (
    _EVENT_ALIASES,
    _apply_event_to_lm_lead,
    _canonical_json,
    _find_lead_magnet,
    _find_lm_lead,
)
from integrations.sendpulse_client import SendPulseClient, SendPulseClientError
from models.content_lm_email_event import ContentLMEmailEvent

logger = structlog.get_logger()

router = APIRouter(prefix="/sendpulse", tags=["Content Hub — SendPulse Tests"])

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class SendPulseConnectionResult(BaseModel):
    status: Literal["ok", "error"]
    message: str
    lists: list[dict[str, Any]] | None = None


class TestWebhookRequest(BaseModel):
    event_type: Literal["subscribe", "open", "click", "unsubscribe", "sequence_completed"]
    email: str = Field(..., min_length=5, max_length=255)
    list_id: str | None = Field(default=None, max_length=100)
    link_url: str | None = Field(default=None, max_length=2000)


class TestWebhookResult(BaseModel):
    status: Literal["ok", "ignored"]
    lm_lead_updated: bool
    event_stored: bool
    event_id: uuid.UUID | None = None
    message: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/test-connection",
    response_model=SendPulseConnectionResult,
    status_code=status.HTTP_200_OK,
    summary="Testa credenciais e lista addressbooks do SendPulse",
)
async def test_sendpulse_connection(
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
) -> SendPulseConnectionResult:
    client = SendPulseClient()
    try:
        token = await client.get_access_token()
        if not token:
            return SendPulseConnectionResult(
                status="error",
                message="Não foi possível obter access token. Verifique SENDPULSE_CLIENT_ID/SENDPULSE_CLIENT_SECRET ou SENDPULSE_API_KEY.",
            )
        lists = await client.list_addressbooks()
        return SendPulseConnectionResult(
            status="ok",
            message=f"Conexão OK. {len(lists)} lista(s) encontrada(s).",
            lists=lists,
        )
    except SendPulseClientError as exc:
        logger.warning(
            "sendpulse.test_connection.failed",
            tenant_id=str(tenant_id),
            error=str(exc),
        )
        return SendPulseConnectionResult(status="error", message=str(exc))


@router.post(
    "/test-webhook",
    response_model=TestWebhookResult,
    status_code=status.HTTP_200_OK,
    summary="Simula processamento de um evento webhook do SendPulse (sem HMAC)",
)
async def test_sendpulse_webhook(
    body: TestWebhookRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> TestWebhookResult:
    # Constrói payload sintético
    payload: dict[str, Any] = {
        "event": body.event_type,
        "email": body.email,
    }
    if body.list_id:
        payload["list_id"] = body.list_id
    if body.link_url:
        payload["link"] = body.link_url

    # Normaliza o tipo de evento (pode receber alias)
    raw = body.event_type.strip().lower()
    event_type = _EVENT_ALIASES.get(raw, raw)

    # Deduplicação: ignora se evento sintético idêntico já foi processado
    payload_hash = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    duplicate_check = await db.execute(
        select(ContentLMEmailEvent.id).where(
            ContentLMEmailEvent.provider == "sendpulse",
            ContentLMEmailEvent.payload_hash == payload_hash,
        )
    )
    if duplicate_check.scalar_one_or_none() is not None:
        return TestWebhookResult(
            status="ok",
            lm_lead_updated=False,
            event_stored=False,
            message="Evento duplicado ignorado (payload idêntico já registrado).",
        )

    lm_lead = await _find_lm_lead(
        db,
        email=body.email.strip().lower(),
        list_id=body.list_id,
        subscriber_id=None,
    )
    lead_magnet = await _find_lead_magnet(db, list_id=body.list_id, lm_lead=lm_lead)

    if lm_lead is None and lead_magnet is None:
        logger.info(
            "sendpulse.test_webhook.ignored",
            email=body.email,
            list_id=body.list_id,
            event_type=event_type,
            tenant_id=str(tenant_id),
        )
        return TestWebhookResult(
            status="ignored",
            lm_lead_updated=False,
            event_stored=False,
            message="Nenhum ContentLMLead ou ContentLeadMagnet encontrado para este email/lista.",
        )

    event_tenant_id = lm_lead.tenant_id if lm_lead else lead_magnet.tenant_id
    event = ContentLMEmailEvent(
        tenant_id=event_tenant_id,
        lead_magnet_id=lead_magnet.id
        if lead_magnet
        else (lm_lead.lead_magnet_id if lm_lead else None),
        lm_lead_id=lm_lead.id if lm_lead else None,
        provider="sendpulse",
        provider_event_id=None,
        payload_hash=payload_hash,
        event_type=event_type,
        event_timestamp=datetime.now(UTC),
        link_url=body.link_url,
        payload=payload,
        processed_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )
    db.add(event)

    lead_updated = False
    if lm_lead is not None:
        _apply_event_to_lm_lead(lm_lead, event_type=event_type, link_url=body.link_url)
        lead_updated = True

    await db.commit()
    await db.refresh(event)

    logger.info(
        "sendpulse.test_webhook.processed",
        event_type=event_type,
        lm_lead_id=str(lm_lead.id) if lm_lead else None,
        tenant_id=str(tenant_id),
    )
    return TestWebhookResult(
        status="ok",
        lm_lead_updated=lead_updated,
        event_stored=True,
        event_id=event.id,
        message=f"Evento '{event_type}' processado com sucesso.",
    )
