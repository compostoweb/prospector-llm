"""
schemas/sandbox.py

Schemas Pydantic v2 para o sistema de sandbox de cadências.
Inclui request/response para criação, geração, aprovação,
simulação de replies, rate limits e Pipedrive dry-run.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from models.enums import (
    Channel,
    Intent,
    SandboxLeadSource,
    SandboxRunStatus,
    SandboxStepStatus,
)

# ── Dados de lead fictício ────────────────────────────────────────────


class FictitiousLeadData(BaseModel):
    """Dados de um lead fictício gerado para o sandbox."""

    name: str
    company: str
    job_title: str
    email: str | None = None
    linkedin_url: str | None = None
    industry: str | None = None
    city: str | None = None
    website: str | None = None


# ── Request schemas ───────────────────────────────────────────────────


class SandboxCreateRequest(BaseModel):
    """Criar um sandbox run para uma cadência."""

    lead_ids: list[uuid.UUID] | None = Field(
        default=None,
        description="IDs de leads reais para usar no sandbox. Mutualmente exclusivo com use_fictitious.",
    )
    lead_count: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Quantidade de leads para amostra aleatória ou fictícios.",
    )
    use_fictitious: bool = Field(
        default=False,
        description="Gerar leads fictícios ao invés de usar reais.",
    )


class SandboxRegenerateRequest(BaseModel):
    """Request para regenerar um step do sandbox (override de temperatura opcional)."""

    temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Override de temperatura para esta geração.",
    )


class SimulateReplyRequest(BaseModel):
    """Request para simular uma resposta inbound."""

    mode: str = Field(
        ...,
        pattern="^(auto|manual)$",
        description="Modo: 'auto' (LLM gera reply) ou 'manual' (texto fornecido).",
    )
    reply_text: str | None = Field(
        default=None,
        description="Texto da resposta manual. Obrigatório quando mode='manual'.",
    )


# ── Response schemas ──────────────────────────────────────────────────


class CompositionContextResponse(BaseModel):
    """Metadados de observabilidade usados pelo AI Composer."""

    generation_mode: str
    step_key: str
    copy_method: str | None
    playbook_sector: str | None
    playbook_role: str | None
    matched_role: str | None
    few_shot_applied: bool
    few_shot_key: str | None
    few_shot_method: str | None
    has_site_summary: bool
    has_recent_posts: bool


class SandboxStepResponse(BaseModel):
    """Representação de um step do sandbox na API."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    sandbox_run_id: uuid.UUID
    lead_id: uuid.UUID | None
    fictitious_lead_data: FictitiousLeadData | None = None
    step_number: int
    channel: Channel
    day_offset: int
    use_voice: bool
    step_type: str | None = None
    scheduled_at_preview: datetime
    message_content: str | None
    audio_preview_url: str | None
    email_subject: str | None
    status: SandboxStepStatus

    # Info LLM
    llm_provider: str | None
    llm_model: str | None
    tokens_in: int | None
    tokens_out: int | None
    composition_context: CompositionContextResponse | None = None

    # Simulação de reply
    simulated_reply: str | None
    simulated_intent: Intent | None
    simulated_confidence: float | None
    simulated_reply_summary: str | None

    # Rate limit
    is_rate_limited: bool
    rate_limit_reason: str | None
    adjusted_scheduled_at: datetime | None

    # Timestamps
    created_at: datetime
    updated_at: datetime


class SandboxRunResponse(BaseModel):
    """Representação completa de um sandbox run na API."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    cadence_id: uuid.UUID
    status: SandboxRunStatus
    lead_source: SandboxLeadSource
    pipedrive_dry_run: dict | None = None
    steps: list[SandboxStepResponse] = []
    created_at: datetime
    updated_at: datetime


class SandboxRunListResponse(BaseModel):
    """Lista de sandbox runs (sem steps para listagem)."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    cadence_id: uuid.UUID
    status: SandboxRunStatus
    lead_source: SandboxLeadSource
    steps_count: int = 0
    created_at: datetime


class SandboxApproveResponse(BaseModel):
    """Resultado da aprovação de um run."""

    sandbox_run_id: uuid.UUID
    status: SandboxRunStatus
    steps_approved: int


class SandboxStartResponse(BaseModel):
    """Resultado do start real da cadência a partir do sandbox."""

    sandbox_run_id: uuid.UUID
    cadence_id: uuid.UUID
    leads_enrolled: int
    steps_created: int


class PipedrivePersonPreview(BaseModel):
    """Preview de pessoa no Pipedrive."""

    name: str
    email: str | None
    person_exists: bool
    person_id: int | None = None


class PipedriveDealPreview(BaseModel):
    """Preview de deal no Pipedrive."""

    title: str
    stage: str
    value: float = 0.0


class PipedriveLeadPreview(BaseModel):
    """Preview completo de um lead no Pipedrive dry-run."""

    lead_name: str
    lead_company: str | None
    intent: Intent | None
    person: PipedrivePersonPreview
    deal: PipedriveDealPreview
    note_preview: str


class PipedriveDryRunResponse(BaseModel):
    """Resultado do dry-run do Pipedrive."""

    sandbox_run_id: uuid.UUID
    leads: list[PipedriveLeadPreview]


class PipedrivePushLeadResult(BaseModel):
    """Resultado do push real de um lead no Pipedrive."""

    lead_name: str
    person_id: int | None = None
    deal_id: int | None = None
    note_added: bool = False
    error: str | None = None


class PipedrivePushResponse(BaseModel):
    """Resultado do push real ao Pipedrive."""

    sandbox_run_id: uuid.UUID
    pushed: int = 0
    errors: int = 0
    results: list[PipedrivePushLeadResult] = []
