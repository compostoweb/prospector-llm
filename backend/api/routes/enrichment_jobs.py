"""
api/routes/enrichment_jobs.py

Endpoints para gerenciamento de filas de enriquecimento em lote.

Endpoints:
  GET    /enrichment-jobs              — lista jobs do tenant
  POST   /enrichment-jobs              — cria um novo job (recebe lista de URLs)
  GET    /enrichment-jobs/{id}         — detalhes de um job
  DELETE /enrichment-jobs/{id}         — cancela / remove um job
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_effective_tenant_id, get_session_flexible
from models.enrichment_job import EnrichmentJob
from schemas.enrichment_job import EnrichmentJobCreate, EnrichmentJobResponse
from services.lead_management import get_or_create_list

logger = structlog.get_logger()
router = APIRouter(prefix="/enrichment-jobs", tags=["Enrichment Jobs"])


@router.get("", response_model=list[EnrichmentJobResponse])
async def list_enrichment_jobs(
    db: AsyncSession = Depends(get_session_flexible),
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
) -> list[EnrichmentJob]:
    result = await db.execute(
        select(EnrichmentJob)
        .where(EnrichmentJob.tenant_id == tenant_id)
        .order_by(EnrichmentJob.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("", response_model=EnrichmentJobResponse, status_code=status.HTTP_201_CREATED)
async def create_enrichment_job(
    payload: EnrichmentJobCreate,
    db: AsyncSession = Depends(get_session_flexible),
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
) -> EnrichmentJob:
    # Normaliza e deduplica as URLs
    unique_urls: list[str] = list(dict.fromkeys(
        u.strip() for u in payload.linkedin_urls if u.strip()
    ))

    if not unique_urls:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Nenhuma URL válida fornecida",
        )

    # Resolve ou cria a lista alvo
    target_list = await get_or_create_list(
        db,
        tenant_id=tenant_id,
        list_id=payload.target_list_id,
        create_list_name=payload.target_list_name,
    )

    job = EnrichmentJob(
        tenant_id=tenant_id,
        linkedin_urls=unique_urls,
        batch_size=payload.batch_size,
        processed_count=0,
        total_count=len(unique_urls),
        status="pending",
        target_list_id=target_list.id if target_list else None,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    logger.info(
        "enrichment_job.created",
        job_id=str(job.id),
        tenant_id=str(tenant_id),
        total_count=job.total_count,
        batch_size=job.batch_size,
    )
    return job


@router.get("/{job_id}", response_model=EnrichmentJobResponse)
async def get_enrichment_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_session_flexible),
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
) -> EnrichmentJob:
    job = await _get_job(db, tenant_id, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job não encontrado")
    return job


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_enrichment_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_session_flexible),
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
) -> None:
    job = await _get_job(db, tenant_id, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job não encontrado")
    if job.status == "running":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job em execução — aguarde o batch atual terminar antes de cancelar",
        )
    await db.delete(job)
    await db.commit()
    logger.info("enrichment_job.deleted", job_id=str(job_id), tenant_id=str(tenant_id))


# ── Helpers ───────────────────────────────────────────────────────────


async def _get_job(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    job_id: uuid.UUID,
) -> EnrichmentJob | None:
    result = await db.execute(
        select(EnrichmentJob).where(
            EnrichmentJob.id == job_id,
            EnrichmentJob.tenant_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()
