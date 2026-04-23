"""
schemas/lead.py

Schemas Pydantic v2 para Lead — create, update e response.
"""

from __future__ import annotations

import math
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from models.enums import EmailType, LeadSource, LeadStatus


class LeadListSummary(BaseModel):
    """Resumo de lista associado a um lead."""

    id: uuid.UUID
    name: str


class LeadActiveCadenceSummary(BaseModel):
    """Resumo de cadência ativa associada ao lead."""

    id: uuid.UUID
    name: str


class LeadEmailInput(BaseModel):
    email: str = Field(..., min_length=3, max_length=254)
    email_type: EmailType = EmailType.UNKNOWN
    source: str | None = Field(default=None, max_length=100)
    verified: bool = False
    is_primary: bool = False

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class LeadEmailResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    email: str
    email_type: EmailType
    source: str | None
    verified: bool
    is_primary: bool
    created_at: datetime
    updated_at: datetime


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
    emails: list[LeadEmailInput] = Field(default_factory=list)
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
    emails: list[LeadEmailInput] | None = None
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
    emails: list[LeadEmailResponse] = Field(default_factory=list)
    phone: str | None
    enriched_at: datetime | None
    notes: str | None
    capture_query: str | None = None
    lead_lists: list[LeadListSummary] = Field(default_factory=list)
    origin_key: str = "manual"
    origin_label: str = "Manual"
    origin_detail: str | None = None
    active_cadence_count: int = 0
    active_cadences: list[LeadActiveCadenceSummary] = Field(default_factory=list)
    has_multiple_active_cadences: bool = False
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
    cadence_name: str | None = None
    step_number: int
    channel: str
    status: str
    item_kind: str = "cadence_step"
    use_voice: bool
    day_offset: int
    scheduled_at: datetime
    sent_at: datetime | None
    message_content: str | None = None
    reply_content: str | None = None
    reply_manual_task_id: uuid.UUID | None = None
    intent: str | None = None
    manual_task_id: uuid.UUID | None = None
    manual_task_type: str | None = None
    manual_task_detail: str | None = None
    notes: str | None = None


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
    list_id: uuid.UUID | None = None
    list_name: str | None = None


class LeadImportResponse(BaseModel):
    """Resultado da importação."""

    imported: int
    duplicates: int
    errors: list[str]
    list_id: uuid.UUID | None = None


class LeadMergeRequest(BaseModel):
    """Mescla vários leads em um lead principal."""

    primary_lead_id: uuid.UUID
    secondary_lead_ids: list[uuid.UUID] = Field(..., min_length=1)


class LeadMergeResponse(BaseModel):
    """Resultado da mesclagem de leads."""

    lead: LeadResponse
    merged_lead_ids: list[uuid.UUID]


class LeadGeneratedPreviewItem(BaseModel):
    """Lead normalizado em modo preview antes de salvar no banco."""

    preview_id: str
    name: str
    first_name: str | None = None
    last_name: str | None = None
    job_title: str | None = None
    company: str | None = None
    company_domain: str | None = None
    website: str | None = None
    industry: str | None = None
    company_size: str | None = None
    linkedin_url: str | None = None
    linkedin_profile_id: str | None = None
    city: str | None = None
    location: str | None = None
    segment: str | None = None
    phone: str | None = None
    email_corporate: str | None = None
    email_personal: str | None = None
    notes: str | None = None
    source: LeadSource
    origin_key: str
    origin_label: str


class LeadGenerationPreviewRequest(BaseModel):
    """Preview de geração de leads via Apify."""

    source: Literal["google_maps", "b2b_database", "linkedin_enrichment"]
    limit: int = Field(default=25, ge=1, le=200)
    search_terms: list[str] | None = None
    location_query: str | None = None
    categories: list[str] | None = None
    job_titles: list[str] | None = None
    locations: list[str] | None = None
    cities: list[str] | None = None
    industries: list[str] | None = None
    company_keywords: list[str] | None = None
    company_sizes: list[str] | None = None
    email_status: list[str] | None = None
    linkedin_urls: list[str] | None = None
    negative_terms: list[str] | None = None
    """Termos negativos: leads com qualquer desses termos no cargo ou keyword da empresa são descartados do preview."""

    @model_validator(mode="after")
    def validate_source_payload(self) -> LeadGenerationPreviewRequest:
        if self.source == "google_maps" and not (self.search_terms or self.location_query):
            raise ValueError("Informe ao menos termos de busca ou localização para Google Maps.")
        if self.source == "b2b_database" and not (
            self.job_titles
            or self.locations
            or self.cities
            or self.industries
            or self.company_keywords
        ):
            raise ValueError("Informe ao menos um filtro para a base B2B.")
        if self.source == "linkedin_enrichment" and not self.linkedin_urls:
            raise ValueError("Informe ao menos uma URL do LinkedIn para enriquecimento.")
        return self


class LeadGenerationPreviewResponse(BaseModel):
    """Preview normalizado da geração de leads."""

    source: str
    items: list[LeadGeneratedPreviewItem]
    total: int


class LeadGenerationImportRequest(BaseModel):
    """Importa os leads aprovados no preview."""

    source: Literal["google_maps", "b2b_database", "linkedin_enrichment"]
    items: list[LeadGeneratedPreviewItem] = Field(..., min_length=1, max_length=500)
    list_id: uuid.UUID | None = None
    create_list_name: str | None = Field(default=None, max_length=200)
    merge_duplicates: bool = True


class LeadGenerationImportResponse(BaseModel):
    """Resultado da importação da nova área de geração."""

    created: int
    updated: int
    duplicates: int
    list_id: uuid.UUID | None = None
    lead_ids: list[uuid.UUID]
