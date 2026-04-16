"""
workers/warmup.py

Task Celery para o ciclo de warmup de e-mail.

Tasks:
  warmup_tick()
    — Disparada pelo Celery Beat a cada 30 minutos
    — Verifica quais campanhas ativas ainda não enviaram o volume de hoje
    — Enfileira warmup_run_campaign para cada campanha pendente

  warmup_run_campaign(campaign_id, tenant_id)
    — Executa o ciclo diário de uma campanha específica
    — Delega para warmup_service.run_daily_warmup()
    — Fila: "cadence" (reusa fila existente)

A lógica de negócio (cálculo de volume, envio, logs) fica em warmup_service.
"""

from __future__ import annotations

import asyncio
from datetime import date
from typing import Any

import structlog
from sqlalchemy import select

from models.tenant import Tenant
from models.warmup import WarmupCampaign
from workers.celery_app import celery_app

logger = structlog.get_logger()

# Chave Redis para controlar que a campanha já rodou hoje
# Formato: warmup:ran:{campaign_id}:{YYYY-MM-DD}
_DAILY_KEY = "warmup:ran:{campaign_id}:{date}"


@celery_app.task(name="workers.warmup.warmup_tick", queue="cadence")
def warmup_tick() -> dict[str, Any]:
    """
    Tick do warmup — verifica campanhas ativas e enfileira execução diária.
    Cada campanha só roda uma vez por dia (controlado via Redis TTL).
    """
    return asyncio.run(_warmup_tick_async())


async def _warmup_tick_async() -> dict[str, Any]:
    from core.database import WorkerSessionLocal  # noqa: PLC0415
    from core.redis_client import redis_client  # noqa: PLC0415

    today = date.today().isoformat()
    enqueued = 0
    skipped = 0

    async with WorkerSessionLocal() as db:
        # Busca todos os tenants ativos
        tenant_result = await db.execute(select(Tenant.id).where(Tenant.is_active.is_(True)))
        tenant_ids = [row.id for row in tenant_result]

    for tenant_id in tenant_ids:
        async with WorkerSessionLocal() as db:
            # Busca campanhas ativas do tenant
            camp_result = await db.execute(
                select(WarmupCampaign).where(
                    WarmupCampaign.tenant_id == tenant_id,
                    WarmupCampaign.status == "active",
                )
            )
            campaigns = camp_result.scalars().all()

        for campaign in campaigns:
            redis_key = _DAILY_KEY.format(
                campaign_id=str(campaign.id),
                date=today,
            )
            # Verifica se já rodou hoje
            already_ran = await redis_client.get(redis_key)
            if already_ran:
                skipped += 1
                continue

            # Marca como rodando (TTL 26h para cobrir mudança de horário)
            await redis_client.setex(redis_key, 26 * 3600, "1")

            # Enfileira a execução
            warmup_run_campaign.apply_async(
                kwargs={
                    "campaign_id": str(campaign.id),
                    "tenant_id": str(tenant_id),
                },
                queue="cadence",
            )
            enqueued += 1

    logger.info(
        "warmup.tick_done",
        enqueued=enqueued,
        skipped=skipped,
    )
    return {"enqueued": enqueued, "skipped": skipped}


@celery_app.task(
    name="workers.warmup.warmup_run_campaign",
    bind=True,
    max_retries=2,
    queue="cadence",
)
def warmup_run_campaign(self, campaign_id: str, tenant_id: str) -> dict[str, Any]:
    """
    Executa o ciclo diário de warmup de uma campanha.
    Retenta até 2 vezes em caso de falha.
    """
    return asyncio.run(_warmup_run_campaign_async(campaign_id, tenant_id))


async def _warmup_run_campaign_async(
    campaign_id: str,
    tenant_id: str,
) -> dict[str, Any]:
    import uuid  # noqa: PLC0415

    from core.database import WorkerSessionLocal  # noqa: PLC0415
    from services.warmup_service import run_daily_warmup  # noqa: PLC0415

    _campaign_id = uuid.UUID(campaign_id)
    _tenant_id = uuid.UUID(tenant_id)

    async with WorkerSessionLocal() as db:
        # Injeta tenant para RLS
        await db.execute(
            __import__("sqlalchemy").text(f"SET LOCAL app.current_tenant_id = '{_tenant_id}'")
        )
        result = await run_daily_warmup(
            campaign_id=_campaign_id,
            tenant_id=_tenant_id,
            db=db,
        )

    logger.info(
        "warmup.campaign_cycle_done",
        campaign_id=campaign_id,
        result=result,
    )
    return result
