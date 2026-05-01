"""
api/routes/content/articles.py

Endpoints de Article (link share LinkedIn Posts API).

GET    /content/articles
POST   /content/articles
GET    /content/articles/{id}
PUT    /content/articles/{id}
DELETE /content/articles/{id}
POST   /content/articles/{id}/restore
POST   /content/articles/scrape-url            (preview metadados)
POST   /content/articles/{id}/upload-thumbnail
DELETE /content/articles/{id}/thumbnail
POST   /content/articles/{id}/schedule
DELETE /content/articles/{id}/schedule
POST   /content/articles/{id}/publish-now
PATCH  /content/articles/{id}/approve
POST   /content/articles/{id}/metrics
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_effective_tenant_id, get_session_flexible
from models.content_article import ContentArticle
from schemas.content_article import (
    ArticleCreate,
    ArticleMetricsUpdate,
    ArticleResponse,
    ArticleScheduleRequest,
    ArticleScrapeRequest,
    ArticleScrapeResponse,
    ArticleUpdate,
)
from services.content.article_service import publish_article_now
from services.content.linkedin_client import LinkedInClientError
from services.content.url_scraper import scrape_url

logger = structlog.get_logger()

router = APIRouter(prefix="/articles", tags=["Content Hub — Articles"])


# ── Helpers ──────────────────────────────────────────────────────────


async def _get_or_404(aid: uuid.UUID, tenant_id: uuid.UUID, db: AsyncSession) -> ContentArticle:
    result = await db.execute(
        select(ContentArticle).where(
            ContentArticle.id == aid,
            ContentArticle.tenant_id == tenant_id,
        )
    )
    obj = result.scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article nao encontrado")
    return obj


# ── Scrape URL (sem id, antes de criar) ──────────────────────────────


@router.post("/scrape-url", response_model=ArticleScrapeResponse)
async def scrape(body: ArticleScrapeRequest) -> ArticleScrapeResponse:
    meta = await scrape_url(body.source_url)
    return ArticleScrapeResponse(
        title=meta.get("title"),
        description=meta.get("description"),
        thumbnail_url=meta.get("thumbnail_url"),
        cached=False,
    )


# ── List / CRUD ──────────────────────────────────────────────────────


@router.get("", response_model=list[ArticleResponse])
async def list_articles(
    art_status: str | None = Query(default=None, alias="status"),
    include_deleted: bool = Query(default=False),
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> list[ArticleResponse]:
    stmt = select(ContentArticle).where(ContentArticle.tenant_id == tenant_id)
    if not include_deleted:
        stmt = stmt.where(ContentArticle.deleted_at.is_(None))
    if art_status:
        stmt = stmt.where(ContentArticle.status == art_status)
    stmt = stmt.order_by(
        ContentArticle.scheduled_for.asc().nulls_last(),
        ContentArticle.created_at.desc(),
    )
    result = await db.execute(stmt)
    return [ArticleResponse.model_validate(a) for a in result.scalars().all()]


@router.post("", response_model=ArticleResponse, status_code=status.HTTP_201_CREATED)
async def create_article(
    body: ArticleCreate,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ArticleResponse:
    obj = ContentArticle(
        tenant_id=tenant_id,
        source_url=body.source_url,
        title=body.title,
        description=body.description,
        thumbnail_url=body.thumbnail_url,
        thumbnail_s3_key=body.thumbnail_s3_key,
        commentary=body.commentary,
        scheduled_for=body.scheduled_for,
        source_newsletter_id=body.source_newsletter_id,
        auto_scraped=body.auto_scraped,
        first_comment_text=body.first_comment_text,
        status="draft",
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    logger.info("content.article_created", article_id=str(obj.id), tenant_id=str(tenant_id))
    return ArticleResponse.model_validate(obj)


@router.get("/{aid}", response_model=ArticleResponse)
async def get_article(
    aid: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ArticleResponse:
    obj = await _get_or_404(aid, tenant_id, db)
    return ArticleResponse.model_validate(obj)


@router.put("/{aid}", response_model=ArticleResponse)
async def update_article(
    aid: uuid.UUID,
    body: ArticleUpdate,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ArticleResponse:
    obj = await _get_or_404(aid, tenant_id, db)
    if obj.deleted_at is not None:
        raise HTTPException(status_code=409, detail="Article foi deletado")
    data = body.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(obj, key, value)
    await db.commit()
    await db.refresh(obj)
    return ArticleResponse.model_validate(obj)


@router.delete("/{aid}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_article(
    aid: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> None:
    obj = await _get_or_404(aid, tenant_id, db)
    if obj.deleted_at is None:
        obj.deleted_at = datetime.now(UTC)
        obj.status = "deleted"
        await db.commit()


@router.post("/{aid}/restore", response_model=ArticleResponse)
async def restore_article(
    aid: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ArticleResponse:
    obj = await _get_or_404(aid, tenant_id, db)
    if obj.deleted_at is None:
        return ArticleResponse.model_validate(obj)
    obj.deleted_at = None
    obj.status = "draft"
    await db.commit()
    await db.refresh(obj)
    return ArticleResponse.model_validate(obj)


# ── Approve / schedule / cancel ──────────────────────────────────────


@router.patch("/{aid}/approve", response_model=ArticleResponse)
async def approve_article(
    aid: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ArticleResponse:
    obj = await _get_or_404(aid, tenant_id, db)
    if obj.status != "draft":
        raise HTTPException(status_code=409, detail=f"Article com status {obj.status}")
    obj.status = "approved"
    await db.commit()
    await db.refresh(obj)
    return ArticleResponse.model_validate(obj)


@router.post("/{aid}/schedule", response_model=ArticleResponse)
async def schedule_article(
    aid: uuid.UUID,
    body: ArticleScheduleRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ArticleResponse:
    obj = await _get_or_404(aid, tenant_id, db)
    if obj.status not in ("draft", "approved", "scheduled"):
        raise HTTPException(status_code=409, detail=f"Status invalido: {obj.status}")
    obj.scheduled_for = body.scheduled_for
    obj.status = "scheduled"
    await db.commit()
    await db.refresh(obj)
    return ArticleResponse.model_validate(obj)


@router.delete("/{aid}/schedule", response_model=ArticleResponse)
async def cancel_article_schedule(
    aid: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ArticleResponse:
    obj = await _get_or_404(aid, tenant_id, db)
    if obj.status != "scheduled":
        raise HTTPException(status_code=409, detail="Article nao esta agendado")
    obj.scheduled_for = None
    obj.status = "approved"
    await db.commit()
    await db.refresh(obj)
    return ArticleResponse.model_validate(obj)


@router.post("/{aid}/publish-now", response_model=ArticleResponse)
async def publish_article(
    aid: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ArticleResponse:
    try:
        article = await publish_article_now(db, article_id=aid, tenant_id=tenant_id)
    except LinkedInClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LinkedIn API error {exc.status_code}: {exc.detail}",
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return ArticleResponse.model_validate(article)


# ── Thumbnail upload ─────────────────────────────────────────────────


_MAX_IMAGE_SIZE = 10 * 1024 * 1024
_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


@router.post("/{aid}/upload-thumbnail", response_model=ArticleResponse)
async def upload_thumbnail(
    aid: uuid.UUID,
    file: UploadFile = File(...),
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ArticleResponse:
    from integrations.s3_client import S3Client

    obj = await _get_or_404(aid, tenant_id, db)

    if file.content_type not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=415, detail=f"Tipo nao suportado: {file.content_type}")
    payload = await file.read()
    if len(payload) > _MAX_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail="Imagem maior que 10MB")

    s3 = S3Client()
    key = f"articles/{tenant_id}/{aid}/thumb-{uuid.uuid4().hex}"
    url = s3.upload_bytes(payload, key, content_type=file.content_type or "image/jpeg")

    if obj.thumbnail_s3_key:
        try:
            s3.delete_object(obj.thumbnail_s3_key)
        except Exception:
            pass

    obj.thumbnail_url = url
    obj.thumbnail_s3_key = key
    obj.linkedin_image_urn = None  # invalida o URN antigo
    await db.commit()
    await db.refresh(obj)
    return ArticleResponse.model_validate(obj)


@router.delete("/{aid}/thumbnail", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_thumbnail(
    aid: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> None:
    from integrations.s3_client import S3Client

    obj = await _get_or_404(aid, tenant_id, db)
    if obj.thumbnail_s3_key:
        try:
            S3Client().delete_object(obj.thumbnail_s3_key)
        except Exception:
            pass
    obj.thumbnail_url = None
    obj.thumbnail_s3_key = None
    obj.linkedin_image_urn = None
    await db.commit()


# ── Metrics ──────────────────────────────────────────────────────────


@router.post("/{aid}/metrics", response_model=ArticleResponse)
async def update_metrics(
    aid: uuid.UUID,
    body: ArticleMetricsUpdate,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ArticleResponse:
    obj = await _get_or_404(aid, tenant_id, db)
    obj.impressions = body.impressions
    obj.likes = body.likes
    obj.comments = body.comments
    obj.shares = body.shares
    if obj.impressions > 0:
        obj.engagement_rate = round((obj.likes + obj.comments + obj.shares) / obj.impressions, 4)
    obj.metrics_updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(obj)
    return ArticleResponse.model_validate(obj)
