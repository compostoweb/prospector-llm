from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from core.config import settings
from models.tenant import TenantIntegration
from services.llm_config import (
    fallback_llm_config,
    merge_llm_config,
    resolve_anthropic_batch_model,
    resolve_tenant_llm_config,
)

pytestmark = pytest.mark.asyncio


async def test_resolve_tenant_llm_config_uses_system_scope(db, tenant_id, tenant):
    result = await db.execute(
        select(TenantIntegration).where(TenantIntegration.tenant_id == tenant_id)
    )
    integration = result.scalar_one()
    integration.llm_default_provider = "openai"
    integration.llm_default_model = "gpt-5.4-mini"
    integration.llm_default_temperature = 0.4
    integration.llm_default_max_tokens = 1536
    await db.flush()

    config = await resolve_tenant_llm_config(db, tenant_id)

    assert config.provider == "openai"
    assert config.model == "gpt-5.4-mini"
    assert config.temperature == 0.4
    assert config.max_tokens == 1536


async def test_resolve_tenant_llm_config_uses_cold_email_scope(db, tenant_id, tenant):
    result = await db.execute(
        select(TenantIntegration).where(TenantIntegration.tenant_id == tenant_id)
    )
    integration = result.scalar_one()
    integration.cold_email_llm_provider = "openai"
    integration.cold_email_llm_model = "gpt-5.4-mini"
    integration.cold_email_llm_temperature = 0.2
    integration.cold_email_llm_max_tokens = 640
    await db.flush()

    config = await resolve_tenant_llm_config(db, tenant_id, scope="cold_email")

    assert config.provider == "openai"
    assert config.model == "gpt-5.4-mini"
    assert config.temperature == 0.2
    assert config.max_tokens == 640


async def test_resolve_tenant_llm_config_falls_back_without_integration(db):
    config = await resolve_tenant_llm_config(db, uuid.uuid4())

    assert config.provider == "openai"
    assert config.model == settings.OPENAI_DEFAULT_MODEL
    assert config.temperature == 0.7
    assert config.max_tokens == 1024


def test_merge_llm_config_applies_overrides() -> None:
    base = merge_llm_config(
        fallback_llm_config(),
        provider="gemini",
        model="gemini-2.5-flash",
        max_tokens=2048,
    )

    assert base.provider == "gemini"
    assert base.model == "gemini-2.5-flash"
    assert base.temperature == 0.7
    assert base.max_tokens == 2048


async def test_resolve_anthropic_batch_model_uses_tenant_model(db, tenant_id, tenant):
    result = await db.execute(
        select(TenantIntegration).where(TenantIntegration.tenant_id == tenant_id)
    )
    integration = result.scalar_one()
    integration.llm_default_provider = "anthropic"
    integration.llm_default_model = "claude-haiku-4-5"
    await db.flush()

    model = await resolve_anthropic_batch_model(db, tenant_id)

    assert model == "claude-haiku-4-5"


async def test_resolve_anthropic_batch_model_rejects_non_anthropic_tenant(db, tenant_id, tenant):
    result = await db.execute(
        select(TenantIntegration).where(TenantIntegration.tenant_id == tenant_id)
    )
    integration = result.scalar_one()
    integration.llm_default_provider = "openai"
    integration.llm_default_model = "gpt-5.4-mini"
    await db.flush()

    with pytest.raises(ValueError, match="Anthropic Batches"):
        await resolve_anthropic_batch_model(db, tenant_id)
