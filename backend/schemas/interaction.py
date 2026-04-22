"""
schemas/interaction.py

Schemas Pydantic v2 para Interaction — somente resposta (criado internamente).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from models.enums import Channel, Intent


class InteractionResponse(BaseModel):
    """Representação de uma interação (enviada ou recebida) na API."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    lead_id: uuid.UUID
    tenant_id: uuid.UUID
    cadence_step_id: uuid.UUID | None
    channel: Channel
    direction: str  # "outbound" | "inbound"
    content_text: str | None
    content_audio_url: str | None
    intent: Intent | None
    unipile_message_id: str | None
    email_message_id: str | None
    provider_thread_id: str | None
    reply_match_status: str | None
    reply_match_source: str | None
    reply_match_sent_cadence_count: int | None
    reply_reviewed_at: datetime | None
    opened: bool
    created_at: datetime


class InteractionLinkReplyAuditRequest(BaseModel):
    """Payload para vincular manualmente um reply auditado a um cadence step."""

    cadence_step_id: uuid.UUID


class InteractionListResponse(BaseModel):
    """Paginação de interações de um lead."""

    items: list[InteractionResponse]
    total: int
