"""
api/routes/content/images.py

Endpoints da galeria de imagens do Content Hub:
  GET  /content/images           — lista imagens com filtros e paginacao
  POST /content/images/generate  — gera imagem standalone com IA
  POST /content/images/upload    — upload de imagem standalone
  DELETE /content/images/{id}    — remove imagem da galeria
"""

from __future__ import annotations

import io
import uuid

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from api.dependencies import (
    get_effective_tenant_id,
    get_llm_registry,
    get_session_flexible,
    get_session_no_auth,
)
from integrations.llm import LLMRegistry
from integrations.s3_client import S3Client
from models.content_gallery_image import ContentGalleryImage
from models.content_post import ContentPost
from schemas.content import (
    ImageAspectRatio,
    ImageStyle,
    ImageSubType,
    ImageVisualDirection,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/images", tags=["Content Hub Images"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_UPLOAD_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/svg+xml",
}


class GalleryImage(BaseModel):
    """Imagem exibida na galeria."""

    id: uuid.UUID
    linked_post_id: uuid.UUID | None = None
    title: str
    post_status: str | None = None
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
    """Geracao de imagem standalone sem vinculo obrigatorio com post existente."""

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
    image_id: uuid.UUID


class UploadStandaloneImageResponse(BaseModel):
    image_url: str
    filename: str
    size_bytes: int
    image_id: uuid.UUID


def _build_post_filters(tenant_id, source=None, style=None, pillar=None, status=None, search=None):
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


def _should_query_standalone_assets(source=None, pillar=None, status=None) -> bool:
    if pillar is not None or status is not None:
        return False
    return True


def _build_gallery_asset_filters(tenant_id, source=None, style=None, search=None):
    clauses = [
        ContentGalleryImage.tenant_id == tenant_id,
        ContentGalleryImage.image_url.isnot(None),
        ContentGalleryImage.image_url != "",
    ]
    if source:
        clauses.append(ContentGalleryImage.source == source)
    if style:
        clauses.append(ContentGalleryImage.image_style == style)
    if search:
        search_term = f"%{search}%"
        clauses.append(
            or_(
                ContentGalleryImage.title.ilike(search_term),
                ContentGalleryImage.image_prompt.ilike(search_term),
                ContentGalleryImage.image_filename.ilike(search_term),
            )
        )
    return clauses


def _build_gallery_image_title(prompt: str) -> str:
    cleaned = " ".join(prompt.split())
    return cleaned[:255] if cleaned else "Imagem gerada"


@router.get(
    "/{image_id}/file",
    summary="Retorna a imagem standalone da galeria via proxy do S3 privado",
    response_class=StreamingResponse,
    include_in_schema=True,
)
async def get_gallery_image_file(
    image_id: uuid.UUID,
    db: AsyncSession = Depends(get_session_no_auth),
) -> StreamingResponse:
    """Faz proxy da imagem standalone da galeria quando o bucket e privado."""
    result = await db.execute(select(ContentGalleryImage).where(ContentGalleryImage.id == image_id))
    gallery_image = result.scalar_one_or_none()
    if gallery_image is None or not gallery_image.image_s3_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Imagem nao encontrada.")

    try:
        data, content_type = S3Client().get_bytes(gallery_image.image_s3_key)
    except Exception as exc:
        logger.error("content.gallery_image_proxy_error", image_id=str(image_id), error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Erro ao buscar imagem",
        ) from exc

    return StreamingResponse(io.BytesIO(data), media_type=content_type)


