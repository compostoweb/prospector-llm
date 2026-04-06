"""
workers/content_voyager.py

Tasks Celery para sincronizacao de analytics LinkedIn via Unipile API.

Tasks:
  sync_tenant_voyager(tenant_id)
    — Sincroniza metricas de um tenant especifico via Unipile
    — Fila: "content"

  sync_all_voyager()
    — Itera todos os tenants com conta Unipile e dispara sync_tenant_voyager
    — Executada via Celery Beat 3x/dia (08h, 14h, 20h)
    — Fila: "content"
"""

from __future__ import annotations

import asyncio

import structlog

from workers.celery_app import celery_app

logger = structlog.get_logger()


# ── sync_tenant_voyager ───────────────────────────────────────────────

@celery_app.task(
    bind=True,
    name="workers.content_voyager.sync_tenant_voyager",
    max_retries=2,
    default_retry_delay=300,  # 5 min antes de retry
    queue="content",
)
def sync_tenant_voyager(self, tenant_id: str) -> dict:  # type: ignore[type-arg]
    """Sincroniza analytics Voyager para um tenant especifico."""
    return asyncio.run(
        _sync_tenant_async(tenant_id, self)
    )


async def _sync_tenant_async(tenant_id: str, task) -> dict:  # type: ignore[type-arg]
    from core.database import WorkerSessionLocal
    from services.content.voyager_sync_service import sync_voyager_for_tenant

    async with WorkerSessionLocal() as db:
        try:
            result = await sync_voyager_for_tenant(
                tenant_id=tenant_id,
                db=db,
            )
            if not result.success:
                logger.warning(
                    "voyager_task.sync_failed",
                    tenant_id=tenant_id,
                    error=result.error,
                )
            return result.to_dict()
        except Exception as exc:
            logger.error(
                "voyager_task.unexpected_error",
                tenant_id=tenant_id,
                error=str(exc),
            )
            try:
                raise task.retry(exc=exc)
            except task.MaxRetriesExceededError:
                return {"tenant_id": tenant_id, "error": str(exc), "success": False}


# ── sync_all_voyager ──────────────────────────────────────────────────

@celery_app.task(
    name="workers.content_voyager.sync_all_voyager",
    queue="content",
)
def sync_all_voyager() -> dict:  # type: ignore[type-arg]
    """
    Itera todos os tenants ativos com li_at configurado e dispara sincronizacao.
    Executado pelo Celery Beat 3x/dia.
    """
    return asyncio.run(_sync_all_async())


async def _sync_all_async() -> dict:
    from sqlalchemy import select

    from core.database import WorkerSessionLocal
    from models.linkedin_account import LinkedInAccount

    dispatched = 0
    async with WorkerSessionLocal() as db:
        stmt = select(LinkedInAccount.tenant_id).where(
            LinkedInAccount.is_active.is_(True),
            LinkedInAccount.unipile_account_id.is_not(None),
        ).distinct()
        rows = await db.execute(stmt)
        tenant_ids = [str(row[0]) for row in rows.fetchall()]

    for tenant_id in tenant_ids:
        sync_tenant_voyager.delay(tenant_id)
        dispatched += 1

    logger.info("voyager_task.all_dispatched", dispatched=dispatched)
    return {"dispatched": dispatched, "tenant_ids": tenant_ids}
