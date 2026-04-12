"""
services/llm_usage_tracker.py

Persistência e estimativa de custo para consumo de LLM.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy.dialects.postgresql import insert

from core.database import WorkerSessionLocal
from integrations.llm.base import LLMMessage, LLMResponse, LLMUsageContext
from models.llm_usage_event import LLMUsageEvent
from models.llm_usage_hourly import LLMUsageHourlyAggregate

logger = structlog.get_logger()

_OPENAI_PRICES: dict[str, tuple[float, float]] = {
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4.1": (2.00, 8.00),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1-nano": (0.10, 0.40),
    "gpt-5": (0.0, 0.0),
    "o1": (15.00, 60.00),
    "o1-mini": (3.00, 12.00),
    "o3": (10.00, 40.00),
    "o3-mini": (1.10, 4.40),
    "o4-mini": (1.10, 4.40),
}
_GEMINI_PRICES: dict[str, tuple[float, float]] = {
    "gemini-2.5-pro": (1.25, 10.00),
    "gemini-2.5-flash": (0.30, 2.50),
    "gemini-2.5-flash-lite": (0.10, 0.40),
    "gemini-2.0-flash": (0.10, 0.40),
    "gemini-3-flash": (0.15, 0.60),
    "gemini-3.1-pro": (1.25, 10.00),
    "gemini-3.1-flash": (0.15, 0.60),
}
_ANTHROPIC_PRICES: dict[str, tuple[float, float]] = {
    "claude-opus-4-6": (5.00, 25.00),
    "claude-opus-4-5": (5.00, 25.00),
    "claude-opus-4-1": (15.00, 75.00),
    "claude-opus-4": (15.00, 75.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-sonnet-4-5": (3.00, 15.00),
    "claude-sonnet-4": (3.00, 15.00),
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-haiku-3-5": (0.80, 4.00),
    "claude-haiku-3": (0.25, 1.25),
    "claude-opus-3": (15.00, 75.00),
}


def estimate_llm_cost(
    *,
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> tuple[float, bool]:
    """Retorna (custo_estimado_usd, is_estimated)."""
    provider_name = (provider or "").lower()
    if provider_name == "openai":
        input_price, output_price = _price_for(model, _OPENAI_PRICES)
    elif provider_name == "gemini":
        input_price, output_price = _price_for(model, _GEMINI_PRICES)
    elif provider_name == "anthropic":
        input_price, output_price = _price_for(model, _ANTHROPIC_PRICES)
    else:
        input_price, output_price = (0.0, 0.0)

    cost = ((input_tokens / 1_000_000) * input_price) + ((output_tokens / 1_000_000) * output_price)
    return round(cost, 6), True


async def record_llm_usage(
    *,
    messages: list[LLMMessage],
    response: LLMResponse,
    usage_context: LLMUsageContext,
    latency_ms: int | None = None,
) -> None:
    """Persiste um evento de uso de LLM sem impactar o fluxo principal."""
    tenant_id = uuid.UUID(str(usage_context.tenant_id))
    input_tokens = max(response.input_tokens, 0)
    output_tokens = max(response.output_tokens, 0)
    total_tokens = input_tokens + output_tokens
    estimated_cost_usd, is_estimated = estimate_llm_cost(
        provider=response.provider,
        model=response.model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
    metadata = _json_safe_dict(usage_context.metadata)

    event = LLMUsageEvent(
        tenant_id=tenant_id,
        provider=response.provider,
        model=response.model,
        module=usage_context.module,
        task_type=usage_context.task_type,
        feature=usage_context.feature,
        entity_type=usage_context.entity_type,
        entity_id=usage_context.entity_id,
        secondary_entity_type=usage_context.secondary_entity_type,
        secondary_entity_id=usage_context.secondary_entity_id,
        prompt_chars=sum(len(message.content) for message in messages),
        completion_chars=len(response.text or ""),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        estimated_cost_usd=estimated_cost_usd,
        is_estimated=is_estimated,
        latency_ms=latency_ms,
        request_metadata=metadata or None,
    )
    feature = usage_context.feature or ""
    bucket_start = _hour_bucket()
    aggregate_insert = insert(LLMUsageHourlyAggregate).values(
        tenant_id=tenant_id,
        bucket_start=bucket_start,
        provider=response.provider,
        model=response.model,
        module=usage_context.module,
        task_type=usage_context.task_type,
        feature=feature,
        requests=1,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        estimated_cost_usd=estimated_cost_usd,
    )
    aggregate_upsert = aggregate_insert.on_conflict_do_update(
        constraint="uq_llm_usage_hourly_bucket_dimensions",
        set_={
            "requests": LLMUsageHourlyAggregate.requests + 1,
            "input_tokens": LLMUsageHourlyAggregate.input_tokens + input_tokens,
            "output_tokens": LLMUsageHourlyAggregate.output_tokens + output_tokens,
            "total_tokens": LLMUsageHourlyAggregate.total_tokens + total_tokens,
            "estimated_cost_usd": LLMUsageHourlyAggregate.estimated_cost_usd + estimated_cost_usd,
            "updated_at": datetime.now(UTC),
        },
    )

    async with WorkerSessionLocal() as session:
        session.add(event)
        await session.execute(aggregate_upsert)
        await session.commit()

    logger.debug(
        "llm.usage_recorded",
        tenant_id=str(tenant_id),
        provider=response.provider,
        model=response.model,
        module=usage_context.module,
        task_type=usage_context.task_type,
        total_tokens=total_tokens,
        estimated_cost_usd=estimated_cost_usd,
    )


def _json_safe_dict(value: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, item in value.items():
        if isinstance(item, (str, int, float, bool)) or item is None:
            safe[key] = item
        else:
            safe[key] = str(item)
    return safe


def _price_for(model: str, price_table: dict[str, tuple[float, float]]) -> tuple[float, float]:
    if model in price_table:
        return price_table[model]
    for key, prices in price_table.items():
        if model.startswith(key):
            return prices
    return (0.0, 0.0)


def _hour_bucket() -> datetime:
    now = datetime.now(UTC)
    return now.replace(minute=0, second=0, microsecond=0)