@router.get(
    "",
    response_model=GalleryImagesResponse,
    summary="Lista imagens da galeria com filtros e paginacao",
)
async def list_gallery_images(
    page: int = Query(1, ge=1, description="Numero da pagina"),
    page_size: int = Query(24, ge=1, le=100, description="Itens por pagina"),
    source: str | None = Query(None, description="Filtrar por origem: generated | uploaded"),
    style: str | None = Query(
        None, description="Filtrar por estilo: clean | with_text | infographic"
    ),
    pillar: str | None = Query(None, description="Filtrar por pilar do post"),
    status: str | None = Query(None, description="Filtrar por status do post"),
    search: str | None = Query(None, description="Busca em titulo, prompt, nome do arquivo"),
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> GalleryImagesResponse:
    """Retorna imagens da galeria unindo posts reais e assets standalone."""

    post_clauses = _build_post_filters(tenant_id, source, style, pillar, status, search)
    include_standalone_assets = _should_query_standalone_assets(source, pillar, status)
    asset_clauses = (
        _build_gallery_asset_filters(tenant_id, source, style, search)
        if include_standalone_assets
        else None
    )

    post_count_query = select(func.count()).select_from(ContentPost).where(*post_clauses)
    post_total_result = await db.execute(post_count_query)
    post_total = post_total_result.scalar() or 0

    asset_total = 0
    if asset_clauses is not None:
        asset_count_query = (
            select(func.count()).select_from(ContentGalleryImage).where(*asset_clauses)
        )
        asset_total_result = await db.execute(asset_count_query)
        asset_total = asset_total_result.scalar() or 0

    total = post_total + asset_total
    offset = (page - 1) * page_size
    merge_limit = page * page_size

    posts_query = (
        select(ContentPost)
        .where(*post_clauses)
        .order_by(ContentPost.updated_at.desc().nullslast())
        .limit(merge_limit)
    )
    post_result = await db.execute(posts_query)
    posts = post_result.scalars().all()

    gallery_assets: list[ContentGalleryImage] = []
    if asset_clauses is not None:
        assets_query = (
            select(ContentGalleryImage)
            .where(*asset_clauses)
            .order_by(ContentGalleryImage.updated_at.desc().nullslast())
            .limit(merge_limit)
        )
        asset_result = await db.execute(assets_query)
        gallery_assets.extend(asset_result.scalars().all())

    images: list[GalleryImage] = []
    for post in posts:
        source_type = "generated" if post.image_style else "uploaded"
        images.append(
            GalleryImage(
                id=post.id,
                linked_post_id=post.id,
                title=post.title,
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

    for asset in gallery_assets:
        images.append(
            GalleryImage(
                id=asset.id,
                linked_post_id=asset.linked_post_id,
                title=asset.title,
                post_status=None,
                post_pillar=None,
                image_url=asset.image_url,
                image_s3_key=asset.image_s3_key,
                image_style=asset.image_style,
                image_prompt=asset.image_prompt,
                image_aspect_ratio=asset.image_aspect_ratio,
                image_filename=asset.image_filename,
                image_size_bytes=asset.image_size_bytes,
                source=asset.source,
                created_at=asset.created_at.isoformat() if asset.created_at else None,
                updated_at=asset.updated_at.isoformat() if asset.updated_at else None,
            )
        )

    images.sort(key=lambda image: image.updated_at or image.created_at or "", reverse=True)
    images = images[offset : offset + page_size]

    return GalleryImagesResponse(
        images=images,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/generate",
    response_model=GenerateStandaloneImageResponse,
    summary="Gera imagem standalone com IA sem criar post",
)
async def generate_standalone_image(
    body: GenerateStandaloneImageRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
    registry: LLMRegistry = Depends(get_llm_registry),
) -> GenerateStandaloneImageResponse:
    """Gera uma imagem com IA e salva como asset independente da galeria."""
    from services.content import image_generator as image_generator_service

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
            detail=f"Falha na geracao de imagem: {exc}",
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

    gallery_image_id = uuid.uuid4()
    s3_key = f"gallery/images/{tenant_id}/{gallery_image_id}.png"
    s3 = S3Client()
    image_url = s3.upload_bytes(image_bytes, s3_key, "image/png")

    gallery_image = ContentGalleryImage(
        id=gallery_image_id,
        tenant_id=tenant_id,
        title=_build_gallery_image_title(body.prompt),
        source="generated",
        image_url=image_url,
        image_s3_key=s3_key,
        image_style=body.style,
        image_prompt=prompt_used,
        image_aspect_ratio=body.aspect_ratio,
    )
    db.add(gallery_image)

    await db.commit()

    logger.info(
        "content.standalone_image_generated",
        image_id=str(gallery_image.id),
        tenant_id=str(tenant_id),
        style=body.style,
    )

    return GenerateStandaloneImageResponse(
        image_url=image_url,
        image_prompt=prompt_used,
        image_id=gallery_image.id,
    )


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
    """Faz upload de uma imagem para a galeria como asset independente."""
    if file.content_type not in ALLOWED_UPLOAD_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de arquivo nao permitido: {file.content_type}. Use JPEG, PNG, WEBP, GIF ou SVG.",
        )

    image_bytes = await file.read()
    if len(image_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Arquivo excede o limite de {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.",
        )

    filename = file.filename or "upload.png"

    ext_map = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
        "image/svg+xml": ".svg",
    }
    ext = ext_map.get(file.content_type or "", ".png")
    gallery_image_id = uuid.uuid4()
    s3_key = f"gallery/uploads/{tenant_id}/{gallery_image_id}{ext}"
    s3 = S3Client()
    image_url = s3.upload_bytes(image_bytes, s3_key, file.content_type or "image/png")

    gallery_image = ContentGalleryImage(
        id=gallery_image_id,
        tenant_id=tenant_id,
        title=filename,
        source="uploaded",
        image_url=image_url,
        image_s3_key=s3_key,
        image_filename=filename,
        image_size_bytes=len(image_bytes),
    )
    db.add(gallery_image)

    await db.commit()

    logger.info(
        "content.standalone_image_uploaded",
        image_id=str(gallery_image.id),
        tenant_id=str(tenant_id),
        filename=filename,
        size_bytes=len(image_bytes),
    )

    return UploadStandaloneImageResponse(
        image_url=image_url,
        filename=filename,
        size_bytes=len(image_bytes),
        image_id=gallery_image.id,
    )


@router.delete(
    "/{image_id}",
    summary="Remove uma imagem da galeria",
)
async def delete_gallery_image(
    image_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
):
    """Remove uma imagem da galeria, seja asset standalone ou imagem de post."""
    result = await db.execute(
        select(ContentPost).where(
            ContentPost.id == image_id,
            ContentPost.tenant_id == tenant_id,
        )
    )
    post = result.scalar_one_or_none()
    if post is not None:
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
            image_id=str(image_id),
            tenant_id=str(tenant_id),
            item_type="post",
        )
        return {"ok": True}

    asset_result = await db.execute(
        select(ContentGalleryImage).where(
            ContentGalleryImage.id == image_id,
            ContentGalleryImage.tenant_id == tenant_id,
        )
    )
    gallery_image = asset_result.scalar_one_or_none()
    if gallery_image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Imagem nao encontrada.")

    if gallery_image.image_s3_key:
        try:
            S3Client().delete_object(gallery_image.image_s3_key)
        except Exception as exc:
            logger.warning(
                "gallery.delete_s3_failed",
                s3_key=gallery_image.image_s3_key,
                error=str(exc),
            )

    await db.delete(gallery_image)
    await db.commit()

    logger.info(
        "content.gallery_image_deleted",
        image_id=str(image_id),
        tenant_id=str(tenant_id),
        item_type="standalone",
    )
    return {"ok": True}
