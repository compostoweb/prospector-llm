"""
services/content/publisher.py

Logica de publicacao de posts no LinkedIn para o Content Hub.

Responsabilidades:
  - Carregar post e conta LinkedIn do tenant
  - Decriptar access_token
  - Chamar LinkedInClient para publicar ou agendar
  - Atualizar status do ContentPost
  - Gravar ContentPublishLog (imutavel)

Esta camada NAO sabe nada de Celery — chamada tanto por workers quanto
por endpoints HTTP de publicacao imediata.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from integrations.s3_client import S3Client
from models.content_linkedin_account import ContentLinkedInAccount
from models.content_post import ContentPost
from models.content_publish_log import ContentPublishLog
from services.content.linkedin_client import LinkedInClient, LinkedInClientError

logger = structlog.get_logger()


# ── Decriptacao de token ──────────────────────────────────────────────


def _maybe_decrypt(value: str) -> str:
    """
    Decripta o valor com Fernet caso LINKEDIN_ACCOUNT_ENCRYPTION_KEY esteja definida.
    Retorna plain text em caso de chave ausente ou falha.
    """
    from core.config import settings

    if not settings.LINKEDIN_ACCOUNT_ENCRYPTION_KEY:
        return value
    try:
        from cryptography.fernet import Fernet

        fernet = Fernet(settings.LINKEDIN_ACCOUNT_ENCRYPTION_KEY.encode())
        return fernet.decrypt(value.encode()).decode()
    except Exception as exc:
        logger.warning("content.publisher.token_decrypt_failed", error=str(exc))
        return value


# ── Helpers internos ──────────────────────────────────────────────────


async def _load_post_and_account(
    db: AsyncSession,
    post_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> tuple[ContentPost, ContentLinkedInAccount]:
    """
    Carrega ContentPost e ContentLinkedInAccount do tenant.
    Levanta ValueError se algum dos dois nao existir.
    """
    post_result = await db.execute(
        select(ContentPost).where(
            ContentPost.id == post_id,
            ContentPost.tenant_id == tenant_id,
        )
    )
    post = post_result.scalar_one_or_none()
    if post is None:
        raise ValueError(f"Post {post_id} nao encontrado para tenant {tenant_id}.")

    account_result = await db.execute(
        select(ContentLinkedInAccount).where(
            ContentLinkedInAccount.tenant_id == tenant_id,
            ContentLinkedInAccount.is_active.is_(True),
        )
    )
    account = account_result.scalar_one_or_none()
    if account is None:
        raise ValueError(
            "Nenhuma conta LinkedIn ativa encontrada para o tenant. "
            "Conecte uma conta em /content/linkedin/auth-url."
        )

    return post, account


def _write_publish_log(
    db: AsyncSession,
    *,
    post_id: uuid.UUID,
    tenant_id: uuid.UUID,
    action: str,
    linkedin_response: dict | None = None,
    error_detail: str | None = None,
) -> ContentPublishLog:
    """Cria e adiciona um ContentPublishLog na sessao (sem commit)."""
    log = ContentPublishLog(
        post_id=post_id,
        tenant_id=tenant_id,
        action=action,
        linkedin_response=linkedin_response,
        error_detail=error_detail,
    )
    db.add(log)
    return log


# ── Funcoes publicas ──────────────────────────────────────────────────


async def publish_now(
    db: AsyncSession,
    *,
    post_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> ContentPost:
    """
    Publica um post imediatamente no LinkedIn.

    - Status obrigatorio: approved | scheduled
    - Atualiza: status=published, linkedin_post_urn, published_at
    - Grava PublishLog (action=publish)
    """
    post, account = await _load_post_and_account(db, post_id, tenant_id)

    if post.status not in ("approved", "scheduled"):
        raise ValueError(
            f"Post deve estar aprovado ou agendado para publicar. Status atual: {post.status}"
        )

    access_token = _maybe_decrypt(account.access_token)

    try:
        async with LinkedInClient(
            access_token=access_token,
            person_urn=account.person_urn,
        ) as client:
            # ── Upload de mídia (se necessário) ──────────────────────
            media_urn: str | None = None
            media_category: str = "NONE"

            if post.image_url and not post.linkedin_image_urn:
                if not post.image_s3_key:
                    raise ValueError(
                        "Post possui image_url mas image_s3_key está ausente. "
                        "Não é possível recuperar a imagem para upload."
                    )
                image_bytes, _ = S3Client().get_bytes(post.image_s3_key)
                post.linkedin_image_urn = await client.upload_image(image_bytes)
                await db.commit()
                logger.info(
                    "content.publisher.image_uploaded",
                    post_id=str(post_id),
                    urn=post.linkedin_image_urn,
                )

            if post.video_url and not post.linkedin_video_urn:
                if not post.video_s3_key:
                    raise ValueError(
                        "Post possui video_url mas video_s3_key está ausente. "
                        "Não é possível recuperar o vídeo para upload."
                    )
                video_bytes, _ = S3Client().get_bytes(post.video_s3_key)
                post.linkedin_video_urn = await client.upload_video(video_bytes)
                await db.commit()
                logger.info(
                    "content.publisher.video_uploaded",
                    post_id=str(post_id),
                    urn=post.linkedin_video_urn,
                )

            # Prioriza vídeo sobre imagem se ambos existirem
            if post.linkedin_video_urn:
                media_urn = post.linkedin_video_urn
                media_category = "VIDEO"
            elif post.linkedin_image_urn:
                media_urn = post.linkedin_image_urn
                media_category = "IMAGE"

            li_response = await client.create_post(
                post.body,
                media_urn=media_urn,
                media_category=media_category,
            )
    except LinkedInClientError as exc:
        # Grava falha e propaga
        post.status = "failed"
        post.error_message = f"LinkedIn API {exc.status_code}: {exc.detail}"
        _write_publish_log(
            db,
            post_id=post_id,
            tenant_id=tenant_id,
            action="fail",
            error_detail=post.error_message,
        )
        await db.commit()
        logger.error(
            "content.publisher.publish_failed",
            post_id=str(post_id),
            tenant_id=str(tenant_id),
            error=exc.detail,
        )
        raise

    # Extrai URN da resposta: header X-RestLi-Id ou campo id
    post_urn = li_response.get("id") or li_response.get("value", {}).get("id") or ""
    post.status = "published"
    post.linkedin_post_urn = post_urn or None
    post.linkedin_scheduled_id = None
    post.published_at = datetime.now(UTC)
    post.error_message = None

    _write_publish_log(
        db,
        post_id=post_id,
        tenant_id=tenant_id,
        action="publish",
        linkedin_response=li_response,
    )
    await db.commit()
    await db.refresh(post)

    logger.info(
        "content.publisher.published",
        post_id=str(post_id),
        tenant_id=str(tenant_id),
        post_urn=post_urn,
    )
    return post


async def schedule_post(
    db: AsyncSession,
    *,
    post_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> ContentPost:
    """
    Marca post como agendado (status=scheduled).

    Nao chama a LinkedIn API com agendamento nativo — a publicacao ocorre
    pelo worker `check_scheduled_posts` quando publish_date chegar.

    - Status obrigatorio: approved
    - publish_date obrigatorio (deve ser futuro)
    """
    post, _account = await _load_post_and_account(db, post_id, tenant_id)

    if post.status != "approved":
        raise ValueError(f"Post deve estar aprovado para agendar. Status atual: {post.status}")
    if not post.publish_date:
        raise ValueError("Post precisa de publish_date para ser agendado.")

    now = datetime.now(UTC)
    publish_date = post.publish_date
    # Normaliza para tz-aware se vier sem timezone
    if publish_date.tzinfo is None:
        publish_date = publish_date.replace(tzinfo=UTC)

    if publish_date <= now:
        raise ValueError("publish_date deve ser no futuro para agendar.")

    post.status = "scheduled"
    post.error_message = None

    _write_publish_log(
        db,
        post_id=post_id,
        tenant_id=tenant_id,
        action="schedule",
    )
    await db.commit()
    await db.refresh(post)

    logger.info(
        "content.publisher.scheduled",
        post_id=str(post_id),
        tenant_id=str(tenant_id),
        publish_date=str(post.publish_date),
    )
    return post


async def cancel_schedule(
    db: AsyncSession,
    *,
    post_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> ContentPost:
    """
    Cancela agendamento de um post (scheduled → approved).

    Se o post tiver linkedin_scheduled_id, tenta cancelar via API do LinkedIn.
    """
    post, account = await _load_post_and_account(db, post_id, tenant_id)

    if post.status != "scheduled":
        raise ValueError(f"Post deve estar agendado para cancelar. Status atual: {post.status}")

    # Cancela no LinkedIn se tiver URN de post agendado
    if post.linkedin_scheduled_id:
        access_token = _maybe_decrypt(account.access_token)
        try:
            async with LinkedInClient(
                access_token=access_token,
                person_urn=account.person_urn,
            ) as client:
                await client.cancel_scheduled_post(post.linkedin_scheduled_id)
        except LinkedInClientError as exc:
            logger.warning(
                "content.publisher.cancel_linkedin_failed",
                post_id=str(post_id),
                error=exc.detail,
            )
            # Nao bloqueia — ainda reverte o status localmente

    post.status = "approved"
    post.linkedin_scheduled_id = None
    post.error_message = None

    _write_publish_log(
        db,
        post_id=post_id,
        tenant_id=tenant_id,
        action="cancel",
    )
    await db.commit()
    await db.refresh(post)

    logger.info(
        "content.publisher.cancelled",
        post_id=str(post_id),
        tenant_id=str(tenant_id),
    )
    return post


async def delete_from_linkedin(
    db: AsyncSession,
    *,
    post: ContentPost,
    tenant_id: uuid.UUID,
) -> None:
    """
    Tenta remover o post do LinkedIn antes de excluir localmente.

    - Post publicado (linkedin_post_urn): DELETE /ugcPosts/{urn}
    - Post agendado (linkedin_scheduled_id): PATCH lifecycleState=DELETED
    - Draft/approved sem URN: não faz nada

    Levanta LinkedInClientError se a API retornar erro, permitindo que o
    endpoint decida se bloqueia ou apenas registra o aviso.
    """
    if not post.linkedin_post_urn and not post.linkedin_scheduled_id:
        return

    account_result = await db.execute(
        select(ContentLinkedInAccount).where(
            ContentLinkedInAccount.tenant_id == tenant_id,
            ContentLinkedInAccount.is_active.is_(True),
        )
    )
    account = account_result.scalar_one_or_none()
    if account is None:
        logger.warning(
            "content.publisher.delete_linkedin_no_account",
            post_id=str(post.id),
            tenant_id=str(tenant_id),
        )
        return

    access_token = _maybe_decrypt(account.access_token)

    async with LinkedInClient(
        access_token=access_token,
        person_urn=account.person_urn,
    ) as client:
        if post.linkedin_post_urn:
            await client.delete_published_post(post.linkedin_post_urn)
            logger.info(
                "content.publisher.linkedin_deleted",
                post_id=str(post.id),
                post_urn=post.linkedin_post_urn,
            )
        elif post.linkedin_scheduled_id:
            await client.cancel_scheduled_post(post.linkedin_scheduled_id)
            logger.info(
                "content.publisher.linkedin_scheduled_deleted",
                post_id=str(post.id),
                scheduled_id=post.linkedin_scheduled_id,
            )
