"""
api/routes/content/newsletters.py

Endpoints da Newsletter "Operacao Inteligente".

GET    /content/newsletters                         lista (filtros)
POST   /content/newsletters                         cria draft
GET    /content/newsletters/banks                   bancos para dropdowns
GET    /content/newsletters/{id}                    busca
PUT    /content/newsletters/{id}                    atualiza
DELETE /content/newsletters/{id}                    soft delete
POST   /content/newsletters/{id}/restore            restaura soft-deleted
POST   /content/newsletters/{id}/generate-draft     LLM completo
POST   /content/newsletters/{id}/improve-section    reescreve secao
POST   /content/newsletters/{id}/upload-cover       upload da capa
DELETE /content/newsletters/{id}/cover              remove capa
POST   /content/newsletters/{id}/schedule           define lembrete
DELETE /content/newsletters/{id}/schedule           cancela lembrete
POST   /content/newsletters/{id}/mark-published     publicado manualmente no Pulse
GET    /content/newsletters/{id}/export             markdown/html para clipboard
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import (
    get_effective_tenant_id,
    get_llm_registry,
    get_session_flexible,
)
from core.file_security import detect_image_content_type, pick_image_extension
from integrations.llm import LLMRegistry
from models.content_article import ContentArticle
from models.content_newsletter import ContentNewsletter
from schemas.content_newsletter import (
    NewsletterCreate,
    NewsletterExportFormat,
    NewsletterGenerateCoverRequest,
    NewsletterGenerateDraftRequest,
    NewsletterImproveSectionRequest,
    NewsletterMarkPublishedRequest,
    NewsletterResponse,
    NewsletterScheduleRequest,
    NewsletterUpdate,
)
from services.content.newsletter_llm_generator import (
    generate_newsletter_draft,
    get_banks_payload,
    improve_newsletter_section,
)
from services.content.newsletter_renderer import render_to_html, render_to_markdown

logger = structlog.get_logger()

router = APIRouter(prefix="/newsletters", tags=["Content Hub — Newsletters"])


# ── Helpers ───────────────────────────────────────────────────────────


async def _get_or_404(nid: uuid.UUID, tenant_id: uuid.UUID, db: AsyncSession) -> ContentNewsletter:
    result = await db.execute(
        select(ContentNewsletter).where(
            ContentNewsletter.id == nid,
            ContentNewsletter.tenant_id == tenant_id,
        )
    )
    obj = result.scalar_one_or_none()
    if obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Newsletter nao encontrada"
        )
    return obj


async def _next_edition_number(db: AsyncSession, tenant_id: uuid.UUID) -> int:
    """
    Atomico via SELECT MAX(edition_number) + 1.
    Em caso de conflito unique, o caller deve tratar.
    """
    result = await db.execute(
        select(func.coalesce(func.max(ContentNewsletter.edition_number), 0)).where(
            ContentNewsletter.tenant_id == tenant_id,
            ContentNewsletter.deleted_at.is_(None),
        )
    )
    current = result.scalar_one()
    return int(current) + 1


# ── Banks (dropdowns) ────────────────────────────────────────────────


@router.get("/banks")
async def get_banks() -> dict[str, Any]:
    """Bancos de referencia para popular dropdowns no frontend."""
    return get_banks_payload()


# ── List / Get / Create / Update / Delete / Restore ──────────────────


@router.get("", response_model=list[NewsletterResponse])
async def list_newsletters(
    nl_status: str | None = Query(default=None, alias="status"),
    include_deleted: bool = Query(default=False),
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> list[NewsletterResponse]:
    stmt = select(ContentNewsletter).where(ContentNewsletter.tenant_id == tenant_id)
    if not include_deleted:
        stmt = stmt.where(ContentNewsletter.deleted_at.is_(None))
    if nl_status:
        stmt = stmt.where(ContentNewsletter.status == nl_status)
    stmt = stmt.order_by(ContentNewsletter.edition_number.desc())
    result = await db.execute(stmt)
    return [NewsletterResponse.model_validate(n) for n in result.scalars().all()]


@router.post("", response_model=NewsletterResponse, status_code=status.HTTP_201_CREATED)
async def create_newsletter(
    body: NewsletterCreate,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> NewsletterResponse:
    edition_number = await _next_edition_number(db, tenant_id)
    obj = ContentNewsletter(
        tenant_id=tenant_id,
        edition_number=edition_number,
        title=body.title or f"Edição #{edition_number}",
        subtitle=body.subtitle,
        body_markdown=body.body_markdown,
        body_html=body.body_html,
        sections_payload=body.sections_payload,
        cover_image_url=body.cover_image_url,
        cover_image_s3_key=body.cover_image_s3_key,
        scheduled_for=body.scheduled_for,
        notion_page_id=body.notion_page_id,
        status="draft",
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    logger.info(
        "content.newsletter_created",
        newsletter_id=str(obj.id),
        edition=edition_number,
        tenant_id=str(tenant_id),
    )
    return NewsletterResponse.model_validate(obj)


@router.get("/{nid}", response_model=NewsletterResponse)
async def get_newsletter(
    nid: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> NewsletterResponse:
    obj = await _get_or_404(nid, tenant_id, db)
    return NewsletterResponse.model_validate(obj)


@router.put("/{nid}", response_model=NewsletterResponse)
async def update_newsletter(
    nid: uuid.UUID,
    body: NewsletterUpdate,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> NewsletterResponse:
    obj = await _get_or_404(nid, tenant_id, db)
    if obj.deleted_at is not None:
        raise HTTPException(status_code=409, detail="Newsletter foi deletada")

    data = body.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(obj, key, value)
    await db.commit()
    await db.refresh(obj)
    return NewsletterResponse.model_validate(obj)


@router.delete("/{nid}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_newsletter(
    nid: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> None:
    obj = await _get_or_404(nid, tenant_id, db)
    if obj.deleted_at is None:
        obj.deleted_at = datetime.now(UTC)
        obj.status = "deleted"
        await db.commit()
    logger.info("content.newsletter_deleted", newsletter_id=str(nid), tenant_id=str(tenant_id))


@router.post("/{nid}/restore", response_model=NewsletterResponse)
async def restore_newsletter(
    nid: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> NewsletterResponse:
    obj = await _get_or_404(nid, tenant_id, db)
    if obj.deleted_at is None:
        return NewsletterResponse.model_validate(obj)
    obj.deleted_at = None
    obj.status = "draft"
    await db.commit()
    await db.refresh(obj)
    return NewsletterResponse.model_validate(obj)


# ── LLM ───────────────────────────────────────────────────────────────


@router.post("/{nid}/generate-draft", response_model=NewsletterResponse)
async def generate_draft(
    nid: uuid.UUID,
    body: NewsletterGenerateDraftRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
    registry: LLMRegistry = Depends(get_llm_registry),
) -> NewsletterResponse:
    obj = await _get_or_404(nid, tenant_id, db)

    payload = await generate_newsletter_draft(
        edition_number=obj.edition_number,
        theme_central=body.theme_central,
        vision_topic=body.vision_topic,
        tutorial_topic=body.tutorial_topic,
        radar_tool=body.radar_tool,
        radar_data=body.radar_data,
        registry=registry,
        tenant_id=str(tenant_id),
        provider=body.provider,
        model=body.model,
        temperature=body.temperature,
        max_tokens=body.max_tokens,
    )

    obj.sections_payload = payload
    if title := payload.get("title"):
        obj.title = str(title)[:300]
    if subtitle := payload.get("subtitle"):
        obj.subtitle = str(subtitle)[:300]
    obj.body_markdown = render_to_markdown(
        payload, edition_number=obj.edition_number, publish_date=obj.scheduled_for
    )
    obj.body_html = render_to_html(
        payload, edition_number=obj.edition_number, publish_date=obj.scheduled_for
    )
    await db.commit()
    await db.refresh(obj)
    logger.info(
        "content.newsletter_draft_generated",
        newsletter_id=str(nid),
        violations=len(payload.get("violations") or []),
    )
    return NewsletterResponse.model_validate(obj)


@router.post("/{nid}/improve-section", response_model=NewsletterResponse)
async def improve_section(
    nid: uuid.UUID,
    body: NewsletterImproveSectionRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
    registry: LLMRegistry = Depends(get_llm_registry),
) -> NewsletterResponse:
    obj = await _get_or_404(nid, tenant_id, db)
    payload = dict(obj.sections_payload or {})
    section_key = f"section_{body.section_id}"
    current_section = payload.get(section_key) or {}

    new_section = await improve_newsletter_section(
        section_id=body.section_id,
        current_payload=current_section if isinstance(current_section, dict) else {},
        instruction=body.instruction,
        registry=registry,
        tenant_id=str(tenant_id),
        provider=body.provider,
        model=body.model,
        temperature=body.temperature,
    )

    payload[section_key] = new_section
    obj.sections_payload = payload
    obj.body_markdown = render_to_markdown(
        payload, edition_number=obj.edition_number, publish_date=obj.scheduled_for
    )
    obj.body_html = render_to_html(
        payload, edition_number=obj.edition_number, publish_date=obj.scheduled_for
    )
    await db.commit()
    await db.refresh(obj)
    return NewsletterResponse.model_validate(obj)


# ── Cover image ───────────────────────────────────────────────────────

_MAX_IMAGE_SIZE = 10 * 1024 * 1024
_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


@router.post("/{nid}/upload-cover", response_model=NewsletterResponse)
async def upload_cover(
    nid: uuid.UUID,
    file: UploadFile = File(...),
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> NewsletterResponse:
    from integrations.s3_client import S3Client

    obj = await _get_or_404(nid, tenant_id, db)

    if file.content_type not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=415, detail=f"Tipo nao suportado: {file.content_type}")
    payload = await file.read()
    if len(payload) > _MAX_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail="Imagem maior que 10MB")

    detected_content_type = detect_image_content_type(payload)
    if detected_content_type is None or detected_content_type not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=422,
            detail="Conteudo do arquivo nao corresponde a uma imagem suportada.",
        )

    if detected_content_type != file.content_type:
        raise HTTPException(
            status_code=422,
            detail=(
                "Conteudo do arquivo nao corresponde ao content_type enviado. "
                f"Detectado: {detected_content_type}; recebido: {file.content_type}."
            ),
        )

    s3 = S3Client()
    ext = pick_image_extension(
        content_type=detected_content_type,
        original_filename=file.filename or "cover.jpg",
    )
    key = f"newsletters/{tenant_id}/{nid}/cover-{uuid.uuid4().hex}{ext}"
    url = s3.upload_bytes(payload, key, content_type=detected_content_type)

    if obj.cover_image_s3_key:
        try:
            s3.delete_object(obj.cover_image_s3_key)
        except Exception:
            pass

    obj.cover_image_url = url
    obj.cover_image_s3_key = key
    await db.commit()
    await db.refresh(obj)
    return NewsletterResponse.model_validate(obj)


@router.post("/{nid}/generate-cover", response_model=NewsletterResponse)
async def generate_cover_with_ai(
    nid: uuid.UUID,
    body: NewsletterGenerateCoverRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
    registry: LLMRegistry = Depends(get_llm_registry),
) -> NewsletterResponse:
    """
    Gera a capa da newsletter via Gemini Nano Banana 2 e persiste em S3.
    """
    from integrations.s3_client import S3Client
    from services.content import image_generator as image_generator_service

    obj = await _get_or_404(nid, tenant_id, db)

    base_prompt = (body.prompt or "").strip()
    if not base_prompt:
        # Fallback: título + tema central inferidos do payload
        title = obj.title or f"Newsletter Operação Inteligente — Edição #{obj.edition_number}"
        tema = ""
        if isinstance(obj.sections_payload, dict):
            tema_section = obj.sections_payload.get("section_tema_quinzena") or {}
            if isinstance(tema_section, dict):
                tema = str(tema_section.get("heading") or tema_section.get("body") or "")[:200]
        base_prompt = f"{title}. {tema}".strip(". ").strip()

    try:
        image_bytes, prompt_used = await image_generator_service.generate_standalone_image(
            prompt=base_prompt,
            style=body.style,
            registry=registry,
            aspect_ratio=body.aspect_ratio,
            visual_direction=body.visual_direction,
            image_size=body.image_size,
        )
    except ValueError as exc:
        logger.warning("content.newsletter_cover_generation_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Falha na geração da capa: {exc}",
        ) from exc
    except Exception as exc:
        exc_str = str(exc)
        logger.error("content.newsletter_cover_generation_error", error=exc_str)
        if "429" in exc_str or "RESOURCE_EXHAUSTED" in exc_str:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Cota da API Gemini esgotada.",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro ao gerar capa: {exc}",
        ) from exc

    s3 = S3Client()
    key = f"newsletters/{tenant_id}/{nid}/cover-ai-{uuid.uuid4().hex}.png"
    url = s3.upload_bytes(image_bytes, key, content_type="image/png")

    if obj.cover_image_s3_key:
        try:
            s3.delete_object(obj.cover_image_s3_key)
        except Exception:
            pass

    obj.cover_image_url = url
    obj.cover_image_s3_key = key
    await db.commit()
    await db.refresh(obj)

    logger.info(
        "content.newsletter_cover_ai_generated",
        newsletter_id=str(nid),
        tenant_id=str(tenant_id),
        prompt_chars=len(prompt_used),
    )
    return NewsletterResponse.model_validate(obj)


@router.delete("/{nid}/cover", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_cover(
    nid: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> None:
    from integrations.s3_client import S3Client

    obj = await _get_or_404(nid, tenant_id, db)
    if obj.cover_image_s3_key:
        try:
            S3Client().delete_object(obj.cover_image_s3_key)
        except Exception:
            pass
    obj.cover_image_url = None
    obj.cover_image_s3_key = None
    await db.commit()


# ── Schedule (lembrete apenas — newsletter sempre publicada manual) ──


@router.post("/{nid}/schedule", response_model=NewsletterResponse)
async def schedule_newsletter(
    nid: uuid.UUID,
    body: NewsletterScheduleRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> NewsletterResponse:
    obj = await _get_or_404(nid, tenant_id, db)
    if obj.deleted_at is not None:
        raise HTTPException(status_code=409, detail="Newsletter foi deletada")
    obj.scheduled_for = body.scheduled_for
    obj.status = "scheduled"
    obj.last_reminder_sent_at = None
    await db.commit()
    await db.refresh(obj)
    return NewsletterResponse.model_validate(obj)


@router.delete("/{nid}/schedule", response_model=NewsletterResponse)
async def cancel_schedule(
    nid: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> NewsletterResponse:
    obj = await _get_or_404(nid, tenant_id, db)
    if obj.status != "scheduled":
        raise HTTPException(status_code=409, detail="Newsletter nao esta agendada")
    obj.scheduled_for = None
    obj.status = "approved" if obj.body_markdown else "draft"
    await db.commit()
    await db.refresh(obj)
    return NewsletterResponse.model_validate(obj)


# ── Mark published (manual) — cria ContentArticle derivado ──────────


@router.post("/{nid}/mark-published", response_model=NewsletterResponse)
async def mark_published(
    nid: uuid.UUID,
    body: NewsletterMarkPublishedRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> NewsletterResponse:
    obj = await _get_or_404(nid, tenant_id, db)
    obj.status = "published"
    obj.linkedin_pulse_url = body.linkedin_pulse_url
    obj.published_at = datetime.now(UTC)

    if body.create_derived_article and obj.derived_article_id is None:
        article = ContentArticle(
            tenant_id=tenant_id,
            source_url=body.linkedin_pulse_url,
            title=obj.title,
            description=obj.subtitle,
            commentary=None,
            status="draft",
            source_newsletter_id=obj.id,
            auto_scraped=False,
        )
        db.add(article)
        await db.flush()
        obj.derived_article_id = article.id

    await db.commit()
    await db.refresh(obj)
    logger.info(
        "content.newsletter_marked_published",
        newsletter_id=str(nid),
        derived_article_id=str(obj.derived_article_id) if obj.derived_article_id else None,
    )
    return NewsletterResponse.model_validate(obj)


# ── Export ──────────────────────────────────────────────────────────


@router.get("/{nid}/export", response_model=NewsletterExportFormat)
async def export_newsletter(
    nid: uuid.UUID,
    fmt: str = Query(default="markdown", alias="format"),
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> NewsletterExportFormat:
    obj = await _get_or_404(nid, tenant_id, db)
    if fmt not in ("markdown", "html"):
        raise HTTPException(status_code=400, detail="format deve ser markdown ou html")
    payload = obj.sections_payload or {}
    if fmt == "markdown":
        content = render_to_markdown(
            payload, edition_number=obj.edition_number, publish_date=obj.scheduled_for
        )
    else:
        content = render_to_html(
            payload, edition_number=obj.edition_number, publish_date=obj.scheduled_for
        )
    return NewsletterExportFormat(format=fmt, content=content)  # type: ignore[arg-type]
