"""
schemas/lead_list.py

Schemas Pydantic v2 para LeadList — criação, atualização e resposta.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


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


class LeadListLeadItem(BaseModel):
    """Representação resumida de um lead dentro de uma lista."""
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    job_title: str | None = None
    company: str | None = None
    email_corporate: str | None = None
    linkedin_url: str | None = None
    status: str = "raw"


class LeadListDetailResponse(BaseModel):
    """Resposta detalhada de uma lista — inclui os leads membros."""
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str | None
    lead_count: int = 0
    leads: list[LeadListLeadItem] = []
    created_at: datetime
    updated_at: datetime

    @field_validator("leads", mode="before")
    @classmethod
    def coerce_none_leads(cls, v: list | None) -> list:
        return v if v is not None else []


class LeadListMembersRequest(BaseModel):
    """Adicionar ou remover leads de uma lista."""
    lead_ids: list[uuid.UUID] = Field(..., min_length=1)
