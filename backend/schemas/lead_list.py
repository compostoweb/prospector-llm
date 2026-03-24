"""
schemas/lead_list.py

Schemas Pydantic v2 para LeadList — criação, atualização e resposta.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class LeadListCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=500)


class LeadListUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None


class LeadListResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str | None
    lead_count: int = 0
    created_at: datetime
    updated_at: datetime


class LeadListMembersRequest(BaseModel):
    """Adicionar ou remover leads de uma lista."""
    lead_ids: list[uuid.UUID] = Field(..., min_length=1)
