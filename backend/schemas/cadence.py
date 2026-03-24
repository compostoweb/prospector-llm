"""
schemas/cadence.py

Schemas Pydantic v2 para create/update de Cadence.
Inclui validação do par provider+model e valores de LLM.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator

from models.enums import Channel

# Combinações válidas: provider → lista de prefixos de model aceitos
# Serve para validação básica — a lista completa vem da API dos providers
_VALID_PROVIDERS = {"openai", "gemini"}

_PROVIDER_MODEL_PREFIXES: dict[str, tuple[str, ...]] = {
    "openai": ("gpt-", "o1", "o3", "o4"),
    "gemini": ("gemini-",),
}


class LLMConfigSchema(BaseModel):
    """Configuração de LLM para uma cadência."""

    provider: str = Field(
        default="openai",
        description="Provedor LLM: openai | gemini",
    )
    model: str = Field(
        default="gpt-4o-mini",
        description="ID do modelo. Ex: gpt-4o-mini, gemini-2.5-flash, gemini-2.5-flash-lite",
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
    def validate_model_matches_provider(self) -> "LLMConfigSchema":
        prefixes = _PROVIDER_MODEL_PREFIXES.get(self.provider, ())
        if prefixes and not any(self.model.startswith(p) for p in prefixes):
            raise ValueError(
                f"Modelo '{self.model}' não parece pertencer ao provider '{self.provider}'. "
                f"Prefixos esperados: {prefixes}"
            )
        return self


class StepTemplateItem(BaseModel):
    """Um step dentro do template customizado de cadência."""

    channel: Channel
    day_offset: int = Field(..., ge=0, le=90, description="Dias após enrollment")
    message_template: str | None = Field(default=None, description="Template de mensagem com variáveis")
    use_voice: bool = Field(default=False, description="Enviar voice note (só linkedin_dm)")

    @model_validator(mode="after")
    def voice_only_for_dm(self) -> "StepTemplateItem":
        if self.use_voice and self.channel != Channel.LINKEDIN_DM:
            raise ValueError("use_voice só é permitido para linkedin_dm")
        return self


class CadenceCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    description: str | None = None
    allow_personal_email: bool = False

    # Configuração LLM — se não informado, usa defaults globais
    llm: LLMConfigSchema = Field(default_factory=LLMConfigSchema)

    # Configuração TTS — se não informado, usa fallback global (VOICE_PROVIDER)
    tts_provider: str | None = Field(
        default=None,
        description="Provedor TTS: speechify | voicebox. NULL = default global.",
    )
    tts_voice_id: str | None = Field(
        default=None,
        description="ID da voz/profile TTS. NULL = default do provider.",
    )

    # Lista de leads vinculada (opcional)
    lead_list_id: str | None = Field(
        default=None,
        description="ID da lista de leads a usar nesta cadência. NULL = nenhuma.",
    )

    # Template de steps customizado — se não informado, usa template padrão
    steps_template: list[StepTemplateItem] | None = Field(
        default=None,
        description="Template customizado de steps. NULL = template padrão (5 steps).",
    )

    @field_validator("steps_template")
    @classmethod
    def validate_steps_not_empty(cls, v: list[StepTemplateItem] | None) -> list[StepTemplateItem] | None:
        if v is not None and len(v) == 0:
            raise ValueError("steps_template não pode ser uma lista vazia")
        return v


class CadenceUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None
    allow_personal_email: bool | None = None
    llm: LLMConfigSchema | None = None
    tts_provider: str | None = None
    tts_voice_id: str | None = None
    lead_list_id: str | None = None
    steps_template: list[StepTemplateItem] | None = None


class CadenceResponse(BaseModel):
    """Representação completa de uma cadência na API."""

    model_config = {"from_attributes": True}

    id: str
    tenant_id: str
    name: str
    description: str | None
    is_active: bool
    allow_personal_email: bool
    llm_provider: str
    llm_model: str
    llm_temperature: float
    llm_max_tokens: int
    tts_provider: str | None = None
    tts_voice_id: str | None = None
    lead_list_id: str | None = None
    steps_template: list[dict] | None = None
    created_at: str | None = None
    updated_at: str | None = None
