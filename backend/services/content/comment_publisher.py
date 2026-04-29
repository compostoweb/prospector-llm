"""
services/content/comment_publisher.py

Posta o "first comment" em um post recem-publicado no LinkedIn e tenta fixar (pin).

A pin via LinkedIn v2 nao e oficialmente suportada — a funcao tenta e, em caso
de falha, marca pin_status="not_supported".
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from models.content_post import ContentPost
from services.content.linkedin_client import LinkedInClient, LinkedInClientError
from services.content.publisher import _load_post_and_account, _maybe_decrypt

logger = structlog.get_logger()


async def post_first_comment(
    db: AsyncSession,
    *,
    post_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> ContentPost:
    """
    Posta o first_comment_text como comentario do proprio autor no post publicado.

    Pre-requisitos:
      - post.status == "published"
      - post.linkedin_post_urn presente
      - post.first_comment_text nao vazio
      - post.first_comment_status in ("pending", "failed")

    Apos sucesso:
      - first_comment_urn preenchido
      - first_comment_status = "posted"
      - first_comment_posted_at = now
      - tenta pin (pin_status = "pinned" | "not_supported" | "failed")
    """
    post, account = await _load_post_and_account(db, post_id, tenant_id)

    if post.status != "published" or not post.linkedin_post_urn:
        raise ValueError(
            f"Post deve estar publicado com URN para receber first comment. "
            f"status={post.status}, urn={post.linkedin_post_urn}"
        )
    if not post.first_comment_text:
        post.first_comment_status = "skipped"
        await db.commit()
        await db.refresh(post)
        return post
    if post.first_comment_status == "posted":
        logger.info("content.comment.already_posted", post_id=str(post_id))
        return post

    access_token = _maybe_decrypt(account.access_token)
    now = datetime.now(UTC)

    try:
        async with LinkedInClient(
            access_token=access_token,
            person_urn=account.person_urn,
        ) as client:
            comment_urn = await client.add_comment(
                post_urn=post.linkedin_post_urn,
                text=post.first_comment_text,
            )
            post.first_comment_urn = comment_urn or None
            post.first_comment_status = "posted"
            post.first_comment_posted_at = now
            post.first_comment_error = None

            # Tenta pin (best effort)
            try:
                pinned = await client.pin_comment(
                    post_urn=post.linkedin_post_urn,
                    comment_urn=comment_urn or "",
                )
                post.first_comment_pin_status = "pinned" if pinned else "not_supported"
            except LinkedInClientError as pin_exc:
                logger.warning(
                    "content.comment.pin_failed",
                    post_id=str(post_id),
                    error=str(pin_exc),
                )
                post.first_comment_pin_status = "failed"

        await db.commit()
        await db.refresh(post)
        logger.info(
            "content.comment.posted",
            post_id=str(post_id),
            comment_urn=comment_urn,
            pin_status=post.first_comment_pin_status,
        )
        return post

    except LinkedInClientError as exc:
        post.first_comment_status = "failed"
        post.first_comment_error = f"{exc.status_code}: {exc.detail}"[:1000]
        await db.commit()
        logger.error(
            "content.comment.failed",
            post_id=str(post_id),
            error=str(exc),
        )
        raise
    except Exception as exc:
        post.first_comment_status = "failed"
        post.first_comment_error = str(exc)[:1000]
        await db.commit()
        logger.error(
            "content.comment.failed",
            post_id=str(post_id),
            error=str(exc),
        )
        raise
