"""
api/routes/content/images.py

Endpoints da galeria de imagens do Content Hub:
  GET  /content/images           — lista imagens com filtros e paginação
  POST /content/images/generate  — gera imagem standalone com IA
  POST /content/images/upload    — upload de imagem standalone
  DELETE /content/images/{id}    — deleta imagem de um post
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import (
    get_effective_tenant_id,
    get_llm_registry,
    get_session_flexible,
)
from integrations.llm import LLMRegistry
from integrations.s3_client import S3Client
from models.content_post import ContentPost
from schemas.content import (
    ImageAspectRatio,
    ImageStyle,
    ImageSubType,
    ImageVisualDirection,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/images", tags=["Content Hub Images"])

# Tamanho máximo de upload: 10 MB
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_UPLOAD_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/svg+xml",
}


# ── Schemas ──────────────────────────────────────────────────────────


class GalleryImage(BaseModel):
    """Imagem exibida na galeria."""

    post_id: uuid.UUID
    post_title: str
    post_status: str
    post_pillar: str | None
    image_url: str | None
    image_s3_key: str | None
    image_style: str | None
    image_prompt: str | None
    image_aspect_ratio: str | None
    image_filename: str | None
    image_size_bytes: int | None
    source: str  # "generated" | "uploaded"
    created_at: str | None
    updated_at: str | None

    model_config = {"from_attributes": True}


class GalleryImagesResponse(BaseModel):
    images: list[GalleryImage]
    total: int
    page: int
    page_size: int


class GenerateStandaloneImageRequest(BaseModel):
    """Geração de imagem standalone — sem vínculo obrigatório com post existente."""

    prompt: str = Field(
        ..., min_length=3, max_length=2000, description="Prompt descritivo para a imagem"
    )
    style: ImageStyle = "clean"
    aspect_ratio: ImageAspectRatio = "4:5"
    sub_type: ImageSubType | None = None
    visual_direction: ImageVisualDirection = "auto"


class GenerateStandaloneImageResponse(BaseModel):
    image_url: str
    image_prompt: str
    post_id: uuid.UUID | None = None


class UploadStandaloneImageResponse(BaseModel):
    image_url: str
    filename: str
    size_bytes: int
    post_id: uuid.UUID


# ── Helpers ──────────────────────────────────────────────────────────


def _build_base_filters(tenant_id, source=None, style=None, pillar=None, status=None, search=None):
    """Build WHERE clauses as a list for reuse in count and list queries."""
    clauses = [
        ContentPost.tenant_id == tenant_id,
        ContentPost.image_url.isnot(None),
        ContentPost.image_url != "",
    ]
    if source == "generated":
        clauses.append(ContentPost.image_style.isnot(None))
        clauses.append(ContentPost.image_filename.is_(None))
    elif source == "uploaded":
        clauses.append(ContentPost.image_filename.isnot(None))
    if style:
        clauses.append(ContentPost.image_style == style)
    if pillar:
        clauses.append(ContentPost.pillar == pillar)
    if status:
        clauses.append(ContentPost.status == status)
    if search:
        search_term = f"%{search}%"
        clauses.append(
            or_(
                ContentPost.title.ilike(search_term),
                ContentPost.image_prompt.ilike(search_term),
                ContentPost.image_filename.ilike(search_term),
            )
        )
    return clauses


# ── GET /images ──────────────────────────────────────────────────────


@router.get(
    "",
    response_model=GalleryImagesResponse,
    summary="Lista imagens da galeria com filtros e paginação",
)
async def list_gallery_images(
    page: int = Query(1, ge=1, description="Número da página"),
    page_size: int = Query(24, ge=1, le=100, description="Itens por página"),
    source: str | None = Query(None, description="Filtrar por origem: generated | uploaded"),
    style: str | None = Query(
        None, description="Filtrar por estilo: clean | with_text | infographic"
    ),
    pillar: str | None = Query(None, description="Filtrar por pilar do post"),
    status: str | None = Query(None, description="Filtrar por status do post"),
    search: str | None = Query(None, description="Busca em título, prompt, nome do arquivo"),
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> GalleryImagesResponse:
    """Retorna posts que possuem imagem (gerada ou upload), com paginação e filtros."""

    clauses = _build_base_filters(tenant_id, source, style, pillar, status, search)

    # Count query
    count_query = select(func.count()).select_from(ContentPost).where(*clauses)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # List query with pagination
    list_query = (
        select(ContentPost)
        .where(*clauses)
        .order_by(ContentPost.updated_at.desc().nullslast())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(list_query)
    posts = result.scalars().all()

    images: list[GalleryImage] = []
    for post in posts:
        source_type = "generated" if post.image_style else "uploaded"
        images.append(
            GalleryImage(
                post_id=post.id,
                post_title=post.title,
                post_status=post.status,
                post_pillar=post.pillar,
                image_url=post.image_url,
                image_s3_key=post.image_s3_key,
                image_style=post.image_style,
                image_prompt=post.image_prompt,
                image_aspect_ratio=post.image_aspect_ratio,
                image_filename=post.image_filename,
                image_size_bytes=post.image_size_bytes,
                source=source_type,
                created_at=post.created_at.isoformat() if post.created_at else None,
                updated_at=post.updated_at.isoformat() if post.updated_at else None,
            )
        )

    return GalleryImagesResponse(
        images=images,
        total=total,
        page=page,
        page_size=page_size,
    )


# ── POST /images/generate ────────────────────────────────────────────


@router.post(
    "/generate",
    response_model=GenerateStandaloneImageResponse,
    summary="Gera imagem standalone com IA (sem exigir post existente)",
)
async def generate_standalone_image(
    body: GenerateStandaloneImageRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
    registry: LLMRegistry = Depends(get_llm_registry),
) -> GenerateStandaloneImageResponse:
    """Gera uma imagem com IA usando um prompt customizado. Cria post draft automaticamente."""
    from services.content import image_generator as image_generator_service

    draft_post = ContentPost(
        tenant_id=tenant_id,
        title="[Imagem Gerada] " + body.prompt[:80],
        body="Imagem gerada por IA — aguardando vínculo com post.",
        pillar="authority",
        status="draft",
        character_count=0,
    )
    db.add(draft_post)
    await db.flush()

    try:
        image_bytes, prompt_used = await image_generator_service.generate_standalone_image(
            prompt=body.prompt,
            style=body.style,
            registry=registry,
            aspect_ratio=body.aspect_ratio,
            sub_type=body.sub_type,
            visual_direction=body.visual_direction,
        )
    except ValueError as exc:
        logger.warning("content.standalone_image_generation_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Falha na geração de imagem: {exc}",
        ) from exc
    except Exception as exc:
        exc_str = str(exc)
        logger.error("content.standalone_image_generation_error", error=exc_str)
        if "429" in exc_str or "RESOURCE_EXHAUSTED" in exc_str:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Cota da API Gemini esgotada. Verifique seu plano e billing em ai.google.dev.",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro ao gerar imagem: {exc}",
        ) from exc

    s3_key = f"images/{tenant_id}/{draft_post.id}.png"
    s3 = S3Client()
    image_url = s3.upload_bytes(image_bytes, s3_key, "image/png")

    draft_post.image_url = image_url
    draft_post.image_s3_key = s3_key
    draft_post.image_style = body.style
    draft_post.image_prompt = prompt_used
    draft_post.image_aspect_ratio = body.aspect_ratio

    await db.commit()

    logger.info(
        "content.standalone_image_generated",
        post_id=str(draft_post.id),
        tenant_id=str(tenant_id),
        style=body.style,
    )

    return GenerateStandaloneImageResponse(
        image_url=image_url,
        image_prompt=prompt_used,
        post_id=draft_post.id,
    )


# ── POST /images/upload ──────────────────────────────────────────────


@router.post(
    "/upload",
    response_model=UploadStandaloneImageResponse,
    summary="Upload de imagem standalone para a galeria",
)
async def upload_standalone_image(
    file: UploadFile = File(...),
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> UploadStandaloneImageResponse:
    """Faz upload de uma imagem para a galeria. Cria post draft automaticamente."""
    if file.content_type not in ALLOWED_UPLOAD_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de arquivo não permitido: {file.content_type}. Use JPEG, PNG, WEBP, GIF ou SVG.",
        )

    image_bytes = await file.read()
    if len(image_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Arquivo excede o limite de {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.",
        )

    filename = file.filename or "upload.png"

    draft_post = ContentPost(
        tenant_id=tenant_id,
        title=f"[Upload] {filename}",
        body="Imagem enviada via upload — aguardando vínculo com post.",
        pillar="authority",
        status="draft",
        character_count=0,
    )
    db.add(draft_post)
    await db.flush()

    ext_map = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
        "image/svg+xml": ".svg",
    }
    ext = ext_map.get(file.content_type or "", ".png")
    s3_key = f"images/{tenant_id}/{draft_post.id}{ext}"
    s3 = S3Client()
    image_url = s3.upload_bytes(image_bytes, s3_key, file.content_type or "image/png")

    draft_post.image_url = image_url
    draft_post.image_s3_key = s3_key
    draft_post.image_filename = filename
    draft_post.image_size_bytes = len(image_bytes)

    await db.commit()

    logger.info(
        "content.standalone_image_uploaded",
        post_id=str(draft_post.id),
        tenant_id=str(tenant_id),
        filename=filename,
        size_bytes=len(image_bytes),
    )

    return UploadStandaloneImageResponse(
        image_url=image_url,
        filename=filename,
        size_bytes=len(image_bytes),
        post_id=draft_post.id,
    )


# ── DELETE /images/{post_id} ─────────────────────────────────────────


@router.delete(
    "/{post_id}",
    summary="Remove a imagem de um post (galeria)",
)
async def delete_gallery_image(
    post_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
):
    """Remove a imagem (S3 + campos) de um post específico."""
    result = await db.execute(
        select(ContentPost).where(
            ContentPost.id == post_id,
            ContentPost.tenant_id == tenant_id,
        )
    )
    post = result.scalar_one_or_none()
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post não encontrado.")

    if post.status in {"scheduled", "published"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Nao e possivel excluir a imagem de posts agendados ou publicados. Altere o status do post antes de remover a imagem.",
        )

    if post.image_s3_key:
        try:
            S3Client().delete_object(post.image_s3_key)
        except Exception as exc:
            logger.warning("gallery.delete_s3_failed", s3_key=post.image_s3_key, error=str(exc))

    post.image_url = None
    post.image_s3_key = None
    post.image_style = None
    post.image_prompt = None
    post.image_aspect_ratio = None
    post.image_filename = None
    post.image_size_bytes = None
    post.linkedin_image_urn = None

    await db.commit()

    logger.info(
        "content.gallery_image_deleted",
        post_id=str(post_id),
        tenant_id=str(tenant_id),
    )

    return {"ok": True}
