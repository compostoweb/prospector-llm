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
    channel: Channel
    direction: str           # "outbound" | "inbound"
    content_text: str | None
    content_audio_url: str | None
    intent: Intent | None
    unipile_message_id: str | None
    opened: bool
    created_at: datetime


class InteractionListResponse(BaseModel):
    """Paginação de interações de um lead."""
    items: list[InteractionResponse]
    total: int
