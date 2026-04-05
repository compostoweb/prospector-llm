"""
api/routes/content/themes.py

Endpoints para banco de temas editoriais.

GET    /content/themes           — listar (filtros: pillar, used)
POST   /content/themes           — criar tema customizado
PATCH  /content/themes/{id}/used — marcar como usado (vincula ao post)
DELETE /content/themes/{id}      — deletar (apenas is_custom=True)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_effective_tenant_id, get_session_flexible
from models.content_theme import ContentTheme
from schemas.content import ContentThemeCreate, ContentThemeResponse

logger = structlog.get_logger()

router = APIRouter(prefix="/themes", tags=["Content Hub — Themes"])


async def _get_theme_or_404(
    theme_id: uuid.UUID,
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> ContentTheme:
    result = await db.execute(
        select(ContentTheme).where(
            ContentTheme.id == theme_id,
            ContentTheme.tenant_id == tenant_id,
        )
    )
    theme = result.scalar_one_or_none()
    if theme is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tema nao encontrado")
    return theme


@router.get("", response_model=list[ContentThemeResponse])
async def list_themes(
    pillar: str | None = Query(default=None, description="authority | case | vision"),
    used: bool | None = Query(default=None, description="true/false — filtrar por status de uso"),
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> list[ContentThemeResponse]:
    stmt = select(ContentTheme).where(ContentTheme.tenant_id == tenant_id)
    if pillar:
        stmt = stmt.where(ContentTheme.pillar == pillar)
    if used is not None:
        stmt = stmt.where(ContentTheme.used == used)
    stmt = stmt.order_by(ContentTheme.created_at.desc())
    result = await db.execute(stmt)
    return [ContentThemeResponse.model_validate(t) for t in result.scalars().all()]


@router.post("", response_model=ContentThemeResponse, status_code=status.HTTP_201_CREATED)
async def create_theme(
    body: ContentThemeCreate,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ContentThemeResponse:
    theme = ContentTheme(
        tenant_id=tenant_id,
        title=body.title,
        pillar=body.pillar,
        is_custom=True,
    )
    db.add(theme)
    await db.commit()
    await db.refresh(theme)
    logger.info("content.theme_created", theme_id=str(theme.id), tenant_id=str(tenant_id))
    return ContentThemeResponse.model_validate(theme)


@router.patch("/{theme_id}/used", response_model=ContentThemeResponse)
async def mark_theme_used(
    theme_id: uuid.UUID,
    post_id: uuid.UUID | None = Query(
        default=None, description="ID do post em que o tema foi usado"
    ),
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ContentThemeResponse:
    theme = await _get_theme_or_404(theme_id, tenant_id, db)
    theme.used = True
    theme.used_at = datetime.now(UTC)
    if post_id:
        theme.used_in_post_id = post_id
    await db.commit()
    await db.refresh(theme)
    logger.info("content.theme_marked_used", theme_id=str(theme_id), tenant_id=str(tenant_id))
    return ContentThemeResponse.model_validate(theme)


@router.delete("/{theme_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_theme(
    theme_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> None:
    theme = await _get_theme_or_404(theme_id, tenant_id, db)
    if not theme.is_custom:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Apenas temas customizados (criados pelo usuario) podem ser deletados.",
        )
    await db.delete(theme)
    await db.commit()
    logger.info("content.theme_deleted", theme_id=str(theme_id), tenant_id=str(tenant_id))
