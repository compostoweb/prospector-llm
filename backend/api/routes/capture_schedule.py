"""
api/routes/capture_schedule.py

Endpoints para configuração de captura automática agendada.

Endpoints:
  GET    /capture-schedule                   — lista configs do tenant
  GET    /capture-schedule/{source}          — config de uma fonte específica
  PUT    /capture-schedule/{source}          — cria ou atualiza config (upsert)
  DELETE /capture-schedule/{source}          — desativa config
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_effective_tenant_id, get_session_flexible
from models.capture_schedule import CaptureScheduleConfig
from schemas.capture_schedule import CaptureScheduleResponse, CaptureScheduleUpsert

logger = structlog.get_logger()
router = APIRouter(prefix="/capture-schedule", tags=["Capture Schedule"])


@router.get("", response_model=list[CaptureScheduleResponse])
async def list_capture_schedules(
    db: AsyncSession = Depends(get_session_flexible),
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
) -> list[CaptureScheduleConfig]:
    result = await db.execute(
        select(CaptureScheduleConfig).where(
            CaptureScheduleConfig.tenant_id == tenant_id
        )
    )
    return list(result.scalars().all())


@router.get("/{source}", response_model=CaptureScheduleResponse)
async def get_capture_schedule(
    source: str,
    db: AsyncSession = Depends(get_session_flexible),
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
) -> CaptureScheduleConfig:
    config = await _get_config(db, tenant_id, source)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Config não encontrada")
    return config


@router.put("/{source}", response_model=CaptureScheduleResponse, status_code=status.HTTP_200_OK)
async def upsert_capture_schedule(
    source: str,
    payload: CaptureScheduleUpsert,
    db: AsyncSession = Depends(get_session_flexible),
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
) -> CaptureScheduleConfig:
    if source != payload.source:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="source no path deve ser igual ao source no body",
        )

    config = await _get_config(db, tenant_id, source)

    if config is None:
        config = CaptureScheduleConfig(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            source=source,
        )
        db.add(config)

    config.is_active = payload.is_active
    config.max_items = payload.max_items
    config.maps_search_terms = payload.maps_search_terms or None
    config.maps_location = payload.maps_location
    config.maps_categories = payload.maps_categories or None
    config.b2b_job_titles = payload.b2b_job_titles or None
    config.b2b_locations = payload.b2b_locations or None
    config.b2b_cities = payload.b2b_cities or None
    config.b2b_industries = payload.b2b_industries or None
    config.b2b_company_keywords = payload.b2b_company_keywords or None
    config.b2b_company_sizes = payload.b2b_company_sizes or None
    config.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(config)

    logger.info(
        "capture_schedule.upserted",
        tenant_id=str(tenant_id),
        source=source,
        is_active=config.is_active,
    )
    return config


@router.delete("/{source}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def disable_capture_schedule(
    source: str,
    db: AsyncSession = Depends(get_session_flexible),
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
) -> None:
    config = await _get_config(db, tenant_id, source)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Config não encontrada")

    config.is_active = False
    config.updated_at = datetime.now(timezone.utc)
    await db.commit()

    logger.info("capture_schedule.disabled", tenant_id=str(tenant_id), source=source)


async def _get_config(
    db: AsyncSession, tenant_id: uuid.UUID, source: str
) -> CaptureScheduleConfig | None:
    result = await db.execute(
        select(CaptureScheduleConfig).where(
            CaptureScheduleConfig.tenant_id == tenant_id,
            CaptureScheduleConfig.source == source,
        )
    )
    return result.scalar_one_or_none()
