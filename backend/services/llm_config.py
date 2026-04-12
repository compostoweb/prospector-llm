from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from models.tenant import TenantIntegration

LLMConfigScope = Literal["system", "cold_email"]

_DEFAULT_TEMPERATURE = 0.7
_DEFAULT_SYSTEM_MAX_TOKENS = 1024
_DEFAULT_COLD_EMAIL_MAX_TOKENS = 512


@dataclass(frozen=True, slots=True)
class ResolvedLLMConfig:
    provider: str
    model: str
    temperature: float
    max_tokens: int


def merge_llm_config(
    base: ResolvedLLMConfig,
    *,
    provider: str | None = None,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> ResolvedLLMConfig:
    return ResolvedLLMConfig(
        provider=provider or base.provider,
        model=model or base.model,
        temperature=base.temperature if temperature is None else temperature,
        max_tokens=base.max_tokens if max_tokens is None else max_tokens,
    )


def fallback_llm_config(scope: LLMConfigScope = "system") -> ResolvedLLMConfig:
    max_tokens = (
        _DEFAULT_COLD_EMAIL_MAX_TOKENS if scope == "cold_email" else _DEFAULT_SYSTEM_MAX_TOKENS
    )
    return ResolvedLLMConfig(
        provider="openai",
        model=settings.OPENAI_DEFAULT_MODEL,
        temperature=_DEFAULT_TEMPERATURE,
        max_tokens=max_tokens,
    )


async def resolve_tenant_llm_config(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    scope: LLMConfigScope = "system",
) -> ResolvedLLMConfig:
    result = await db.execute(
        select(TenantIntegration).where(TenantIntegration.tenant_id == tenant_id)
    )
    integration = result.scalar_one_or_none()
    if integration is None:
        return fallback_llm_config(scope)

    if scope == "cold_email":
        return ResolvedLLMConfig(
            provider=integration.cold_email_llm_provider,
            model=integration.cold_email_llm_model,
            temperature=integration.cold_email_llm_temperature,
            max_tokens=integration.cold_email_llm_max_tokens,
        )

    return ResolvedLLMConfig(
        provider=integration.llm_default_provider,
        model=integration.llm_default_model,
        temperature=integration.llm_default_temperature,
        max_tokens=integration.llm_default_max_tokens,
    )


async def resolve_anthropic_batch_model(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    model: str | None = None,
) -> str:
    if model:
        return model

    config = await resolve_tenant_llm_config(db, tenant_id)
    if config.provider != "anthropic":
        raise ValueError(
            "A analise batch usa Anthropic Batches. Configure o provider LLM padrao do tenant como anthropic ou informe um modelo Anthropic explicitamente."
        )

    return config.model
