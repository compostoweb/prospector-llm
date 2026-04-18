from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import UTC, date, datetime

import structlog
from redis import exceptions as redis_exceptions
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.redis_client import RedisClient, redis_client
from models.cadence import Cadence
from models.email_account import EmailAccount
from models.enums import Channel
from models.linkedin_account import LinkedInAccount
from models.tenant import TenantIntegration

logger = structlog.get_logger()

DEFAULT_CHANNEL_LIMITS: dict[Channel, int] = {
    Channel.LINKEDIN_CONNECT: 20,
    Channel.LINKEDIN_DM: 40,
    Channel.LINKEDIN_POST_REACTION: 40,
    Channel.LINKEDIN_POST_COMMENT: 40,
    Channel.LINKEDIN_INMAIL: 40,
    Channel.EMAIL: 300,
}

CHANNEL_BUDGET_FLOOR_RATIOS: dict[Channel, float] = {
    Channel.LINKEDIN_CONNECT: 0.60,
    Channel.LINKEDIN_DM: 0.70,
    Channel.LINKEDIN_POST_REACTION: 0.65,
    Channel.LINKEDIN_POST_COMMENT: 0.65,
    Channel.LINKEDIN_INMAIL: 0.70,
    Channel.EMAIL: 0.90,
}


@dataclass(frozen=True)
class AccountRateScope:
    scope_key: str
    limit: int
    scope_type: str
    scope_label: str


@dataclass(frozen=True)
class CadenceDeliveryBudgetSnapshot:
    channel: Channel
    scope_type: str
    scope_label: str
    configured_limit: int
    daily_budget: int
    used_today: int
    remaining_today: int
    usage_pct: float
    generated_at: datetime


def resolve_tenant_limits(integration: TenantIntegration | None) -> dict[Channel, int]:
    if integration is None:
        return dict(DEFAULT_CHANNEL_LIMITS)

    return {
        Channel.LINKEDIN_CONNECT: integration.limit_linkedin_connect
        or DEFAULT_CHANNEL_LIMITS[Channel.LINKEDIN_CONNECT],
        Channel.LINKEDIN_DM: integration.limit_linkedin_dm
        or DEFAULT_CHANNEL_LIMITS[Channel.LINKEDIN_DM],
        Channel.LINKEDIN_POST_REACTION: integration.limit_linkedin_post_reaction
        or DEFAULT_CHANNEL_LIMITS[Channel.LINKEDIN_POST_REACTION],
        Channel.LINKEDIN_POST_COMMENT: integration.limit_linkedin_post_comment
        or DEFAULT_CHANNEL_LIMITS[Channel.LINKEDIN_POST_COMMENT],
        Channel.LINKEDIN_INMAIL: integration.limit_linkedin_inmail
        or DEFAULT_CHANNEL_LIMITS[Channel.LINKEDIN_INMAIL],
        Channel.EMAIL: integration.limit_email or DEFAULT_CHANNEL_LIMITS[Channel.EMAIL],
    }


async def resolve_account_rate_scope(
    db: AsyncSession,
    cadence: Cadence,
    channel: Channel,
    integration: TenantIntegration | None,
    tenant_limit: int,
) -> AccountRateScope | None:
    if channel == Channel.EMAIL:
        if cadence.email_account_id:
            email_account_result = await db.execute(
                select(EmailAccount).where(EmailAccount.id == cadence.email_account_id)
            )
            email_account = email_account_result.scalar_one_or_none()
            account_limit = tenant_limit
            label = f"Conta de e-mail {str(cadence.email_account_id)[:8]}"
            if email_account is not None:
                account_limit = min(tenant_limit, max(int(email_account.daily_send_limit), 1))
                label = email_account.display_name
            return AccountRateScope(
                scope_key=f"email-account:{cadence.email_account_id}",
                limit=max(account_limit, 1),
                scope_type="email_account",
                scope_label=label,
            )

        gmail_account_id = (
            (integration and integration.unipile_gmail_account_id)
            or settings.UNIPILE_ACCOUNT_ID_GMAIL
            or ""
        )
        if gmail_account_id:
            return AccountRateScope(
                scope_key=f"email-fallback:{gmail_account_id}",
                limit=max(tenant_limit, 1),
                scope_type="tenant_fallback",
                scope_label=f"Fallback Gmail {mask_account_identifier(gmail_account_id)}",
            )
        return None

    if channel.value.startswith("linkedin"):
        if cadence.linkedin_account_id:
            linkedin_account_result = await db.execute(
                select(LinkedInAccount).where(LinkedInAccount.id == cadence.linkedin_account_id)
            )
            linkedin_account = linkedin_account_result.scalar_one_or_none()
            label = f"Conta LinkedIn {str(cadence.linkedin_account_id)[:8]}"
            if linkedin_account is not None:
                label = linkedin_account.display_name
            return AccountRateScope(
                scope_key=f"linkedin-account:{cadence.linkedin_account_id}",
                limit=max(tenant_limit, 1),
                scope_type="linkedin_account",
                scope_label=label,
            )

        linkedin_account_id = (
            (integration and integration.unipile_linkedin_account_id)
            or settings.UNIPILE_ACCOUNT_ID_LINKEDIN
            or ""
        )
        if linkedin_account_id:
            return AccountRateScope(
                scope_key=f"linkedin-fallback:{linkedin_account_id}",
                limit=max(tenant_limit, 1),
                scope_type="tenant_fallback",
                scope_label=f"Fallback LinkedIn {mask_account_identifier(linkedin_account_id)}",
            )

    return None


