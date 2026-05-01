"""
services/content/article_service.py

Logica de publicacao de Articles (link share posts) no LinkedIn
via REST Posts API.

Article = post tipo cartao com link externo (newsletter/blog/etc).
Diferente de ContentPost, nao usa /ugcPosts.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from integrations.s3_client import S3Client
from models.content_article import ContentArticle
from models.content_linkedin_account import ContentLinkedInAccount
from services.content.linkedin_client import LinkedInClient, LinkedInClientError
from services.content.token_refresh import (
    ensure_fresh_token,
    is_token_expired_error,
    refresh_and_persist,
)

logger = structlog.get_logger()


async def _load_article_and_account(
    db: AsyncSession,
    article_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> tuple[ContentArticle, ContentLinkedInAccount]:
    art_result = await db.execute(
        select(ContentArticle).where(
            ContentArticle.id == article_id,
            ContentArticle.tenant_id == tenant_id,
        )
    )
    article = art_result.scalar_one_or_none()
    if article is None:
        raise ValueError(f"Article {article_id} nao encontrado para tenant {tenant_id}.")

    acc_result = await db.execute(
        select(ContentLinkedInAccount).where(
            ContentLinkedInAccount.tenant_id == tenant_id,
            ContentLinkedInAccount.is_active.is_(True),
        )
    )
    account = acc_result.scalar_one_or_none()
    if account is None:
        raise ValueError(
            "Nenhuma conta LinkedIn ativa para o tenant. "
            "Conecte uma conta em /content/linkedin/auth-url."
        )
    return article, account


async def publish_article_now(
    db: AsyncSession,
    *,
    article_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> ContentArticle:
    """
    Publica um Article (link share) imediatamente no LinkedIn.

    - status obrigatorio: approved | scheduled
    - upload de thumbnail se thumbnail_s3_key e linkedin_image_urn ausente
    - chama POST /rest/posts content.article
    - atualiza status=published, linkedin_post_urn, published_at
    """
    article, account = await _load_article_and_account(db, article_id, tenant_id)

    if article.status not in ("approved", "scheduled"):
        raise ValueError(
            f"Article deve estar approved ou scheduled. Status atual: {article.status}"
        )

    access_token = await ensure_fresh_token(db, account)

    async def _do_publish(token: str) -> dict[str, Any]:
        async with LinkedInClient(access_token=token, person_urn=account.person_urn) as client:
            # Upload thumbnail se necessario
            if article.thumbnail_s3_key and not article.linkedin_image_urn:
                try:
                    image_bytes, _ = S3Client().get_bytes(article.thumbnail_s3_key)
                    article.linkedin_image_urn = await client.upload_image(image_bytes)
                    await db.commit()
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "content.article.thumbnail_upload_failed",
                        article_id=str(article_id),
                        error=str(exc),
                    )

            return await client.create_article_post(
                commentary=article.commentary or "",
                source_url=article.source_url,
                title=article.title,
                description=article.description,
                thumbnail_urn=article.linkedin_image_urn,
            )

    try:
        response = await _do_publish(access_token)
    except LinkedInClientError as exc:
        if is_token_expired_error(exc) and account.refresh_token:
            logger.info("content.article.token_401_refreshing", article_id=str(article_id))
            access_token = await refresh_and_persist(db, account)
            response = await _do_publish(access_token)
        else:
            article.status = "failed"
            article.error_message = f"{exc.status_code}: {exc.detail}"[:1000]
            await db.commit()
            raise

    article.status = "published"
    article.linkedin_post_urn = (response.get("id") or "") or None
    article.published_at = datetime.now(UTC)
    article.error_message = None
    await db.commit()
    await db.refresh(article)

    logger.info(
        "content.article_published",
        article_id=str(article_id),
        post_urn=article.linkedin_post_urn,
        tenant_id=str(tenant_id),
    )
    return article
