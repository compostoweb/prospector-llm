"""
schemas/cadence.py

Schemas Pydantic v2 para create/update de Cadence.
Inclui validação do par provider+model e valores de LLM.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from models.enums import CadenceMode, Channel, StepType
from schemas.lead import LeadResponse

# Combinações válidas: provider → lista de prefixos de model aceitos
# Serve para validação básica — a lista completa vem da API dos providers
_VALID_PROVIDERS = {"openai", "gemini", "anthropic", "openrouter"}

_PROVIDER_MODEL_PREFIXES: dict[str, tuple[str, ...]] = {
    "openai": ("gpt-", "o1", "o3", "o4"),
    "gemini": ("gemini-",),
    "anthropic": ("claude-",),
    "openrouter": (),  # OpenRouter aceita qualquer modelo — validação dinâmica
}

_MANUAL_TASK_TYPES = {
    "call",
    "linkedin_post_comment",
    "whatsapp",
    "other",
}


class LLMConfigSchema(BaseModel):
    """Configuração de LLM para uma cadência."""

    provider: str = Field(
        default="openai",
        description="Provedor LLM: openai | gemini | anthropic",
    )
    model: str = Field(
        default="gpt-5.4-mini",
        description="ID do modelo. Ex: gpt-5.4-mini, gemini-2.5-flash, claude-haiku-4-5",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Temperatura de geração (0.0–1.0)",
    )
    max_tokens: int = Field(
        default=1024,
        ge=64,
        le=8192,
        description="Máximo de tokens por geração",
    )

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        if v not in _VALID_PROVIDERS:
            raise ValueError(f"Provider '{v}' inválido. Use: {sorted(_VALID_PROVIDERS)}")
        return v

    @model_validator(mode="after")
    def validate_model_matches_provider(self) -> LLMConfigSchema:
        prefixes = _PROVIDER_MODEL_PREFIXES.get(self.provider, ())
        if prefixes and not any(self.model.startswith(p) for p in prefixes):
            raise ValueError(
                f"Modelo '{self.model}' não parece pertencer ao provider '{self.provider}'. "
                f"Prefixos esperados: {prefixes}"
            )
        return self


class StepLayoutMetadata(BaseModel):
    """Metadados de posicionamento visual do step no editor."""

    x: float = Field(default=0.0, description="Posição X do nó no canvas")
    y: float = Field(default=0.0, description="Posição Y do nó no canvas")


class StepTemplateItem(BaseModel):
    """Um step dentro do template customizado de cadência."""

    channel: Channel
    day_offset: int = Field(..., ge=0, le=90, description="Dias após enrollment")
    message_template: str | None = Field(
        default=None, description="Template de mensagem com variáveis"
    )
    use_voice: bool = Field(default=False, description="Enviar voice note (só linkedin_dm)")
    audio_file_id: str | None = Field(
        default=None,
        description="ID do áudio pré-gravado (S3). Se preenchido, usa esse áudio ao invés de TTS.",
    )
    step_type: StepType | None = Field(
        default=None,
        description=(
            "Tipo de instrução para geração de conteúdo. "
            "NULL = inferência automática baseada no canal, posição e contexto."
        ),
    )
    # A/B testing de assunto (só canal EMAIL)
    subject_variants: list[str] | None = Field(
        default=None,
        max_length=10,
        description="Variações de assunto para A/B testing (2–4 opções). Só canal EMAIL.",
    )
    # Template salvo (substitui LLM para o corpo do e-mail)
    email_template_id: str | None = Field(
        default=None,
        description="ID de EmailTemplate salvo. Se preenchido, usa o corpo do template ao invés de LLM.",
    )
    layout: StepLayoutMetadata | None = Field(
        default=None,
        description="Posição visual persistida do step no editor ReactFlow.",
    )
    manual_task_type: str | None = Field(
        default=None,
        description=(
            "Tipo operacional da tarefa manual: call | linkedin_post_comment | whatsapp | other. "
            "Só para channel=manual_task."
        ),
    )
    manual_task_detail: str | None = Field(
        default=None,
        max_length=1000,
        description="Detalhamento/instruções da tarefa manual. Só para channel=manual_task.",
    )

    @model_validator(mode="after")
    def voice_only_for_dm(self) -> StepTemplateItem:
        if self.use_voice and self.channel != Channel.LINKEDIN_DM:
            raise ValueError("use_voice só é permitido para linkedin_dm")
        if self.audio_file_id and not self.use_voice:
            # Se tem audio_file_id, force use_voice=True
            self.use_voice = True
        return self

    @model_validator(mode="after")
    def step_type_matches_channel(self) -> StepTemplateItem:
        """Valida que o step_type é compatível com o canal selecionado."""
        if self.step_type is None:
            return self

        valid_by_channel: dict[Channel, set[StepType]] = {
            Channel.LINKEDIN_CONNECT: {StepType.LINKEDIN_CONNECT},
            Channel.LINKEDIN_DM: {
                StepType.LINKEDIN_DM_FIRST,
                StepType.LINKEDIN_DM_POST_CONNECT,
                StepType.LINKEDIN_DM_POST_CONNECT_VOICE,
                StepType.LINKEDIN_DM_VOICE,
                StepType.LINKEDIN_DM_FOLLOWUP,
                StepType.LINKEDIN_DM_BREAKUP,
            },
            Channel.EMAIL: {
                StepType.EMAIL_FIRST,
                StepType.EMAIL_FOLLOWUP,
                StepType.EMAIL_BREAKUP,
            },
        }
        allowed = valid_by_channel.get(self.channel, set())
        if self.step_type not in allowed:
            allowed_names = sorted(s.value for s in allowed) if allowed else ["nenhum"]
            raise ValueError(
                f"step_type '{self.step_type.value}' não é compatível com canal '{self.channel.value}'. "
                f"Opções válidas: {allowed_names}"
            )
        return self

    @model_validator(mode="after")
    def manual_task_fields_match_channel(self) -> StepTemplateItem:
        if self.manual_task_type and self.channel != Channel.MANUAL_TASK:
            raise ValueError("manual_task_type só é permitido para channel=manual_task")
        if self.manual_task_detail and self.channel != Channel.MANUAL_TASK:
            raise ValueError("manual_task_detail só é permitido para channel=manual_task")
        if self.manual_task_type and self.manual_task_type not in _MANUAL_TASK_TYPES:
            allowed = sorted(_MANUAL_TASK_TYPES)
            raise ValueError(f"manual_task_type '{self.manual_task_type}' inválido. Use: {allowed}")
        return self


class CadenceCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    description: str | None = None
    allow_personal_email: bool = False
    # Novas cadências nascem pausadas; a ativação ocorre via PATCH /cadences/{id}
    mode: CadenceMode = Field(
        default=CadenceMode.AUTOMATIC,
        description="Modo: automatic | semi_manual",
    )
    cadence_type: str = Field(
        default="mixed",
        description="Tipo: mixed | email_only. email_only força todos os steps no canal EMAIL.",
    )

    # Configuração LLM — se não informado, usa o padrão do tenant
    llm: LLMConfigSchema | None = None

    # Configuração TTS — se não informado, usa fallback global (VOICE_PROVIDER)
    tts_provider: str | None = Field(
        default=None,
        description="Provedor TTS: speechify | voicebox. NULL = default global.",
    )
    tts_voice_id: str | None = Field(
        default=None,
        description="ID da voz/profile TTS. NULL = default do provider.",
    )
    tts_speed: float = Field(
        default=1.0,
        ge=0.5,
        le=2.0,
        description="Velocidade da fala TTS (0.5–2.0). 1.0 = normal.",
    )
    tts_pitch: float = Field(
        default=0.0,
        ge=-50.0,
        le=50.0,
        description="Entonação/pitch TTS (-50 a +50%). 0 = normal.",
    )
    lead_list_id: str | None = Field(
        default=None,
        description="ID da lista de leads a usar nesta cadência. NULL = nenhuma.",
    )
    email_account_id: str | None = Field(
        default=None,
        description="ID da conta de e-mail preferencial para steps EMAIL. NULL = usa Unipile global.",
    )
    linkedin_account_id: str | None = Field(
        default=None,
        description="ID da conta LinkedIn preferencial para steps LinkedIn. NULL = usa Unipile global.",
    )

    # Contexto de prospecção (alimenta prompts da IA)
    target_segment: str | None = Field(
        default=None,
        max_length=300,
        description="Segmento-alvo: 'SaaS B2B', 'indústria farmacêutica', 'varejo premium'.",
    )
    persona_description: str | None = Field(
        default=None,
        description="Persona ideal: cargo típico, dores, prioridades do decisor.",
    )
    offer_description: str | None = Field(
        default=None,
        description="Proposta de valor resumida — o que sua empresa oferece.",
    )
    tone_instructions: str | None = Field(
        default=None,
        description="Instruções extras de tom/voz para a IA.",
    )

    # Template de steps customizado — se não informado, usa template padrão
    steps_template: list[StepTemplateItem] | None = Field(
        default=None,
        description="Template customizado de steps. NULL = template padrão (5 steps).",
    )

    @field_validator("steps_template")
    @classmethod
    def validate_steps_not_empty(
        cls, v: list[StepTemplateItem] | None
    ) -> list[StepTemplateItem] | None:
        if v is not None and len(v) == 0:
            raise ValueError("steps_template não pode ser uma lista vazia")
        return v


class CadenceUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None
    allow_personal_email: bool | None = None
    mode: CadenceMode | None = None
    cadence_type: str | None = None
    llm: LLMConfigSchema | None = None
    tts_provider: str | None = None
    tts_voice_id: str | None = None
    tts_speed: float | None = Field(default=None, ge=0.5, le=2.0)
    tts_pitch: float | None = Field(default=None, ge=-50.0, le=50.0)
    lead_list_id: str | None = None
    email_account_id: str | None = None
    linkedin_account_id: str | None = None
    target_segment: str | None = None
    persona_description: str | None = None
    offer_description: str | None = None
    tone_instructions: str | None = None
    steps_template: list[StepTemplateItem] | None = None


class CadenceResponse(BaseModel):
    """Representação completa de uma cadência na API."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str | None
    is_active: bool
    allow_personal_email: bool
    mode: str = "automatic"
    cadence_type: str = "mixed"
    llm_provider: str
    llm_model: str
    llm_temperature: float
    llm_max_tokens: int
    tts_provider: str | None = None
    tts_voice_id: str | None = None
    tts_speed: float = 1.0
    tts_pitch: float = 0.0
    lead_list_id: uuid.UUID | None = None
    email_account_id: uuid.UUID | None = None
    linkedin_account_id: uuid.UUID | None = None
    target_segment: str | None = None
    persona_description: str | None = None
    offer_description: str | None = None
    tone_instructions: str | None = None
    steps_template: list[dict] | None = None
    created_at: datetime
    updated_at: datetime


