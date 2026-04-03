"""
api/routes/content/settings.py

Configuracoes do Content Hub por tenant.

GET /content/settings — buscar configuracoes do tenant (cria default se nao existir)
PUT /content/settings — atualizar configuracoes (upsert)
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_effective_tenant_id, get_session_flexible
from models.content_settings import ContentSettings
from schemas.content import ContentSettingsResponse, ContentSettingsUpdate

logger = structlog.get_logger()

router = APIRouter(prefix="/settings", tags=["Content Hub — Settings"])


async def _get_or_create_settings(
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> ContentSettings:
    result = await db.execute(
        select(ContentSettings).where(ContentSettings.tenant_id == tenant_id)
    )
    settings_obj = result.scalar_one_or_none()
    if settings_obj is None:
        settings_obj = ContentSettings(tenant_id=tenant_id)
        db.add(settings_obj)
        await db.commit()
        await db.refresh(settings_obj)
    return settings_obj


@router.get("", response_model=ContentSettingsResponse)
async def get_settings(
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ContentSettingsResponse:
    settings_obj = await _get_or_create_settings(tenant_id, db)
    return ContentSettingsResponse.model_validate(settings_obj)


@router.put("", response_model=ContentSettingsResponse)
async def update_settings(
    body: ContentSettingsUpdate,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ContentSettingsResponse:
    settings_obj = await _get_or_create_settings(tenant_id, db)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(settings_obj, field, value)
    await db.commit()
    await db.refresh(settings_obj)
    logger.info("content.settings_updated", tenant_id=str(tenant_id))
    return ContentSettingsResponse.model_validate(settings_obj)
