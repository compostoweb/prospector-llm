"""
api/routes/content/posts.py

Endpoints CRUD para posts do calendario editorial.

GET    /content/posts              — listagem (filtros: status, pillar, week_number)
POST   /content/posts              — criar post
GET    /content/posts/{id}         — buscar por ID
PUT    /content/posts/{id}         — atualizar
DELETE /content/posts/{id}         — deletar (apenas status=draft)
PATCH  /content/posts/{id}/approve — draft -> approved
POST   /content/posts/{id}/metrics — atualizar metricas manualmente
POST   /content/posts/{id}/schedule     — aprovado -> agendado (publish_date obrigatorio)
DELETE /content/posts/{id}/schedule     — cancelar agendamento (scheduled -> approved)
POST   /content/posts/{id}/publish-now  — publica imediatamente (approved | scheduled)
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_effective_tenant_id, get_session_flexible
from models.content_post import ContentPost
from schemas.content import (
    ContentPostCreate,
    ContentPostMetricsUpdate,
    ContentPostResponse,
    ContentPostUpdate,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/posts", tags=["Content Hub — Posts"])


# ── Helper ────────────────────────────────────────────────────────────

async def _get_post_or_404(
    post_id: uuid.UUID,
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> ContentPost:
    result = await db.execute(
        select(ContentPost).where(
            ContentPost.id == post_id,
            ContentPost.tenant_id == tenant_id,
        )
    )
    post = result.scalar_one_or_none()
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post nao encontrado")
    return post


# ── Listagem ──────────────────────────────────────────────────────────

@router.get("", response_model=list[ContentPostResponse])
async def list_posts(
    post_status: str | None = Query(default=None, alias="status", description="draft | approved | scheduled | published | failed"),
    pillar: str | None = Query(default=None, description="authority | case | vision"),
    week_number: int | None = Query(default=None, ge=1, le=54),
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> list[ContentPostResponse]:
    stmt = select(ContentPost).where(ContentPost.tenant_id == tenant_id)
    if post_status:
        stmt = stmt.where(ContentPost.status == post_status)
    if pillar:
        stmt = stmt.where(ContentPost.pillar == pillar)
    if week_number:
        stmt = stmt.where(ContentPost.week_number == week_number)
    stmt = stmt.order_by(ContentPost.publish_date.asc().nulls_last(), ContentPost.created_at.desc())
    result = await db.execute(stmt)
    return [ContentPostResponse.model_validate(p) for p in result.scalars().all()]


# ── Criacao ───────────────────────────────────────────────────────────

@router.post("", response_model=ContentPostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    body: ContentPostCreate,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ContentPostResponse:
    char_count = body.character_count if body.character_count is not None else len(body.body)
    post = ContentPost(
        tenant_id=tenant_id,
        title=body.title,
        body=body.body,
        pillar=body.pillar,
        hook_type=body.hook_type,
        hashtags=body.hashtags,
        character_count=char_count,
        publish_date=body.publish_date,
        week_number=body.week_number,
        status="draft",
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)
    logger.info("content.post_created", post_id=str(post.id), tenant_id=str(tenant_id))
    return ContentPostResponse.model_validate(post)


# ── Detalhe ───────────────────────────────────────────────────────────

@router.get("/{post_id}", response_model=ContentPostResponse)
async def get_post(
    post_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ContentPostResponse:
    post = await _get_post_or_404(post_id, tenant_id, db)
    return ContentPostResponse.model_validate(post)


# ── Atualizacao ───────────────────────────────────────────────────────

@router.put("/{post_id}", response_model=ContentPostResponse)
async def update_post(
    post_id: uuid.UUID,
    body: ContentPostUpdate,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ContentPostResponse:
    post = await _get_post_or_404(post_id, tenant_id, db)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(post, field, value)
    await db.commit()
    await db.refresh(post)
    logger.info("content.post_updated", post_id=str(post_id), tenant_id=str(tenant_id))
    return ContentPostResponse.model_validate(post)


# ── Delete ────────────────────────────────────────────────────────────

@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_post(
    post_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> None:
    post = await _get_post_or_404(post_id, tenant_id, db)
    if post.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Nao e possivel deletar post com status '{post.status}'. Apenas drafts podem ser deletados.",
        )
    await db.delete(post)
    await db.commit()
    logger.info("content.post_deleted", post_id=str(post_id), tenant_id=str(tenant_id))


# ── Aprovacao ─────────────────────────────────────────────────────────

@router.patch("/{post_id}/approve", response_model=ContentPostResponse)
async def approve_post(
    post_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ContentPostResponse:
    post = await _get_post_or_404(post_id, tenant_id, db)
    if post.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Apenas posts em 'draft' podem ser aprovados. Status atual: '{post.status}'.",
        )
    post.status = "approved"
    await db.commit()
    await db.refresh(post)
    logger.info("content.post_approved", post_id=str(post_id), tenant_id=str(tenant_id))
    return ContentPostResponse.model_validate(post)


# ── Metricas manuais ──────────────────────────────────────────────────

@router.post("/{post_id}/metrics", response_model=ContentPostResponse)
async def update_metrics(
    post_id: uuid.UUID,
    body: ContentPostMetricsUpdate,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ContentPostResponse:
    from datetime import datetime, timezone

    post = await _get_post_or_404(post_id, tenant_id, db)
    post.impressions = body.impressions
    post.likes = body.likes
    post.comments = body.comments
    post.shares = body.shares
    if body.engagement_rate is not None:
        post.engagement_rate = body.engagement_rate
    post.metrics_updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(post)
    logger.info("content.post_metrics_updated", post_id=str(post_id), tenant_id=str(tenant_id))
    return ContentPostResponse.model_validate(post)


# ── Agendamento ───────────────────────────────────────────────────────

@router.post("/{post_id}/schedule", response_model=ContentPostResponse)
async def schedule_post(
    post_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ContentPostResponse:
    """
    Marca post aprovado como agendado (status=scheduled).

    Requer:
    - post.status == approved
    - post.publish_date definido e no futuro

    O Celery Beat check_scheduled_posts publicara o post quando publish_date chegar.
    """
    from services.content.publisher import schedule_post as svc_schedule

    try:
        post = await svc_schedule(db, post_id=post_id, tenant_id=tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    logger.info("content.post_scheduled_api", post_id=str(post_id), tenant_id=str(tenant_id))
    return ContentPostResponse.model_validate(post)


@router.delete(
    "/{post_id}/schedule",
    status_code=status.HTTP_200_OK,
    response_model=ContentPostResponse,
)
async def cancel_schedule(
    post_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ContentPostResponse:
    """
    Cancela agendamento (scheduled → approved).

    Se o post tiver linkedin_scheduled_id, tenta cancelar no LinkedIn.
    """
    from services.content.publisher import cancel_schedule as svc_cancel

    try:
        post = await svc_cancel(db, post_id=post_id, tenant_id=tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    logger.info("content.schedule_cancelled_api", post_id=str(post_id), tenant_id=str(tenant_id))
    return ContentPostResponse.model_validate(post)


@router.post("/{post_id}/publish-now", response_model=ContentPostResponse)
async def publish_now(
    post_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ContentPostResponse:
    """
    Publica o post imediatamente via LinkedIn API (sincrono).

    Requer post.status == approved | scheduled.
    Requer conta LinkedIn ativa conectada.
    """
    from services.content.publisher import publish_now as svc_publish
    from services.content.linkedin_client import LinkedInClientError

    try:
        post = await svc_publish(db, post_id=post_id, tenant_id=tenant_id)
    except LinkedInClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LinkedIn API error {exc.status_code}: {exc.detail}",
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    logger.info("content.post_published_api", post_id=str(post_id), tenant_id=str(tenant_id))
    return ContentPostResponse.model_validate(post)
