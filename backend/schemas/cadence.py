"""
schemas/cadence.py

Schemas Pydantic v2 para create/update de Cadence.
Inclui validação do par provider+model e valores de LLM.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from models.enums import CadenceMode, Channel, StepType

# Combinações válidas: provider → lista de prefixos de model aceitos
# Serve para validação básica — a lista completa vem da API dos providers
_VALID_PROVIDERS = {"openai", "gemini", "anthropic", "openrouter"}

_PROVIDER_MODEL_PREFIXES: dict[str, tuple[str, ...]] = {
    "openai": ("gpt-", "o1", "o3", "o4"),
    "gemini": ("gemini-",),
    "anthropic": ("claude-",),
    "openrouter": (),  # OpenRouter aceita qualquer modelo — validação dinâmica
}


class LLMConfigSchema(BaseModel):
    """Configuração de LLM para uma cadência."""

    provider: str = Field(
        default="openai",
        description="Provedor LLM: openai | gemini | anthropic",
    )
    model: str = Field(
        default="gpt-4o-mini",
        description="ID do modelo. Ex: gpt-4o-mini, gemini-2.5-flash, claude-haiku-4-5",
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


class CadenceCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    description: str | None = None
    allow_personal_email: bool = False
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
