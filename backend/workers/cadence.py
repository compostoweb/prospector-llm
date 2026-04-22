"""
workers/cadence.py

Task Celery para o tick da cadência — disparada pelo Beat a cada minuto.

Task:
  cadence_tick()
    — Busca todos os tenants ativos
    — Por tenant: consulta CadenceSteps com scheduled_at <= now() e status=PENDING
    — Verifica rate limit Redis por canal
    — Enfileira dispatch_step para cada step aprovado
    — Fila: "cadence"

Rate limiting:
  Chave Redis: ratelimit:{tenant_id}:{channel}:{YYYY-MM-DD}
  Limites padrão: LINKEDIN_CONNECT=20, LINKEDIN_DM=40, EMAIL=300
  O check é feito com INCR atômico + TTL para garantir exatidão.

Segurança: steps só são despachados se o lead ainda estiver IN_CADENCE.
Se o lead foi arquivado ou convertido, o step é marcado como SKIPPED.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

import structlog
from sqlalchemy import select

from core.config import settings
from core.database import WorkerSessionLocal, get_worker_session
from core.redis_client import redis_client
from models.cadence import Cadence
from models.cadence_step import CadenceStep
from models.enums import Channel, LeadStatus, StepStatus
from models.lead import Lead
from models.tenant import Tenant, TenantIntegration
from services.cadence_delivery_budget import (
    DEFAULT_CHANNEL_LIMITS,
    build_account_rate_counter_key,
    get_or_create_daily_account_budget,
    resolve_account_rate_scope,
    resolve_tenant_limits,
)
from services.cadence_step_eligibility import evaluate_step_eligibility
from workers.celery_app import celery_app

logger = structlog.get_logger()

LINKEDIN_ENGAGEMENT_CHANNELS = {
    Channel.LINKEDIN_POST_REACTION,
    Channel.LINKEDIN_POST_COMMENT,
}


@dataclass(frozen=True)
class DeliveryThrottlePolicy:
    throttle_scope: str
    min_interval_seconds: int
    max_interval_seconds: int
    per_minute_limit: int


@celery_app.task(
    bind=True,
    name="workers.cadence.cadence_tick",
    max_retries=1,
    queue="cadence",
)
def cadence_tick(self) -> dict:
    """
    Tick da cadência — executado pelo Beat a cada minuto.
    Enfileira dispatch_step para cada step pendente que passou do horário.
    """
    return asyncio.run(_tick_async())


async def _tick_async() -> dict:
    dispatched = 0
    skipped = 0

    # Busca todos os tenants ativos (sem filtro RLS — é a task de sistema)
    async with WorkerSessionLocal() as root_session:
        result = await root_session.execute(select(Tenant).where(Tenant.is_active.is_(True)))
        tenants: list[Tenant] = list(result.scalars().all())

    for tenant in tenants:
        tid = tenant.id
        try:
            async for db in get_worker_session(tid):
                now = datetime.now(tz=UTC)
                integration_result = await db.execute(
                    select(TenantIntegration).where(TenantIntegration.tenant_id == tid)
                )
                integration = integration_result.scalar_one_or_none()
                tenant_limits = resolve_tenant_limits(integration)

                # Busca steps pendentes e vencidos deste tenant
                # Só despacha steps de cadências ativas
                steps_result = await db.execute(
                    select(CadenceStep)
                    .join(Cadence, CadenceStep.cadence_id == Cadence.id)
                    .where(
                        CadenceStep.tenant_id == tid,
                        CadenceStep.status == StepStatus.PENDING,
                        CadenceStep.scheduled_at <= now,
                        Cadence.is_active.is_(True),
                    )
                    .order_by(CadenceStep.scheduled_at.asc())
                    .limit(200)
                )
                steps: list[CadenceStep] = list(steps_result.scalars().all())

                for step in steps:
                    cadence_result = await db.execute(
                        select(Cadence).where(Cadence.id == step.cadence_id)
                    )
                    cadence = cadence_result.scalar_one_or_none()
                    if cadence is None:
                        logger.warning(
                            "cadence_tick.cadence_not_found",
                            step_id=str(step.id),
                            cadence_id=str(step.cadence_id),
                        )
                        continue

                    # Verifica se o lead ainda está em cadência
                    lead_result = await db.execute(select(Lead).where(Lead.id == step.lead_id))
                    lead = lead_result.scalar_one_or_none()
                    lead_status = lead.status if lead is not None else None

                    if lead is None or lead_status != LeadStatus.IN_CADENCE:
                        step.status = StepStatus.SKIPPED
                        skipped += 1
                        logger.info(
                            "cadence_tick.step_skipped",
                            step_id=str(step.id),
                            reason="lead_not_in_cadence",
                            lead_status=str(lead_status),
                        )
                        continue

                    assert lead is not None
                    eligibility = await evaluate_step_eligibility(
                        db=db,
                        cadence=cadence,
                        step=step,
                        lead=lead,
                        integration=integration,
                    )
                    if not eligibility.dispatchable:
                        step.status = StepStatus.SKIPPED
                        skipped += 1
                        logger.info(
                            "cadence_tick.step_skipped",
                            step_id=str(step.id),
                            reason=eligibility.reason,
                            channel=step.channel.value,
                        )
                        continue

                    allowed = await _reserve_step_rate_limits(
                        db=db,
                        tenant_id=tid,
                        cadence=cadence,
                        step=step,
                        integration=integration,
                        tenant_limits=tenant_limits,
                    )
                    if not allowed:
                        continue

                    # Enfileira o dispatch
                    from workers.dispatch import dispatch_step

                    dispatch_countdown = await _reserve_dispatch_countdown(
                        db=db,
                        cadence=cadence,
                        step=step,
                        integration=integration,
                        tenant_limits=tenant_limits,
                        now=now,
                    )

                    step.status = StepStatus.DISPATCHING
                    await db.flush()

                    if dispatch_countdown > 0:
                        dispatch_step.apply_async(
                            args=[str(step.id), str(tid)],
                            countdown=dispatch_countdown,
                            queue="dispatch",
                        )
                        logger.info(
                            "cadence_tick.delivery_throttled",
                            step_id=str(step.id),
                            cadence_id=str(cadence.id),
                            channel=step.channel.value,
                            countdown_seconds=dispatch_countdown,
                        )
                    else:
                        dispatch_step.delay(str(step.id), str(tid))
                    dispatched += 1

                await db.commit()

                # Auto-matricula novos leads adicionados à lista vinculada
                enrolled = await _auto_enroll_list_members(db, tid)
                if enrolled:
                    await db.commit()

        except Exception as exc:  # noqa: BLE001
            logger.error(
                "cadence_tick.tenant_error",
                tenant_id=str(tid),
                error=str(exc),
            )

    logger.info(
        "cadence_tick.done",
        dispatched=dispatched,
        skipped=skipped,
        tenants=len(tenants),
    )
    return {"dispatched": dispatched, "skipped": skipped}


async def _reserve_step_rate_limits(
    db,
    tenant_id: uuid.UUID,
    cadence: Cadence,
    step: CadenceStep,
    integration: TenantIntegration | None,
    tenant_limits: dict[Channel, int],
) -> bool:
    tenant_limit = tenant_limits.get(step.channel, DEFAULT_CHANNEL_LIMITS.get(step.channel, 40))
    tenant_allowed = await redis_client.check_and_increment(
        channel=step.channel.value,
        tenant_id=tenant_id,
        limit=tenant_limit,
    )
    if not tenant_allowed:
        logger.info(
            "cadence_tick.rate_limited",
            tenant_id=str(tenant_id),
            channel=step.channel.value,
            scope="tenant",
        )
        return False

    account_scope = await resolve_account_rate_scope(
        db=db,
        cadence=cadence,
        channel=step.channel,
        integration=integration,
        tenant_limit=tenant_limit,
    )
    if account_scope is None:
        return True

    budget = await get_or_create_daily_account_budget(
        account_scope.scope_key, step.channel, account_scope.limit
    )
    account_counter_key = build_account_rate_counter_key(account_scope.scope_key, step.channel)
    account_allowed = await redis_client.check_and_increment_key(account_counter_key, limit=budget)
    if account_allowed:
        return True

    await redis_client.release_rate_limit(step.channel.value, tenant_id)
    logger.info(
        "cadence_tick.rate_limited",
        tenant_id=str(tenant_id),
        channel=step.channel.value,
        scope="account",
        account_scope=account_scope.scope_key,
        budget=budget,
    )
    return False


async def _reserve_dispatch_countdown(
    *,
    db,
    cadence: Cadence,
    step: CadenceStep,
    integration: TenantIntegration | None,
    tenant_limits: dict[Channel, int],
    now: datetime,
) -> int:
    policy = await _build_delivery_throttle_policy(
        db=db,
        cadence=cadence,
        step=step,
        integration=integration,
        tenant_limits=tenant_limits,
    )
    if policy is None:
        return 0

    now_ts = int(now.timestamp())
    scheduled_ts = await redis_client.reserve_delivery_slot(
        throttle_scope=policy.throttle_scope,
        now_ts=now_ts,
        min_gap_seconds=policy.min_interval_seconds,
        max_gap_seconds=policy.max_interval_seconds,
        per_minute_limit=policy.per_minute_limit,
    )
    return max(scheduled_ts - now_ts, 0)


async def _build_delivery_throttle_policy(
    *,
    db,
    cadence: Cadence,
    step: CadenceStep,
    integration: TenantIntegration | None,
    tenant_limits: dict[Channel, int],
) -> DeliveryThrottlePolicy | None:
    throttled_channels = {
        Channel.EMAIL,
        Channel.LINKEDIN_CONNECT,
        Channel.LINKEDIN_DM,
        Channel.LINKEDIN_POST_REACTION,
        Channel.LINKEDIN_POST_COMMENT,
        Channel.LINKEDIN_INMAIL,
    }
    if step.channel not in throttled_channels:
        return None

    tenant_limit = tenant_limits.get(step.channel, DEFAULT_CHANNEL_LIMITS.get(step.channel, 40))
    account_scope = await resolve_account_rate_scope(
        db=db,
        cadence=cadence,
        channel=step.channel,
        integration=integration,
        tenant_limit=tenant_limit,
    )
    if account_scope is None:
        return None

    if step.channel == Channel.EMAIL:
        return DeliveryThrottlePolicy(
            throttle_scope=f"email:{account_scope.scope_key}",
            min_interval_seconds=settings.CADENCE_EMAIL_MIN_INTERVAL_SECONDS,
            max_interval_seconds=settings.CADENCE_EMAIL_MAX_INTERVAL_SECONDS,
            per_minute_limit=settings.CADENCE_EMAIL_MAX_PER_MINUTE,
        )

    if step.channel == Channel.LINKEDIN_CONNECT:
        return DeliveryThrottlePolicy(
            throttle_scope=f"linkedin:{account_scope.scope_key}",
            min_interval_seconds=settings.CADENCE_LINKEDIN_CONNECT_MIN_INTERVAL_SECONDS,
            max_interval_seconds=settings.CADENCE_LINKEDIN_CONNECT_MAX_INTERVAL_SECONDS,
            per_minute_limit=settings.CADENCE_LINKEDIN_CONNECT_MAX_PER_MINUTE,
        )

    if step.channel == Channel.LINKEDIN_DM:
        return DeliveryThrottlePolicy(
            throttle_scope=f"linkedin:{account_scope.scope_key}",
            min_interval_seconds=settings.CADENCE_LINKEDIN_DM_MIN_INTERVAL_SECONDS,
            max_interval_seconds=settings.CADENCE_LINKEDIN_DM_MAX_INTERVAL_SECONDS,
            per_minute_limit=settings.CADENCE_LINKEDIN_DM_MAX_PER_MINUTE,
        )

    if step.channel in LINKEDIN_ENGAGEMENT_CHANNELS:
        return DeliveryThrottlePolicy(
            throttle_scope=f"linkedin:{account_scope.scope_key}",
            min_interval_seconds=settings.CADENCE_LINKEDIN_ENGAGEMENT_MIN_INTERVAL_SECONDS,
            max_interval_seconds=settings.CADENCE_LINKEDIN_ENGAGEMENT_MAX_INTERVAL_SECONDS,
            per_minute_limit=settings.CADENCE_LINKEDIN_ENGAGEMENT_MAX_PER_MINUTE,
        )

    if step.channel == Channel.LINKEDIN_INMAIL:
        return DeliveryThrottlePolicy(
            throttle_scope=f"linkedin:{account_scope.scope_key}",
            min_interval_seconds=settings.CADENCE_LINKEDIN_INMAIL_MIN_INTERVAL_SECONDS,
            max_interval_seconds=settings.CADENCE_LINKEDIN_INMAIL_MAX_INTERVAL_SECONDS,
            per_minute_limit=settings.CADENCE_LINKEDIN_INMAIL_MAX_PER_MINUTE,
        )

    return None


async def _auto_enroll_list_members(db, tenant_id: uuid.UUID) -> int:
    """
    Verifica todas as cadências ativas deste tenant que possuem lead_list_id.
    Para cada lead da lista que ainda não possui steps nessa cadência e cujo
    status seja RAW ou ENRICHED, realiza o enrollment automático.
    Retorna o número de leads matriculados.
    """
    from models.cadence import Cadence
    from services.cadence_manager import CadenceManager

    enrolled_count = 0
    manager = CadenceManager()

    # Busca cadências ativas com lista vinculada
    cadences_result = await db.execute(
        select(Cadence).where(
            Cadence.tenant_id == tenant_id,
            Cadence.is_active.is_(True),
            Cadence.lead_list_id.is_not(None),
        )
    )
    cadences: list[Cadence] = list(cadences_result.scalars().all())

    for cadence in cadences:
        enrolled_count += await manager.auto_enroll_list_members(cadence, db, limit=50)

    return enrolled_count
