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
from datetime import datetime, timezone

import structlog
from sqlalchemy import select

from models.cadence_step import CadenceStep
from models.enums import Channel, LeadStatus, StepStatus
from models.lead import Lead
from models.tenant import Tenant
from workers.celery_app import celery_app

logger = structlog.get_logger()

# Limites padrão caso o tenant não tenha configuração própria
_DEFAULT_LIMITS: dict[Channel, int] = {
    Channel.LINKEDIN_CONNECT: 20,
    Channel.LINKEDIN_DM: 40,
    Channel.EMAIL: 300,
}


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
    return asyncio.get_event_loop().run_until_complete(_tick_async())


async def _tick_async() -> dict:
    from core.database import get_session
    from core.redis_client import redis_client

    dispatched = 0
    skipped = 0

    # Busca todos os tenants ativos (sem filtro RLS — é a task de sistema)
    # Usa session sem tenant_id para listar tenants
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from core.config import settings

    engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as root_session:
        result = await root_session.execute(
            select(Tenant).where(Tenant.is_active.is_(True))
        )
        tenants: list[Tenant] = list(result.scalars().all())

    await engine.dispose()

    for tenant in tenants:
        tid = tenant.id
        try:
            async for db in get_session(tid):
                now = datetime.now(tz=timezone.utc)

                # Busca steps pendentes e vencidos deste tenant
                steps_result = await db.execute(
                    select(CadenceStep)
                    .where(
                        CadenceStep.tenant_id == tid,
                        CadenceStep.status == StepStatus.PENDING,
                        CadenceStep.scheduled_at <= now,
                    )
                    .order_by(CadenceStep.scheduled_at.asc())
                    .limit(200)
                )
                steps: list[CadenceStep] = list(steps_result.scalars().all())

                for step in steps:
                    # Verifica se o lead ainda está em cadência
                    lead_result = await db.execute(
                        select(Lead.status).where(Lead.id == step.lead_id)
                    )
                    lead_status = lead_result.scalar_one_or_none()

                    if lead_status != LeadStatus.IN_CADENCE:
                        step.status = StepStatus.SKIPPED
                        skipped += 1
                        logger.info(
                            "cadence_tick.step_skipped",
                            step_id=str(step.id),
                            reason="lead_not_in_cadence",
                            lead_status=str(lead_status),
                        )
                        continue

                    # Verifica rate limit
                    limit = _DEFAULT_LIMITS.get(step.channel, 40)
                    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
                    rate_key = f"ratelimit:{tid}:{step.channel.value}:{today}"

                    allowed = await redis_client.check_and_increment(
                        channel=step.channel.value,
                        tenant_id=tid,
                        limit=limit,
                    )
                    if not allowed:
                        logger.info(
                            "cadence_tick.rate_limited",
                            tenant_id=str(tid),
                            channel=step.channel.value,
                            rate_key=rate_key,
                        )
                        continue

                    # Enfileira o dispatch
                    from workers.dispatch import dispatch_step
                    dispatch_step.delay(str(step.id), str(tid))
                    dispatched += 1

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