async def get_or_create_daily_account_budget(
    scope_key: str,
    channel: Channel,
    limit: int,
    *,
    redis: RedisClient = redis_client,
) -> int:
    budget_key = build_account_budget_key(scope_key, channel)
    try:
        cached = await redis.get(budget_key)
        if cached is not None:
            return max(int(cached), 1)

        drawn_budget = draw_daily_budget(limit, channel)
        created = await redis.set_if_absent(budget_key, str(drawn_budget), ttl=86400)
        if created:
            return drawn_budget

        cached_after_race = await redis.get(budget_key)
        return max(int(cached_after_race or drawn_budget), 1)
    except redis_exceptions.RedisError as exc:
        logger.warning(
            "delivery_budget.redis_unavailable",
            channel=channel.value,
            scope_key=scope_key,
            error=str(exc),
        )
        return draw_daily_budget(limit, channel)


async def get_current_account_usage(
    scope_key: str,
    channel: Channel,
    *,
    redis: RedisClient = redis_client,
) -> int:
    try:
        current = await redis.get(build_account_rate_counter_key(scope_key, channel))
        return max(int(current or 0), 0)
    except redis_exceptions.RedisError as exc:
        logger.warning(
            "delivery_budget.usage_unavailable",
            channel=channel.value,
            scope_key=scope_key,
            error=str(exc),
        )
        return 0


async def build_cadence_delivery_budget_snapshots(
    db: AsyncSession,
    cadence: Cadence,
    integration: TenantIntegration | None,
    *,
    redis: RedisClient = redis_client,
) -> list[CadenceDeliveryBudgetSnapshot]:
    tenant_limits = resolve_tenant_limits(integration)
    channels = ordered_delivery_channels(cadence)
    snapshots: list[CadenceDeliveryBudgetSnapshot] = []
    generated_at = datetime.now(tz=UTC)

    for channel in channels:
        configured_limit = tenant_limits.get(channel, DEFAULT_CHANNEL_LIMITS.get(channel, 40))
        account_scope = await resolve_account_rate_scope(
            db,
            cadence,
            channel,
            integration,
            configured_limit,
        )
        if account_scope is None:
            continue

        daily_budget = await get_or_create_daily_account_budget(
            account_scope.scope_key,
            channel,
            account_scope.limit,
            redis=redis,
        )
        used_today = await get_current_account_usage(
            account_scope.scope_key,
            channel,
            redis=redis,
        )
        remaining_today = max(daily_budget - used_today, 0)
        usage_pct = round((used_today / daily_budget) * 100, 1) if daily_budget else 0.0
        snapshots.append(
            CadenceDeliveryBudgetSnapshot(
                channel=channel,
                scope_type=account_scope.scope_type,
                scope_label=account_scope.scope_label,
                configured_limit=configured_limit,
                daily_budget=daily_budget,
                used_today=used_today,
                remaining_today=remaining_today,
                usage_pct=usage_pct,
                generated_at=generated_at,
            )
        )

    return snapshots


def ordered_delivery_channels(cadence: Cadence) -> list[Channel]:
    ordered = [
        Channel.LINKEDIN_CONNECT,
        Channel.LINKEDIN_DM,
        Channel.LINKEDIN_POST_REACTION,
        Channel.LINKEDIN_POST_COMMENT,
        Channel.LINKEDIN_INMAIL,
        Channel.EMAIL,
    ]
    configured_steps = getattr(cadence, "steps_template", None) or []
    configured_channels = {
        Channel(str(step.get("channel")))
        for step in configured_steps
        if step.get("channel") and str(step.get("channel")) != Channel.MANUAL_TASK.value
    }
    return [channel for channel in ordered if channel in configured_channels]


def draw_daily_budget(limit: int, channel: Channel) -> int:
    floor_ratio = CHANNEL_BUDGET_FLOOR_RATIOS.get(channel, 0.70)
    floor_value = max(1, int(limit * floor_ratio))
    if floor_value >= limit:
        return max(limit, 1)
    return random.randint(floor_value, limit)


def build_account_budget_key(scope_key: str, channel: Channel) -> str:
    return f"ratelimit:account-budget:{scope_key}:{channel.value}:{date.today()}"


def build_account_rate_counter_key(scope_key: str, channel: Channel) -> str:
    return f"ratelimit:account:{scope_key}:{channel.value}:{date.today()}"


def build_account_rate_limit_key(cadence, integration, channel) -> str | None:
    if channel.value == Channel.EMAIL.value:
        if cadence is not None and getattr(cadence, "email_account_id", None):
            scope_key = f"email-account:{cadence.email_account_id}"
        else:
            gmail_account_id = (
                (integration and getattr(integration, "unipile_gmail_account_id", None))
                or settings.UNIPILE_ACCOUNT_ID_GMAIL
                or ""
            )
            if not gmail_account_id:
                return None
            scope_key = f"email-fallback:{gmail_account_id}"
    elif channel.value.startswith("linkedin"):
        if cadence is not None and getattr(cadence, "linkedin_account_id", None):
            scope_key = f"linkedin-account:{cadence.linkedin_account_id}"
        else:
            linkedin_account_id = (
                (integration and getattr(integration, "unipile_linkedin_account_id", None))
                or settings.UNIPILE_ACCOUNT_ID_LINKEDIN
                or ""
            )
            if not linkedin_account_id:
                return None
            scope_key = f"linkedin-fallback:{linkedin_account_id}"
    else:
        return None

    return build_account_rate_counter_key(scope_key, channel)


def mask_account_identifier(value: str) -> str:
    if len(value) <= 8:
        return value
    return f"{value[:4]}...{value[-4:]}"
