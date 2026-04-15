"""
schemas/content_inbound.py

Schemas do subsistema inbound do Content Hub: lead magnets, LPs e calculadora.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, TypeAlias

from pydantic import BaseModel, Field, field_validator

LeadMagnetType: TypeAlias = Literal["pdf", "calculator", "email_sequence", "link"]
LeadMagnetStatus: TypeAlias = Literal["draft", "active", "paused", "archived"]
LMPostType: TypeAlias = Literal["launch", "relaunch", "reminder"]
LMDistributionType: TypeAlias = Literal["comment", "dm", "link_bio"]
LMLeadOrigin: TypeAlias = Literal[
    "linkedin_comment",
    "linkedin_dm",
    "landing_page",
    "cold_outreach",
    "direct",
    "calculator",
]
LMSendPulseSyncStatus: TypeAlias = Literal["pending", "processing", "synced", "failed", "skipped"]
LMSequenceStatus: TypeAlias = Literal["pending", "active", "completed", "unsubscribed"]
CalculatorRole: TypeAlias = Literal["ceo", "cfo", "gerente", "analista", "operacional"]
CalculatorProcessType: TypeAlias = Literal[
    "financeiro", "juridico", "operacional", "atendimento", "rh"
]
CalculatorCompanySegment: TypeAlias = Literal[
    "clinicas", "industria", "advocacia", "contabilidade", "varejo", "servicos"
]
CalculatorCompanySize: TypeAlias = Literal["pequena", "media", "grande"]
CalculatorProcessAreaSpan: TypeAlias = Literal["1", "2-3", "4+"]


class ContentLeadMagnetCreate(BaseModel):
    type: LeadMagnetType
    title: str = Field(..., min_length=2, max_length=255)
    description: str | None = None
    status: LeadMagnetStatus = "draft"
    file_url: str | None = Field(default=None, max_length=2000)
    cta_text: str | None = Field(default=None, max_length=100)
    email_subject: str | None = Field(default=None, max_length=255)
    email_headline: str | None = Field(default=None, max_length=255)
    email_body_text: str | None = None
    email_cta_label: str | None = Field(default=None, max_length=100)
    sendpulse_list_id: str | None = Field(default=None, max_length=100)
    linked_calculator_id: uuid.UUID | None = None


class ContentLeadMagnetUpdate(BaseModel):
    type: LeadMagnetType | None = None
    title: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = None
    file_url: str | None = Field(default=None, max_length=2000)
    cta_text: str | None = Field(default=None, max_length=100)
    email_subject: str | None = Field(default=None, max_length=255)
    email_headline: str | None = Field(default=None, max_length=255)
    email_body_text: str | None = None
    email_cta_label: str | None = Field(default=None, max_length=100)
    sendpulse_list_id: str | None = Field(default=None, max_length=100)
    linked_calculator_id: uuid.UUID | None = None


class ContentLeadMagnetStatusUpdate(BaseModel):
    status: LeadMagnetStatus


class ContentLeadMagnetResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    type: LeadMagnetType
    title: str
    description: str | None
    status: LeadMagnetStatus
    file_url: str | None
    cta_text: str | None
    email_subject: str | None
    email_headline: str | None
    email_body_text: str | None
    email_cta_label: str | None
    sendpulse_list_id: str | None
    linked_calculator_id: uuid.UUID | None
    total_leads_captured: int
    total_downloads: int
    conversion_rate: float | None
    created_at: datetime
    updated_at: datetime


class ContentLMPostCreate(BaseModel):
    content_post_id: uuid.UUID | None = None
    post_type: LMPostType = "launch"
    distribution_type: LMDistributionType = "comment"
    trigger_word: str | None = Field(default=None, max_length=50)
    linkedin_post_urn: str | None = Field(default=None, max_length=100)
    published_at: datetime | None = None


class ContentLMPostResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    lead_magnet_id: uuid.UUID
    content_post_id: uuid.UUID | None
    post_type: LMPostType
    distribution_type: LMDistributionType
    trigger_word: str | None
    linkedin_post_urn: str | None
    comments_count: int
    dms_sent: int
    clicks_lp: int
    leads_from_post: int
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ContentLMLeadCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    email: str = Field(..., min_length=5, max_length=255)
    linkedin_profile_url: str | None = Field(default=None, max_length=500)
    company: str | None = Field(default=None, max_length=150)
    role: str | None = Field(default=None, max_length=150)
    phone: str | None = Field(default=None, max_length=30)
    origin: LMLeadOrigin = "direct"
    lm_post_id: uuid.UUID | None = None
    capture_metadata: dict[str, object] | None = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class ContentLMLeadResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    lead_magnet_id: uuid.UUID
    lm_post_id: uuid.UUID | None
    name: str
    email: str
    linkedin_profile_url: str | None
    company: str | None
    role: str | None
    phone: str | None
    origin: LMLeadOrigin
    capture_metadata: dict[str, object] | None
    sendpulse_list_id: str | None
    sendpulse_subscriber_id: str | None
    sendpulse_sync_status: LMSendPulseSyncStatus
    sendpulse_last_synced_at: datetime | None
    sendpulse_last_error: str | None
    sequence_status: LMSequenceStatus
    sequence_completed: bool
    converted_via_email: bool
    converted_to_lead: bool
    lead_id: uuid.UUID | None
    downloaded_at: datetime | None
    created_at: datetime
    updated_at: datetime


class LeadMagnetMetricsResponse(BaseModel):
    lead_magnet_id: uuid.UUID
    total_leads_captured: int
    total_synced_to_sendpulse: int
    total_sequence_completed: int
    total_converted_via_email: int
    total_unsubscribed: int
    total_opens: int
    total_clicks: int
    landing_page_views: int
    landing_page_submissions: int
    landing_page_conversion_rate: float | None
    qualified_conversion_rate: float | None


class ContentLMLeadConvertResponse(BaseModel):
    lm_lead_id: uuid.UUID
    lead_id: uuid.UUID


class ContentLandingPageUpsert(BaseModel):
    slug: str = Field(..., min_length=2, max_length=100)
    title: str = Field(..., min_length=2, max_length=255)
    subtitle: str | None = None
    hero_image_url: str | None = Field(default=None, max_length=2000)
    benefits: list[str] = Field(default_factory=list)
    social_proof_count: int = Field(default=0, ge=0)
    author_bio: str | None = None
    author_photo_url: str | None = Field(default=None, max_length=2000)
    meta_title: str | None = Field(default=None, max_length=255)
    meta_description: str | None = None
    publisher_name: str | None = Field(default=None, max_length=255)
    features: list[dict] | None = None
    expected_result: str | None = None
    badge_text: str | None = Field(default=None, max_length=500)
    published: bool = False


class ContentLandingPageResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    lead_magnet_id: uuid.UUID
    slug: str
    title: str
    subtitle: str | None
    hero_image_url: str | None
    benefits: list[str]
    social_proof_count: int
    author_bio: str | None
    author_photo_url: str | None
    meta_title: str | None
    meta_description: str | None
    publisher_name: str | None
    features: list[dict] | None
    expected_result: str | None
    badge_text: str | None
    published: bool
    total_views: int
    total_submissions: int
    conversion_rate: float | None
    created_at: datetime
    updated_at: datetime


class LandingPagePublicResponse(BaseModel):
    id: uuid.UUID
    lead_magnet_id: uuid.UUID
    lead_magnet_type: LeadMagnetType
    lead_magnet_title: str
    lead_magnet_description: str | None
    file_url: str | None
    cta_text: str | None
    slug: str
    title: str
    subtitle: str | None
    hero_image_url: str | None
    benefits: list[str]
    social_proof_count: int
    author_bio: str | None
    author_photo_url: str | None
    meta_title: str | None
    meta_description: str | None
    publisher_name: str | None
    features: list[dict] | None
    expected_result: str | None
    badge_text: str | None
    public_url: str


class LandingPagePublicCaptureRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    email: str = Field(..., min_length=5, max_length=255)
    company: str = Field(..., min_length=1, max_length=150)
    role: str = Field(..., min_length=1, max_length=150)
    phone: str = Field(..., min_length=1, max_length=30)
    linkedin_profile_url: str | None = Field(default=None, max_length=500)
    session_id: str | None = Field(default=None, max_length=100)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class LandingPagePublicCaptureResponse(BaseModel):
    lm_lead_id: uuid.UUID
    sendpulse_sync_status: LMSendPulseSyncStatus


class InvestmentRangeResponse(BaseModel):
    min: float
    max: float


class CalculatorConfigResponse(BaseModel):
    role_hourly_costs: dict[CalculatorRole, float]
    process_investment_ranges: dict[CalculatorProcessType, InvestmentRangeResponse]


class CalculatorCalculateRequest(BaseModel):
    lead_magnet_id: uuid.UUID | None = None
    pessoas: int = Field(..., ge=1, le=1000)
    horas_semana: float = Field(..., gt=0, le=168)
    custo_hora: float | None = Field(default=None, gt=0, le=5000)
    cargo: CalculatorRole
    retrabalho_pct: float = Field(..., ge=0, le=50)
    tipo_processo: CalculatorProcessType
    company_segment: CalculatorCompanySegment | None = None
    company_size: CalculatorCompanySize | None = None
    process_area_span: CalculatorProcessAreaSpan | None = None
    session_id: str | None = Field(default=None, max_length=100)


class CalculatorCalculateResponse(BaseModel):
    result_id: uuid.UUID
    custo_hora_sugerido: float
    custo_mensal: float
    custo_retrabalho: float
    custo_total_mensal: float
    custo_anual: float
    investimento_estimado_min: float
    investimento_estimado_max: float
    roi_estimado: float
    payback_meses: float
    mensagem_resultado: str


class CalculatorConvertRequest(BaseModel):
    result_id: uuid.UUID
    name: str = Field(..., min_length=2, max_length=150)
    email: str = Field(..., min_length=5, max_length=255)
    company: str = Field(..., min_length=1, max_length=150)
    role: str = Field(..., min_length=1, max_length=150)
    phone: str = Field(..., min_length=1, max_length=30)
    create_prospect: bool = True

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class CalculatorConvertResponse(BaseModel):
    result_id: uuid.UUID
    lm_lead_id: uuid.UUID | None
    lead_id: uuid.UUID | None
    sendpulse_sync_status: LMSendPulseSyncStatus | None
    diagnosis_email_sent: bool
    internal_notification_sent: bool


class CalculatorMetricsResponse(BaseModel):
    total_simulations: int
    total_captured_contacts: int
    total_converted_to_lead: int
    conversion_rate: float | None


# ── Landing Page — IA e Upload ────────────────────────────────────────


class LPImageUploadResponse(BaseModel):
    url: str


class LPImproveFieldRequest(BaseModel):
    field: Literal["title", "subtitle", "benefits", "meta_title", "meta_description", "features", "expected_result", "badge_text", "email_subject", "email_headline", "email_body_text", "email_cta_label"]
    current_value: str
    lead_magnet_title: str
    lead_magnet_type: str
    context: str | None = None


class LPImproveFieldResponse(BaseModel):
    improved: str