class TemplateVariableResponse(BaseModel):
    key: str
    token: str
    label: str


class StepComposeRequest(BaseModel):
    action: Literal["generate", "improve"] = Field(
        ...,
        description="Ação desejada no editor: gerar um template novo ou melhorar um rascunho atual.",
    )
    current_text: str | None = Field(
        default=None,
        description="Rascunho atual do corpo/template para ação improve.",
    )
    current_subject: str | None = Field(
        default=None,
        description="Assunto atual do email para ação improve.",
    )


class StepPreviewRequest(BaseModel):
    lead_id: uuid.UUID | None = Field(
        default=None,
        description="Lead usado na prévia. NULL = lead de exemplo do sistema.",
    )
    current_text: str | None = Field(
        default=None,
        description="Texto atual do editor ainda não salvo.",
    )
    current_subject: str | None = Field(
        default=None,
        description="Assunto atual do editor ainda não salvo.",
    )
    current_email_template_id: str | None = Field(
        default=None,
        description="Template salvo atualmente selecionado no editor.",
    )


class StepSendTestEmailRequest(StepPreviewRequest):
    to_email: EmailStr = Field(..., description="Endereço que receberá o e-mail de teste.")


class StepComposeResponse(BaseModel):
    action: Literal["generate", "improve"]
    channel: Channel
    step_number: int
    step_type: StepType | None = None
    message_template: str
    subject: str | None = None
    variables: list[str] = Field(default_factory=list)
    method: str = Field(default="llm_template")


