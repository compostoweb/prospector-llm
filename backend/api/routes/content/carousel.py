"""
api/routes/content/carousel.py

Endpoints para gerenciamento de carrosseis multi-imagem em posts.

POST   /posts/{post_id}/carousel/images               — upload de nova imagem
POST   /posts/{post_id}/carousel/images/from-gallery  — importa imagens existentes da galeria
DELETE /posts/{post_id}/carousel/images/{image_id}    — remove imagem do carrossel
PATCH  /posts/{post_id}/carousel/reorder              — reordena (body: {order: [image_id]})

Limites:
- Carrossel suporta 2 a 9 imagens (limite do LinkedIn)
- Imagens nao publicadas ficam com `linkedin_image_urn=NULL` ate publish_now
- Cada carrossel tem `carousel_group_id` UUID compartilhado entre suas imagens
  (usado para agrupamento visual na galeria, independente de `linked_post_id`)
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.dependencies import get_effective_tenant_id, get_session_flexible
from core.file_security import detect_image_content_type, pick_image_extension, sanitize_download_filename
from integrations.s3_client import S3Client
from models.content_gallery_image import ContentGalleryImage
from models.content_post import ContentPost
from schemas.content import (
    CarouselImageItem,
    CarouselImportFromGalleryRequest,
    CarouselReorderRequest,
    ContentPostResponse,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/posts", tags=["Content Hub — Carousel"])

_MAX_CAROUSEL_IMAGES = 9
_MIN_CAROUSEL_IMAGES_TO_PUBLISH = 2
_MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB
_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────


async def _get_post_with_carousel(
    post_id: uuid.UUID, tenant_id: uuid.UUID, db: AsyncSession
) -> ContentPost:
    result = await db.execute(
        select(ContentPost)
        .options(selectinload(ContentPost.carousel_images))
        .where(ContentPost.id == post_id, ContentPost.tenant_id == tenant_id)
    )
    post = result.scalar_one_or_none()
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post não encontrado")
    return post


async def _next_position(post_id: uuid.UUID, db: AsyncSession) -> int:
    result = await db.execute(
        select(ContentGalleryImage.position)
        .where(
            ContentGalleryImage.linked_post_id == post_id,
            ContentGalleryImage.position.isnot(None),
        )
        .order_by(ContentGalleryImage.position.desc())
        .limit(1)
    )
    last = result.scalar_one_or_none()
    return (last + 1) if last is not None else 0


async def _resolve_or_create_group_id(
    post_id: uuid.UUID, db: AsyncSession
) -> uuid.UUID:
    """Reaproveita o carousel_group_id existente do post; cria novo se ainda não houver."""
    result = await db.execute(
        select(ContentGalleryImage.carousel_group_id)
        .where(
            ContentGalleryImage.linked_post_id == post_id,
            ContentGalleryImage.carousel_group_id.isnot(None),
        )
        .limit(1)
    )
    existing = result.scalar_one_or_none()
    return existing if existing else uuid.uuid4()


async def _recompact_positions(post_id: uuid.UUID, db: AsyncSession) -> None:
    """Renumera posições começando em 0, mantendo ordem atual."""
    result = await db.execute(
        select(ContentGalleryImage)
        .where(
            ContentGalleryImage.linked_post_id == post_id,
            ContentGalleryImage.position.isnot(None),
        )
        .order_by(ContentGalleryImage.position.asc())
    )
    items = list(result.scalars().all())
    for new_pos, item in enumerate(items):
        if item.position != new_pos:
            item.position = new_pos


async def _carousel_response(
    post: ContentPost, db: AsyncSession
) -> list[CarouselImageItem]:
    """Recarrega as imagens do carrossel ordenadas e devolve schema."""
    result = await db.execute(
        select(ContentGalleryImage)
        .where(
            ContentGalleryImage.linked_post_id == post.id,
            ContentGalleryImage.position.isnot(None),
        )
        .order_by(ContentGalleryImage.position.asc())
    )
    return [CarouselImageItem.model_validate(img) for img in result.scalars().all()]


# ─────────────────────────────────────────────────────────────────────
# Upload de nova imagem
# ─────────────────────────────────────────────────────────────────────


@router.post(
    "/{post_id}/carousel/images",
    response_model=list[CarouselImageItem],
    status_code=status.HTTP_201_CREATED,
    summary="Faz upload de uma imagem e adiciona ao final do carrossel do post",
)
async def add_carousel_image(
    post_id: uuid.UUID,
    file: UploadFile = File(...),
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> list[CarouselImageItem]:
    if file.content_type not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Formato inválido. Aceitos: JPEG, PNG, WEBP, GIF.",
        )

    post = await _get_post_with_carousel(post_id, tenant_id, db)

    if len(post.carousel_images) >= _MAX_CAROUSEL_IMAGES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Carrossel já possui {_MAX_CAROUSEL_IMAGES} imagens (limite do LinkedIn).",
        )

    image_bytes = await file.read()
    if len(image_bytes) > _MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Imagem excede o limite de 10 MB.",
        )

    detected_content_type = detect_image_content_type(image_bytes)
    if detected_content_type is None or detected_content_type not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Conteudo do arquivo nao corresponde a uma imagem suportada.",
        )

    if detected_content_type != file.content_type:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Conteudo do arquivo nao corresponde ao content_type enviado. "
                f"Detectado: {detected_content_type}; recebido: {file.content_type}."
            ),
        )

    position = await _next_position(post_id, db)
    group_id = await _resolve_or_create_group_id(post_id, db)

    original_name = sanitize_download_filename(
        file.filename or f"carousel-{position}.jpg",
        fallback=f"carousel-{position}.jpg",
    )
    ext = pick_image_extension(
        content_type=detected_content_type,
        original_filename=original_name,
    )
    new_image_id = uuid.uuid4()
    s3_key = f"images/{tenant_id}/carousel/{post_id}/{new_image_id}{ext}"

    image_url = S3Client().upload_bytes(
        image_bytes, s3_key, detected_content_type
    )

    item = ContentGalleryImage(
        id=new_image_id,
        tenant_id=tenant_id,
        linked_post_id=post_id,
        title=post.title,
        image_url=image_url,
        image_s3_key=s3_key,
        image_filename=original_name,
        image_size_bytes=len(image_bytes),
        source="uploaded",
        position=position,
        carousel_group_id=group_id,
        # Invalida URN antigo: se trocou imagem, precisa reupload no LinkedIn
        linkedin_image_urn=None,
    )
    db.add(item)

    # Atualiza media_kind do post se necessário
    if post.media_kind != "carousel":
        post.media_kind = "carousel"

    await db.commit()

    logger.info(
        "content.carousel.image_added",
        post_id=str(post_id),
        image_id=str(new_image_id),
        position=position,
        tenant_id=str(tenant_id),
    )
    return await _carousel_response(post, db)


# ─────────────────────────────────────────────────────────────────────
# Importar imagens existentes da galeria
# ─────────────────────────────────────────────────────────────────────


@router.post(
    "/{post_id}/carousel/images/from-gallery",
    response_model=list[CarouselImageItem],
    status_code=status.HTTP_200_OK,
    summary="Vincula imagens da galeria ao carrossel do post",
)
async def import_carousel_images_from_gallery(
    post_id: uuid.UUID,
    body: CarouselImportFromGalleryRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> list[CarouselImageItem]:
    post = await _get_post_with_carousel(post_id, tenant_id, db)

    available_slots = _MAX_CAROUSEL_IMAGES - len(post.carousel_images)
    if available_slots <= 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Carrossel já possui {_MAX_CAROUSEL_IMAGES} imagens (limite do LinkedIn).",
        )
    if len(body.image_ids) > available_slots:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Tentativa de adicionar {len(body.image_ids)} imagens, "
                f"mas há apenas {available_slots} slots disponíveis."
            ),
        )

    # Carrega imagens solicitadas (apenas as do mesmo tenant)
    result = await db.execute(
        select(ContentGalleryImage).where(
            ContentGalleryImage.id.in_(body.image_ids),
            ContentGalleryImage.tenant_id == tenant_id,
        )
    )
    found_images = list(result.scalars().all())
    if len(found_images) != len(body.image_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Uma ou mais imagens não foram encontradas no tenant atual.",
        )

    # Valida que nenhuma já pertence a outro carrossel ativo
    for img in found_images:
        if img.position is not None and img.linked_post_id and img.linked_post_id != post_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Imagem {img.id} já pertence a outro carrossel "
                    f"(post {img.linked_post_id}). Remova-a de lá primeiro."
                ),
            )

    next_pos = await _next_position(post_id, db)
    group_id = await _resolve_or_create_group_id(post_id, db)

    # Mantém a ordem fornecida no body
    id_to_image = {img.id: img for img in found_images}
    for offset, image_id in enumerate(body.image_ids):
        img = id_to_image[image_id]
        img.linked_post_id = post_id
        img.position = next_pos + offset
        img.carousel_group_id = group_id
        # Imagem trocou de contexto/post — invalida URN cacheado
        img.linkedin_image_urn = None

    if post.media_kind != "carousel":
        post.media_kind = "carousel"

    await db.commit()

    logger.info(
        "content.carousel.images_imported",
        post_id=str(post_id),
        count=len(body.image_ids),
        tenant_id=str(tenant_id),
    )
    return await _carousel_response(post, db)


# ─────────────────────────────────────────────────────────────────────
# Remover imagem do carrossel
# ─────────────────────────────────────────────────────────────────────


@router.delete(
    "/{post_id}/carousel/images/{image_id}",
    response_model=list[CarouselImageItem],
    summary="Remove uma imagem do carrossel e recompacta posições",
)
async def remove_carousel_image(
    post_id: uuid.UUID,
    image_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> list[CarouselImageItem]:
    post = await _get_post_with_carousel(post_id, tenant_id, db)

    result = await db.execute(
        select(ContentGalleryImage).where(
            ContentGalleryImage.id == image_id,
            ContentGalleryImage.linked_post_id == post_id,
            ContentGalleryImage.tenant_id == tenant_id,
        )
    )
    image = result.scalar_one_or_none()
    if image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Imagem não pertence a este carrossel.",
        )

    # Desvincula sem deletar o registro (a imagem permanece na galeria)
    image.linked_post_id = None
    image.position = None
    image.carousel_group_id = None
    image.linkedin_image_urn = None

    await db.flush()
    await _recompact_positions(post_id, db)

    # Se carrossel ficou com 0 imagens, volta media_kind para "none"
    remaining_result = await db.execute(
        select(ContentGalleryImage).where(
            ContentGalleryImage.linked_post_id == post_id,
            ContentGalleryImage.position.isnot(None),
        )
    )
    remaining = list(remaining_result.scalars().all())
    if not remaining:
        post.media_kind = "none"

    await db.commit()

    logger.info(
        "content.carousel.image_removed",
        post_id=str(post_id),
        image_id=str(image_id),
        remaining=len(remaining),
        tenant_id=str(tenant_id),
    )
    return await _carousel_response(post, db)


# ─────────────────────────────────────────────────────────────────────
# Reordenar carrossel
# ─────────────────────────────────────────────────────────────────────


@router.patch(
    "/{post_id}/carousel/reorder",
    response_model=list[CarouselImageItem],
    summary="Reordena as imagens do carrossel",
)
async def reorder_carousel(
    post_id: uuid.UUID,
    body: CarouselReorderRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> list[CarouselImageItem]:
    post = await _get_post_with_carousel(post_id, tenant_id, db)

    current_ids = {img.id for img in post.carousel_images}
    requested_ids = set(body.order)

    if current_ids != requested_ids:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A lista 'order' deve conter exatamente os mesmos IDs do carrossel atual. "
                f"Atual: {sorted(map(str, current_ids))}. "
                f"Recebido: {sorted(map(str, requested_ids))}."
            ),
        )

    id_to_image = {img.id: img for img in post.carousel_images}
    for new_pos, image_id in enumerate(body.order):
        id_to_image[image_id].position = new_pos

    await db.commit()

    logger.info(
        "content.carousel.reordered",
        post_id=str(post_id),
        count=len(body.order),
        tenant_id=str(tenant_id),
    )
    return await _carousel_response(post, db)
