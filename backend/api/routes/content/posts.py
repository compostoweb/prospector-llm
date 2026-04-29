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
from datetime import UTC, datetime

import structlog
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.dependencies import get_effective_tenant_id, get_session_flexible, get_session_no_auth
from models.content_post import ContentPost
from schemas.content import (
    ContentPostCreate,
    ContentPostMetricsUpdate,
    ContentPostResponse,
    ContentPostRevisionResponse,
    ContentPostUpdate,
)
from services.content.linkedin_client import LinkedInClientError
from services.content.publisher import delete_from_linkedin

logger = structlog.get_logger()

router = APIRouter(prefix="/posts", tags=["Content Hub — Posts"])


# ── Helper ────────────────────────────────────────────────────────────


async def _get_post_or_404(
    post_id: uuid.UUID,
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> ContentPost:
    result = await db.execute(
        select(ContentPost)
        .options(selectinload(ContentPost.carousel_images))
        .where(
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
    post_status: str | None = Query(
        default=None,
        alias="status",
        description="draft | approved | scheduled | published | failed",
    ),
    pillar: str | None = Query(default=None, description="authority | case | vision"),
    week_number: int | None = Query(default=None, ge=1, le=54),
    include_deleted: bool = Query(default=False),
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> list[ContentPostResponse]:
    stmt = (
        select(ContentPost)
        .options(selectinload(ContentPost.carousel_images))
        .where(ContentPost.tenant_id == tenant_id)
    )
    if not include_deleted:
        stmt = stmt.where(ContentPost.deleted_at.is_(None))
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
        media_kind=body.media_kind,
        status="draft",
    )
    db.add(post)
    await db.commit()
    await db.refresh(post, attribute_names=["carousel_images"])
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

    was_published = post.status == "published" and post.linkedin_post_urn is not None

    update_data = body.model_dump(exclude_unset=True)
    # Snapshot apenas se algum campo versionado mudou
    versioned = {"title", "body", "hashtags", "pillar", "hook_type", "first_comment_text"}
    has_versioned_change = any(
        field in update_data and getattr(post, field, None) != update_data[field]
        for field in versioned
    )
    if has_versioned_change:
        from services.content.revision_service import REASON_MANUAL_EDIT, snapshot_post

        await snapshot_post(db, post=post, reason=REASON_MANUAL_EDIT)

    for field, value in update_data.items():
        setattr(post, field, value)
    await db.commit()
    await db.refresh(post, attribute_names=["carousel_images"])
    logger.info("content.post_updated", post_id=str(post_id), tenant_id=str(tenant_id))

    response = ContentPostResponse.model_validate(post)
    if was_published:
        response = response.model_copy(
            update={
                "linkedin_sync_warning": (
                    "Post atualizado localmente. A API do LinkedIn não permite "
                    "editar o conteúdo de posts já publicados — o texto no LinkedIn permanece inalterado."
                )
            }
        )
    return response


# ── Delete ────────────────────────────────────────────────────────────


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_post(
    post_id: uuid.UUID,
    hard: bool = Query(default=False, description="Se True, faz hard delete + remove no LinkedIn"),
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> None:
    """Soft delete por padrão. ?hard=true mantém o comportamento antigo (hard delete + LinkedIn)."""
    post = await _get_post_or_404(post_id, tenant_id, db)

    if hard:
        try:
            await delete_from_linkedin(db, post=post, tenant_id=tenant_id)
        except LinkedInClientError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Erro ao deletar post no LinkedIn (API {exc.status_code}): {exc.detail}. "
                "O post local não foi removido.",
            ) from exc
        await db.delete(post)
        await db.commit()
        logger.info("content.post_hard_deleted", post_id=str(post_id), tenant_id=str(tenant_id))
        return

    if post.deleted_at is not None:
        # Idempotente
        return
    post.deleted_at = datetime.now(UTC)
    await db.commit()
    logger.info("content.post_soft_deleted", post_id=str(post_id), tenant_id=str(tenant_id))


@router.post("/{post_id}/restore", response_model=ContentPostResponse)
async def restore_post(
    post_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ContentPostResponse:
    """Restaura um post soft-deleted (deleted_at IS NOT NULL)."""
    result = await db.execute(
        select(ContentPost)
        .where(ContentPost.id == post_id, ContentPost.tenant_id == tenant_id)
        .options(selectinload(ContentPost.carousel_images))
    )
    post = result.scalar_one_or_none()
    if post is None:
        raise HTTPException(status_code=404, detail="Post não encontrado")
    if post.deleted_at is None:
        raise HTTPException(status_code=409, detail="Post não está deletado")
    post.deleted_at = None
    await db.commit()
    await db.refresh(post)
    logger.info("content.post_restored", post_id=str(post_id), tenant_id=str(tenant_id))
    return ContentPostResponse.model_validate(post)


# ── Revisões (Phase 3D) ───────────────────────────────────────────────


@router.get("/{post_id}/revisions", response_model=list[ContentPostRevisionResponse])
async def list_post_revisions(
    post_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=200),
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> list[ContentPostRevisionResponse]:
    """Lista revisões (snapshots) de um post, mais recentes primeiro."""
    from models.content_post_revision import ContentPostRevision

    # Confirma ownership
    await _get_post_or_404(post_id, tenant_id, db)

    result = await db.execute(
        select(ContentPostRevision)
        .where(
            ContentPostRevision.post_id == post_id,
            ContentPostRevision.tenant_id == tenant_id,
        )
        .order_by(ContentPostRevision.created_at.desc())
        .limit(limit)
    )
    revisions = list(result.scalars().all())
    return [ContentPostRevisionResponse.model_validate(r) for r in revisions]


@router.post("/{post_id}/revisions/{revision_id}/restore", response_model=ContentPostResponse)
async def restore_post_revision(
    post_id: uuid.UUID,
    revision_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ContentPostResponse:
    """Aplica snapshot de revisão antiga ao post.

    Cria nova revisão com reason='restore' antes de aplicar.
    Permitido apenas em status draft|approved|failed (nunca published/scheduled).
    """
    from models.content_post_revision import ContentPostRevision
    from services.content.revision_service import (
        REASON_RESTORE,
        apply_snapshot,
        snapshot_post,
    )

    post = await _get_post_or_404(post_id, tenant_id, db)
    if post.status not in ("draft", "approved", "failed"):
        raise HTTPException(
            status_code=409,
            detail=f"Restauração não permitida em status {post.status}",
        )

    rev_result = await db.execute(
        select(ContentPostRevision).where(
            ContentPostRevision.id == revision_id,
            ContentPostRevision.post_id == post_id,
            ContentPostRevision.tenant_id == tenant_id,
        )
    )
    revision = rev_result.scalar_one_or_none()
    if revision is None:
        raise HTTPException(status_code=404, detail="Revisão não encontrada")

    # Snapshot do estado atual antes de aplicar
    await snapshot_post(db, post=post, reason=REASON_RESTORE)
    changed = apply_snapshot(post, dict(revision.snapshot))
    await db.commit()
    await db.refresh(post, attribute_names=["carousel_images"])
    logger.info(
        "content.post_revision_restored",
        post_id=str(post_id),
        revision_id=str(revision_id),
        changed_fields=changed,
        tenant_id=str(tenant_id),
    )
    return ContentPostResponse.model_validate(post)


# ── Aprovacao ─────────────────────────────────────────────────────────


@router.patch("/{post_id}/approve", response_model=ContentPostResponse)
async def approve_post(
    post_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ContentPostResponse:
    post = await _get_post_or_404(post_id, tenant_id, db)
    if post.status not in ("draft", "failed"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Apenas posts em 'draft' ou 'failed' podem ser aprovados. "
                f"Status atual: '{post.status}'."
            ),
        )
    post.status = "approved"
    post.error_message = None
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
    from datetime import datetime

    post = await _get_post_or_404(post_id, tenant_id, db)
    post.impressions = body.impressions
    post.likes = body.likes
    post.comments = body.comments
    post.shares = body.shares
    if body.engagement_rate is not None:
        post.engagement_rate = body.engagement_rate
    post.metrics_updated_at = datetime.now(UTC)
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
    from services.content.linkedin_client import LinkedInClientError
    from services.content.publisher import publish_now as svc_publish

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


# ── First comment retry ──────────────────────────────────────────────


@router.post("/{post_id}/first-comment/retry", response_model=ContentPostResponse)
async def retry_first_comment(
    post_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ContentPostResponse:
    """
    Re-tenta postar o first comment de um post ja publicado.

    Aceita posts com first_comment_status == "failed" ou "pending".
    Recarrega post com carousel_images apos atualizacao.
    """
    from services.content.comment_publisher import post_first_comment
    from services.content.linkedin_client import LinkedInClientError

    try:
        await post_first_comment(db, post_id=post_id, tenant_id=tenant_id)
    except LinkedInClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LinkedIn API error {exc.status_code}: {exc.detail}",
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    # Reload com carousel_images para resposta consistente
    result = await db.execute(
        select(ContentPost)
        .where(ContentPost.id == post_id, ContentPost.tenant_id == tenant_id)
        .options(selectinload(ContentPost.carousel_images))
    )
    post = result.scalar_one()
    logger.info(
        "content.first_comment_retried",
        post_id=str(post_id),
        tenant_id=str(tenant_id),
        status=post.first_comment_status,
    )
    return ContentPostResponse.model_validate(post)


# ── Imagem gerada por IA ──────────────────────────────────────────────


@router.delete(
    "/{post_id}/image",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Remove a imagem do post (S3 + campos do banco)",
)
async def delete_post_image(
    post_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> None:
    from integrations.s3_client import S3Client

    post = await _get_post_or_404(post_id, tenant_id, db)

    if post.image_s3_key:
        try:
            S3Client().delete_object(post.image_s3_key)
        except Exception:
            pass

    post.image_url = None
    post.image_s3_key = None
    post.image_style = None
    post.image_prompt = None
    post.image_aspect_ratio = None
    post.image_filename = None
    post.image_size_bytes = None
    post.linkedin_image_urn = None

    await db.commit()
    logger.info("content.post_image_deleted", post_id=str(post_id), tenant_id=str(tenant_id))


# ── Upload manual de imagem ──────────────────────────────────────────

_MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB
_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


@router.post(
    "/{post_id}/upload-image",
    response_model=ContentPostResponse,
    summary="Faz upload manual de imagem para o post",
)
async def upload_post_image(
    post_id: uuid.UUID,
    file: UploadFile = File(...),
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ContentPostResponse:
    """
    Aceita JPEG, PNG, WEBP, GIF. Tamanho máximo: 10 MB.
    Substitui qualquer imagem existente (gerada por IA ou upload anterior).
    """
    from integrations.s3_client import S3Client

    if file.content_type not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Formato inválido. Aceitos: JPEG, PNG, WEBP, GIF.",
        )

    post = await _get_post_or_404(post_id, tenant_id, db)

    image_bytes = await file.read()

    if len(image_bytes) > _MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Imagem excede o limite de 10 MB.",
        )

    if post.image_s3_key:
        try:
            S3Client().delete_object(post.image_s3_key)
        except Exception:
            pass

    original_name = file.filename or "image.jpg"
    ext = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else "jpg"
    s3_key = f"images/{tenant_id}/{post_id}.{ext}"
    s3 = S3Client()
    image_url = s3.upload_bytes(image_bytes, s3_key, file.content_type or "image/jpeg")

    post.image_url = image_url
    post.image_s3_key = s3_key
    post.image_filename = original_name
    post.image_size_bytes = len(image_bytes)
    post.image_style = None
    post.image_prompt = None
    post.image_aspect_ratio = None
    post.linkedin_image_urn = None

    await db.commit()
    await db.refresh(post)

    logger.info(
        "content.post_image_uploaded",
        post_id=str(post_id),
        tenant_id=str(tenant_id),
        size_bytes=len(image_bytes),
    )
    return ContentPostResponse.model_validate(post)


# ── Upload de vídeo ───────────────────────────────────────────────────

_MAX_VIDEO_SIZE = 150 * 1024 * 1024  # 150 MB


@router.post(
    "/{post_id}/upload-video",
    response_model=ContentPostResponse,
    summary="Faz upload de vídeo MP4 para o post",
)
async def upload_post_video(
    post_id: uuid.UUID,
    file: UploadFile = File(...),
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ContentPostResponse:
    """
    Aceita apenas video/mp4. Tamanho máximo: 150 MB.
    Salva no S3 e atualiza post.video_url + post.video_s3_key.
    """
    from integrations.s3_client import S3Client

    if file.content_type not in ("video/mp4", "video/quicktime"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Formato inválido. Apenas video/mp4 é aceito.",
        )

    post = await _get_post_or_404(post_id, tenant_id, db)

    video_bytes = await file.read()

    if len(video_bytes) > _MAX_VIDEO_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Vídeo excede o limite de 150 MB.",
        )

    # Remove vídeo anterior do S3
    if post.video_s3_key:
        try:
            S3Client().delete_object(post.video_s3_key)
        except Exception:
            pass

    s3_key = f"videos/{tenant_id}/{post_id}.mp4"
    s3 = S3Client()
    video_url = s3.upload_bytes(video_bytes, s3_key, "video/mp4")

    post.video_url = video_url
    post.video_s3_key = s3_key
    post.video_filename = file.filename or "video.mp4"
    post.video_size_bytes = len(video_bytes)
    post.linkedin_video_urn = None  # URN inválido após novo upload

    await db.commit()
    await db.refresh(post)

    logger.info(
        "content.post_video_uploaded",
        post_id=str(post_id),
        tenant_id=str(tenant_id),
        size_bytes=len(video_bytes),
    )
    return ContentPostResponse.model_validate(post)


@router.delete(
    "/{post_id}/video",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Remove o vídeo do post (S3 + campos do banco)",
)
async def delete_post_video(
    post_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> None:
    from integrations.s3_client import S3Client

    post = await _get_post_or_404(post_id, tenant_id, db)

    if post.video_s3_key:
        try:
            S3Client().delete_object(post.video_s3_key)
        except Exception:
            pass

    post.video_url = None
    post.video_s3_key = None
    post.video_filename = None
    post.video_size_bytes = None
    post.linkedin_video_urn = None

    await db.commit()
    logger.info("content.post_video_deleted", post_id=str(post_id), tenant_id=str(tenant_id))


# ── Proxy de imagem (S3 privado) ────────────────────────────────────────────────


@router.get(
    "/{post_id}/image",
    summary="Retorna a imagem do post (proxy do S3 privado)",
    response_class=StreamingResponse,
    include_in_schema=True,
)
async def get_post_image(
    post_id: uuid.UUID,
    db: AsyncSession = Depends(get_session_no_auth),
) -> StreamingResponse:
    import io

    from integrations.s3_client import S3Client

    result = await db.execute(select(ContentPost).where(ContentPost.id == post_id))
    post = result.scalar_one_or_none()
    if post is None or not post.image_s3_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Imagem não encontrada")

    try:
        data, content_type = S3Client().get_bytes(post.image_s3_key)
    except Exception as exc:
        logger.error("content.post_image_proxy_error", post_id=str(post_id), error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="Erro ao buscar imagem"
        ) from exc

    return StreamingResponse(io.BytesIO(data), media_type=content_type)


# ── Proxy de vídeo (S3 privado, suporte a Range requests) ──────────────────────


@router.get(
    "/{post_id}/video",
    summary="Stream do vídeo do post (proxy do S3 privado)",
    include_in_schema=True,
)
async def stream_post_video(
    request: Request,
    post_id: uuid.UUID,
    db: AsyncSession = Depends(get_session_no_auth),
) -> Response:
    from integrations.s3_client import S3Client

    result = await db.execute(select(ContentPost).where(ContentPost.id == post_id))
    post = result.scalar_one_or_none()
    if post is None or not post.video_s3_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vídeo não encontrado")

    s3 = S3Client()
    range_header = request.headers.get("range")

    try:
        if range_header:
            obj = s3.get_object_range(post.video_s3_key, range_header)
            return Response(
                content=obj["body"],
                status_code=206,
                headers={
                    "Content-Range": obj["content_range"],
                    "Content-Length": str(obj["content_length"]),
                    "Accept-Ranges": "bytes",
                    "Content-Type": "video/mp4",
                    "Cache-Control": "private, max-age=3600",
                },
            )

        data, content_type = s3.get_bytes(post.video_s3_key)
        return Response(
            content=data,
            media_type=content_type or "video/mp4",
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": str(len(data)),
                "Cache-Control": "private, max-age=3600",
            },
        )
    except Exception as exc:
        logger.error("content.post_video_proxy_error", post_id=str(post_id), error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="Erro ao buscar vídeo"
        ) from exc
