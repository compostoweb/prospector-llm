from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from redis import exceptions as redis_exceptions

from models.enums import Channel
from services.cadence_delivery_budget import (
    get_current_account_usage,
    get_or_create_daily_account_budget,
)

pytestmark = pytest.mark.asyncio


async def test_get_or_create_daily_account_budget_falls_back_when_redis_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis = AsyncMock()
    redis.get.side_effect = redis_exceptions.ConnectionError("redis down")

    monkeypatch.setattr(
        "services.cadence_delivery_budget.draw_daily_budget",
        lambda limit, channel: 27,
    )

    budget = await get_or_create_daily_account_budget(
        "email-account:test",
        Channel.EMAIL,
        30,
        redis=redis,
    )

    assert budget == 27


async def test_get_current_account_usage_returns_zero_when_redis_fails() -> None:
    redis = AsyncMock()
    redis.get.side_effect = redis_exceptions.ConnectionError("redis down")

    usage = await get_current_account_usage(
        "email-account:test",
        Channel.EMAIL,
        redis=redis,
    )

    assert usage == 0