"""
schemas/lead.py

Schemas Pydantic v2 para Lead — create, update e response.
"""

from __future__ import annotations

import math
import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from models.enums import LeadSource, LeadStatus


class LeadCreateRequest(BaseModel):
    """Criação manual de lead (canal: api ou import)."""

    name: str = Field(..., min_length=2, max_length=300)
    first_name: str | None = Field(default=None, max_length=150)
    last_name: str | None = Field(default=None, max_length=150)
    job_title: str | None = Field(default=None, max_length=200)
    company: str | None = Field(default=None, max_length=300)
    company_domain: str | None = None
    website: str | None = None
    industry: str | None = Field(default=None, max_length=200)
    company_size: str | None = Field(default=None, max_length=50)
    linkedin_url: str | None = None
    city: str | None = Field(default=None, max_length=150)
    location: str | None = Field(default=None, max_length=300)
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
    first_name: str | None = None
    last_name: str | None = None
    job_title: str | None = None
    company: str | None = None
    company_domain: str | None = None
    website: str | None = None
    industry: str | None = None
    company_size: str | None = None
    linkedin_url: str | None = None
    city: str | None = None
    location: str | None = None
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
    first_name: str | None
    last_name: str | None
    job_title: str | None
    company: str | None
    company_domain: str | None
    website: str | None
    industry: str | None
    company_size: str | None
    linkedin_url: str | None
    linkedin_profile_id: str | None
    linkedin_connection_status: str | None = None
    linkedin_connected_at: datetime | None = None
    city: str | None
    location: str | None
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
    pages: int = 0

    @model_validator(mode="after")
    def _compute_pages(self) -> LeadListResponse:
        if self.page_size > 0:
            self.pages = math.ceil(self.total / self.page_size)
        return self


class LeadStepResponse(BaseModel):
    """Step de cadência formatado para o timeline do lead."""
    model_config = {"from_attributes": True}

    id: uuid.UUID
    lead_id: uuid.UUID
    cadence_id: uuid.UUID
    step_number: int
    channel: str
    status: str
    use_voice: bool
    day_offset: int
    scheduled_at: datetime
    sent_at: datetime | None
    message_content: str | None = None
    reply_content: str | None = None
    intent: str | None = None


class LeadImportItem(BaseModel):
    """Item individual de importação de leads."""
    name: str = Field(..., min_length=2, max_length=300)
    first_name: str | None = Field(default=None, max_length=150)
    last_name: str | None = Field(default=None, max_length=150)
    job_title: str | None = Field(default=None, max_length=200)
    company: str | None = Field(default=None, max_length=300)
    company_domain: str | None = None
    website: str | None = None
    industry: str | None = Field(default=None, max_length=200)
    company_size: str | None = Field(default=None, max_length=50)
    linkedin_url: str | None = None
    city: str | None = Field(default=None, max_length=150)
    location: str | None = Field(default=None, max_length=300)
    segment: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=30)
    email_corporate: str | None = None
    email_personal: str | None = None
    notes: str | None = None

    @field_validator("linkedin_url")
    @classmethod
    def validate_linkedin_url(cls, v: str | None) -> str | None:
        if v and "linkedin.com" not in v:
            raise ValueError("linkedin_url deve ser uma URL válida do LinkedIn")
        return v


class LeadImportRequest(BaseModel):
    """Requisição de importação em lote."""
    items: list[LeadImportItem] = Field(..., min_length=1, max_length=5000)


class LeadImportResponse(BaseModel):
    """Resultado da importação."""
    imported: int
    duplicates: int
    errors: list[str]
