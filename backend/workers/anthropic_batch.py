"""
workers/anthropic_batch.py

Tasks Celery para análise de leads via Anthropic Message Batches API.

Tasks:
  submit_lead_analysis_batch  — submete um batch de leads para análise de ICP
  poll_anthropic_batches      — verifica batches in_progress e processa resultados

Filas:
  submit_lead_analysis_batch → "enrich"
  poll_anthropic_batches     → "enrich"
"""

from __future__ import annotations

import asyncio
import uuid

import structlog
from sqlalchemy import select

from workers.celery_app import celery_app

logger = structlog.get_logger()

_POLL_BATCH_SIZE = 50


@celery_app.task(
    bind=True,
    name="workers.anthropic_batch.submit_lead_analysis_batch",
    max_retries=2,
    default_retry_delay=60,
    queue="enrich",
    ignore_result=True,
)
def submit_lead_analysis_batch(
    self,
    tenant_id: str,
    lead_ids: list[str],
    model: str | None = None,
) -> dict:
    """
    Submete um lote de leads para análise de ICP via Anthropic Batches API.

    Args:
        tenant_id: UUID do tenant como string
        lead_ids: Lista de UUIDs de leads como strings
        model: Modelo Anthropic a usar (padrão: claude-haiku-4-5)

    Returns:
        {"job_id": "...", "batch_id": "...", "count": N}
    """
    return asyncio.run(
        _submit_batch_async(tenant_id, lead_ids, model, self)
    )


async def _submit_batch_async(
    tenant_id: str,
    lead_ids: list[str],
    model: str | None,
    task,
) -> dict:
    from core.database import WorkerSessionLocal
    from models.lead import Lead
    from services.anthropic_batch_service import submit_lead_analysis_batch as _submit

    tenant_uuid = uuid.UUID(tenant_id)
    lead_uuids = [uuid.UUID(lid) for lid in lead_ids]

    async with WorkerSessionLocal() as db:
        result = await db.execute(
            select(Lead).where(
                Lead.id.in_(lead_uuids),
                Lead.tenant_id == tenant_uuid,
            )
        )
        leads = list(result.scalars().all())

        if not leads:
            logger.warning(
                "anthropic_batch_worker.no_leads_found",
                tenant_id=tenant_id,
                requested=len(lead_ids),
            )
            return {"job_id": None, "batch_id": None, "count": 0}

        kwargs: dict = {"leads": leads, "tenant_id": tenant_uuid, "db": db}
        if model:
            kwargs["model"] = model

        job = await _submit(**kwargs)
        await db.commit()

        return {
            "job_id": str(job.id),
            "batch_id": job.anthropic_batch_id,
            "count": len(leads),
        }


@celery_app.task(
    bind=True,
    name="workers.anthropic_batch.poll_anthropic_batches",
    max_retries=0,
    queue="enrich",
    ignore_result=True,
)
def poll_anthropic_batches(self) -> dict:
    """
    Verifica o status de todos os jobs Anthropic in_progress.

    Executado periodicamente pelo Celery Beat a cada 5 minutos.
    Para cada job finalizado, baixa e processa os resultados.

    Returns:
        {"polled": N, "ended": M, "processed_leads": K}
    """
    return asyncio.run(_poll_batches_async())


async def _poll_batches_async() -> dict:
    from core.database import WorkerSessionLocal
    from services.anthropic_batch_service import (
        get_pending_jobs,
        poll_batch,
        process_batch_results,
    )

    polled = 0
    ended = 0
    processed_leads = 0

    async with WorkerSessionLocal() as db:
        jobs = await get_pending_jobs(db, limit=_POLL_BATCH_SIZE)

        for job in jobs:
            polled += 1
            try:
                is_done = await poll_batch(job)
                if is_done:
                    ended += 1
                    count = await process_batch_results(job, db)
                    processed_leads += count
                    job.status = "processed"
            except Exception as exc:
                logger.error(
                    "anthropic_batch_worker.poll_error",
                    batch_id=job.anthropic_batch_id,
                    error=str(exc),
                )

        if ended:
            await db.commit()

    logger.info(
        "anthropic_batch_worker.poll_done",
        polled=polled,
        ended=ended,
        processed_leads=processed_leads,
    )
    return {"polled": polled, "ended": ended, "processed_leads": processed_leads}