class StepPreviewResponse(BaseModel):
    channel: Channel
    step_number: int
    lead_id: uuid.UUID | None = None
    lead_name: str | None = None
    subject: str | None = None
    body: str = ""
    body_is_html: bool = False
    variables: list[str] = Field(default_factory=list)
    method: str = Field(default="manual_template")


class StepSendTestEmailResponse(BaseModel):
    to_email: EmailStr
    subject: str
    provider_type: str
    body_is_html: bool


class CadenceDeliveryBudgetItemResponse(BaseModel):
    channel: Channel
    scope_type: str
    scope_label: str
    configured_limit: int
    daily_budget: int
    used_today: int
    remaining_today: int
    usage_pct: float


class CadenceDeliveryBudgetResponse(BaseModel):
    cadence_id: uuid.UUID
    generated_at: datetime
    items: list[CadenceDeliveryBudgetItemResponse] = Field(default_factory=list)


class CadenceReplyEventResponse(BaseModel):
    interaction_id: uuid.UUID
    lead: LeadResponse
    channel: Channel
    step_number: int | None = None
    replied_at: datetime
    intent: str | None = None
    reply_text: str | None = None
    reply_match_source: str | None = None
    pipedrive_sync_status: str | None = None
    pipedrive_person_id: int | None = None
    pipedrive_deal_id: int | None = None
    pipedrive_synced_at: datetime | None = None
    pipedrive_sync_error: str | None = None


class CadenceReplyAuditCandidateStepResponse(BaseModel):
    id: uuid.UUID
    cadence_id: uuid.UUID
    cadence_name: str | None = None
    step_number: int
    channel: Channel
    status: str
    scheduled_at: datetime
    sent_at: datetime | None = None


class CadenceReplyAuditItemResponse(BaseModel):
    interaction_id: uuid.UUID
    lead: LeadResponse
    channel: Channel
    created_at: datetime
    reply_match_status: str
    reply_match_source: str | None = None
    reply_match_sent_cadence_count: int | None = None
    content_text: str | None = None
    candidate_steps: list[CadenceReplyAuditCandidateStepResponse] = Field(default_factory=list)


class CadenceReplyManagementResponse(BaseModel):
    replies: list[CadenceReplyEventResponse] = Field(default_factory=list)
    audit_items: list[CadenceReplyAuditItemResponse] = Field(default_factory=list)
