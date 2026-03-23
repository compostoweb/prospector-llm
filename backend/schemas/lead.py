"""
schemas/lead.py

Schemas Pydantic v2 para Lead — create, update e response.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from models.enums import LeadSource, LeadStatus


class LeadCreateRequest(BaseModel):
    """Criação manual de lead (canal: api ou import)."""

    name: str = Field(..., min_length=2, max_length=300)
    company: str | None = Field(default=None, max_length=300)
    website: str | None = None
    linkedin_url: str | None = None
    city: str | None = Field(default=None, max_length=150)
    segment: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=30)
    email_corporate: str | None = None
    email_personal: str | None = None
    notes: str | None = None
    source: LeadSource = LeadSource.MANUAL

    @field_validator("linkedin_url")
    @classmethod
    def validate_linkedin_url(cls, v: str | None) -> str | None:
        if v and "linkedin.com" not in v:
            raise ValueError("linkedin_url deve ser uma URL válida do LinkedIn")
        return v


class LeadUpdateRequest(BaseModel):
    """Atualização parcial de lead (todos os campos opcionais)."""

    name: str | None = Field(default=None, min_length=2, max_length=300)
    company: str | None = None
    website: str | None = None
    linkedin_url: str | None = None
    city: str | None = None
    segment: str | None = None
    phone: str | None = None
    email_corporate: str | None = None
    email_personal: str | None = None
    notes: str | None = None
    status: LeadStatus | None = None


class LeadEnrollRequest(BaseModel):
    """Inscreve um lead em uma cadência."""
    cadence_id: uuid.UUID


class LeadResponse(BaseModel):
    """Representação completa de um lead na API."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    company: str | None
    website: str | None
    linkedin_url: str | None
    linkedin_profile_id: str | None
    city: str | None
    segment: str | None
    source: LeadSource
    status: LeadStatus
    score: float | None
    email_corporate: str | None
    email_corporate_source: str | None
    email_corporate_verified: bool
    email_personal: str | None
    email_personal_source: str | None
    phone: str | None
    enriched_at: datetime | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class LeadListResponse(BaseModel):
    """Paginação de leads."""
    items: list[LeadResponse]
    total: int
    page: int
    page_size: int
