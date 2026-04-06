"""
api/routes/lead_analysis.py

Endpoints para análise de leads via Anthropic Batches API.

POST /leads/analyze-batch      — submete um batch de leads para análise de ICP
GET  /leads/analyze-batch/{id} — status do job de análise
"""

from __future__ import annotations

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_effective_tenant_id, get_session_flexible
from models.anthropic_batch_job import AnthropicBatchJob

logger = structlog.get_logger()

router = APIRouter(prefix="/leads", tags=["Lead Analysis"])


# ── Schemas ───────────────────────────────────────────────────────────


class AnalyzeBatchRequest(BaseModel):
    lead_ids: list[uuid.UUID] = Field(..., min_length=1, max_length=500)
    model: str | None = Field(
        None, description="Modelo Anthropic (padrão: claude-haiku-4-5)"
    )


class AnalyzeBatchResponse(BaseModel):
    job_id: uuid.UUID
    batch_id: str
    status: str
    count: int
    message: str


class BatchJobStatusResponse(BaseModel):
    job_id: uuid.UUID
    batch_id: str
    status: str
    request_count: int
    succeeded_count: int | None
    failed_count: int | None
    expired_count: int | None
    model: str | None
    ended_at: str | None
    created_at: str | None


# ── Endpoints ─────────────────────────────────────────────────────────


@router.post(
    "/analyze-batch",
    response_model=AnalyzeBatchResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submete leads para análise de ICP via Anthropic Batches",
)
async def submit_analyze_batch(
    body: AnalyzeBatchRequest,
    db: AsyncSession = Depends(get_session_flexible),
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
) -> AnalyzeBatchResponse:
    """
    Enfileira um batch de leads para análise assíncrona de ICP via Anthropic.

    O processamento pode demorar até 24h. Use GET /leads/analyze-batch/{id}
    para acompanhar o status.
    """
    from core.config import settings

    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ANTHROPIC_API_KEY não configurada.",
        )

    # Dispara a task Celery de forma assíncrona
    from workers.anthropic_batch import submit_lead_analysis_batch

    task_kwargs: dict = {
        "tenant_id": str(tenant_id),
        "lead_ids": [str(lid) for lid in body.lead_ids],
    }
    if body.model:
        task_kwargs["model"] = body.model

    submit_lead_analysis_batch.apply_async(kwargs=task_kwargs)

    logger.info(
        "lead_analysis.batch_enqueued",
        tenant_id=str(tenant_id),
        count=len(body.lead_ids),
    )

    return AnalyzeBatchResponse(
        job_id=uuid.uuid4(),  # placeholder — job real criado dentro do worker
        batch_id="pending",
        status="queued",
        count=len(body.lead_ids),
        message=f"{len(body.lead_ids)} lead(s) enfileirado(s) para análise.",
    )


@router.post(
    "/analyze-batch/sync",
    response_model=AnalyzeBatchResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submete análise de ICP e retorna job_id imediatamente",
)
async def submit_analyze_batch_sync(
    body: AnalyzeBatchRequest,
    db: AsyncSession = Depends(get_session_flexible),
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
) -> AnalyzeBatchResponse:
    """
    Submete o batch diretamente (sem fila) e retorna o job_id real para rastreamento.
    Use este endpoint quando precisar do job_id imediatamente.
    """
    from core.config import settings
    from models.lead import Lead
    from services.anthropic_batch_service import submit_lead_analysis_batch as _submit

    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ANTHROPIC_API_KEY não configurada.",
        )

    lead_uuids = body.lead_ids
    result = await db.execute(
        select(Lead).where(
            Lead.id.in_(lead_uuids),
            Lead.tenant_id == tenant_id,
        )
    )
    leads = list(result.scalars().all())

    if not leads:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhum lead encontrado para os IDs informados.",
        )

    kwargs: dict = {"leads": leads, "tenant_id": tenant_id, "db": db}
    if body.model:
        kwargs["model"] = body.model

    job = await _submit(**kwargs)
    await db.commit()

    return AnalyzeBatchResponse(
        job_id=job.id,
        batch_id=job.anthropic_batch_id,
        status=job.status,
        count=len(leads),
        message=f"{len(leads)} lead(s) enviado(s) para análise. Processamento em até 24h.",
    )


@router.get(
    "/analyze-batch/{job_id}",
    response_model=BatchJobStatusResponse,
    summary="Consulta o status de um job de análise",
)
async def get_batch_job_status(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_session_flexible),
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
) -> BatchJobStatusResponse:
    """Retorna o status atual de um job de análise de leads."""
    result = await db.execute(
        select(AnthropicBatchJob).where(
            AnthropicBatchJob.id == job_id,
            AnthropicBatchJob.tenant_id == tenant_id,
        )
    )
    job = result.scalar_one_or_none()

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job não encontrado.",
        )

    return BatchJobStatusResponse(
        job_id=job.id,
        batch_id=job.anthropic_batch_id,
        status=job.status,
        request_count=job.request_count or 0,
        succeeded_count=job.succeeded_count,
        failed_count=job.failed_count,
        expired_count=job.expired_count,
        model=job.model,
        ended_at=job.ended_at.isoformat() if job.ended_at else None,
        created_at=job.created_at.isoformat() if job.created_at else None,
    )
