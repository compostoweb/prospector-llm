"""
schemas/cadence.py

Schemas Pydantic v2 para create/update de Cadence.
Inclui validação do par provider+model e valores de LLM.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator

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


class CadenceCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    description: str | None = None
    allow_personal_email: bool = False

    # Configuração LLM — se não informado, usa defaults globais
    llm: LLMConfigSchema = Field(default_factory=LLMConfigSchema)


class CadenceUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None
    allow_personal_email: bool | None = None
    llm: LLMConfigSchema | None = None


class CadenceResponse(BaseModel):
    id: str
    name: str
    description: str | None
    is_active: bool
    allow_personal_email: bool
    llm_provider: str
    llm_model: str
    llm_temperature: float
    llm_max_tokens: int

    model_config = {"from_attributes": True}
