"""
workers/content.py

Tasks Celery para publicacao de posts no Content Hub.

Tasks:
  publish_to_linkedin(post_id, tenant_id)
    — Publica um post aprovado/agendado imediatamente via LinkedIn API
    — Fila: "content"

  cancel_linkedin_post(post_id, tenant_id)
    — Cancela agendamento de um post (scheduled → approved)
    — Fila: "content"

  check_scheduled_posts()
    — Verifica posts com status=scheduled e publish_date <= agora
    — Enfileira publish_to_linkedin para cada um
    — Executada via Celery Beat a cada minuto
    — Fila: "content"

Segurança anti-duplicata:
  - publish_to_linkedin verifica status antes de publicar (idempotencia)
  - check_scheduled_posts e idempotente: cada post so e publicado uma vez
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

import structlog

from workers.celery_app import celery_app

logger = structlog.get_logger()


# ── publish_to_linkedin ───────────────────────────────────────────────


@celery_app.task(
    bind=True,
    name="workers.content.publish_to_linkedin",
    max_retries=3,
    default_retry_delay=60,
    queue="content",
)
def publish_to_linkedin(self, post_id: str, tenant_id: str) -> dict:
    """
    Publica um post no LinkedIn imediatamente.

    Seguro para retry — verifica status antes de agir.
    """
    return asyncio.run(_publish_async(post_id, tenant_id, self))


async def _publish_async(post_id: str, tenant_id: str, task) -> dict:  # type: ignore[type-arg]
    from core.database import get_worker_session
    from services.content.linkedin_client import LinkedInClientError
    from services.content.publisher import publish_now

    tid = uuid.UUID(tenant_id)
    pid = uuid.UUID(post_id)

    async for db in get_worker_session(tid):
        # Verifica status atual antes de publicar (idempotencia)
        from sqlalchemy import select

        from models.content_post import ContentPost

        result = await db.execute(
            select(ContentPost).where(
                ContentPost.id == pid,
                ContentPost.tenant_id == tid,
            )
        )
        post = result.scalar_one_or_none()
        if post is None:
            logger.warning(
                "content.publish_task.post_not_found",
                post_id=post_id,
                tenant_id=tenant_id,
            )
            return {"status": "skipped", "reason": "not_found"}

        if post.status == "published":
            logger.info(
                "content.publish_task.already_published",
                post_id=post_id,
            )
            return {"status": "skipped", "reason": "already_published"}

        if post.status not in ("approved", "scheduled"):
            logger.warning(
                "content.publish_task.invalid_status",
                post_id=post_id,
                status=post.status,
            )
            return {"status": "skipped", "reason": f"invalid_status:{post.status}"}

        try:
            updated_post = await publish_now(db, post_id=pid, tenant_id=tid)
            # Libera lock idempotency (Phase 3A)
            updated_post.processing_at = None
            updated_post.processing_lock_id = None
            await db.commit()
            # Enfileira first comment com delay de 30s, se houver texto
            if updated_post.first_comment_text and updated_post.first_comment_status in (
                "pending",
                "failed",
            ):
                celery_app.send_task(
                    "workers.content.post_first_comment",
                    args=[post_id, tenant_id],
                    countdown=30,
                    queue="content",
                )
            return {
                "status": "published",
                "post_id": post_id,
                "linkedin_post_urn": updated_post.linkedin_post_urn,
            }
        except LinkedInClientError as exc:
            # Libera lock para retry (Phase 3A)
            post.processing_at = None
            post.processing_lock_id = None
            await db.commit()
            logger.error(
                "content.publish_task.linkedin_error",
                post_id=post_id,
                error=exc.detail,
                retries=task.request.retries,
            )
            raise task.retry(exc=exc)
        except ValueError as exc:
            post.processing_at = None
            post.processing_lock_id = None
            await db.commit()
            logger.error(
                "content.publish_task.value_error",
                post_id=post_id,
                error=str(exc),
            )
            return {"status": "failed", "reason": str(exc)}


# ── cancel_linkedin_post ──────────────────────────────────────────────


@celery_app.task(
    bind=True,
    name="workers.content.cancel_linkedin_post",
    max_retries=2,
    default_retry_delay=30,
    queue="content",
)
def cancel_linkedin_post(self, post_id: str, tenant_id: str) -> dict:
    """
    Cancela agendamento de um post (scheduled → approved).
    """
    return asyncio.run(_cancel_async(post_id, tenant_id, self))


async def _cancel_async(post_id: str, tenant_id: str, task) -> dict:  # type: ignore[type-arg]
    from core.database import get_worker_session
    from services.content.publisher import cancel_schedule

    tid = uuid.UUID(tenant_id)
    pid = uuid.UUID(post_id)

    async for db in get_worker_session(tid):
        try:
            await cancel_schedule(db, post_id=pid, tenant_id=tid)
            return {"status": "cancelled", "post_id": post_id}
        except ValueError as exc:
            logger.warning(
                "content.cancel_task.value_error",
                post_id=post_id,
                error=str(exc),
            )
            return {"status": "skipped", "reason": str(exc)}


# ── check_scheduled_posts (Beat) ──────────────────────────────────────


@celery_app.task(
    name="workers.content.check_scheduled_posts",
    queue="content",
)
def check_scheduled_posts() -> dict:
    """
    Verifica posts agendados com publish_date no passado e os publica.

    Executada pelo Celery Beat a cada minuto.
    Enfileira publish_to_linkedin para cada post elegivel.
    """
    return asyncio.run(_check_scheduled_async())


async def _check_scheduled_async() -> dict:
    from datetime import timedelta

    from sqlalchemy import update

    from core.database import WorkerSessionLocal
    from models.content_post import ContentPost

    now = datetime.now(UTC)
    # Posts em processamento ha > 10 minutos sao reabertos (lock expirado)
    stale_threshold = now - timedelta(minutes=10)

    # Usa sessao sem RLS para varrer todos os tenants (task global do Beat)
    async with WorkerSessionLocal() as db:
        # Libera locks expirados
        await db.execute(
            update(ContentPost)
            .where(
                ContentPost.status == "scheduled",
                ContentPost.processing_at.isnot(None),
                ContentPost.processing_at < stale_threshold,
            )
            .values(processing_at=None, processing_lock_id=None)
        )
        # Atomic claim: somente posts livres (processing_at IS NULL)
        lock_id = uuid.uuid4()
        claim_result = await db.execute(
            update(ContentPost)
            .where(
                ContentPost.status == "scheduled",
                ContentPost.publish_date <= now,
                ContentPost.processing_at.is_(None),
                ContentPost.deleted_at.is_(None),
            )
            .values(processing_at=now, processing_lock_id=lock_id)
            .returning(ContentPost.id, ContentPost.tenant_id)
        )
        rows = claim_result.all()
        await db.commit()

        dispatched = 0
        for post_id, tenant_id in rows:
            publish_to_linkedin.apply_async(
                args=[str(post_id), str(tenant_id)],
                queue="content",
            )
            dispatched += 1
            logger.info(
                "content.check_scheduled.dispatched",
                post_id=str(post_id),
                tenant_id=str(tenant_id),
            )

        logger.info(
            "content.check_scheduled.done",
            dispatched=dispatched,
            checked_at=now.isoformat(),
        )
        return {"dispatched": dispatched}


# ── post_first_comment_task ───────────────────────────────────────────


@celery_app.task(
    bind=True,
    name="workers.content.post_first_comment",
    max_retries=3,
    default_retry_delay=60,
    queue="content",
)
def post_first_comment_task(self, post_id: str, tenant_id: str) -> dict:
    """
    Posta o first comment apos a publicacao do post.
    Executado com delay (geralmente 30s) para garantir que o post esteja "no ar".
    """
    return asyncio.run(_post_first_comment_async(post_id, tenant_id, self))


async def _post_first_comment_async(post_id: str, tenant_id: str, task) -> dict:  # type: ignore[type-arg]
    from core.database import get_worker_session
    from services.content.comment_publisher import post_first_comment
    from services.content.linkedin_client import LinkedInClientError

    tid = uuid.UUID(tenant_id)
    pid = uuid.UUID(post_id)

    async for db in get_worker_session(tid):
        try:
            updated = await post_first_comment(db, post_id=pid, tenant_id=tid)
            return {
                "status": updated.first_comment_status,
                "comment_urn": updated.first_comment_urn,
                "pin_status": updated.first_comment_pin_status,
            }
        except LinkedInClientError as exc:
            logger.error(
                "content.first_comment.linkedin_error",
                post_id=post_id,
                error=exc.detail,
                retries=task.request.retries,
            )
            raise task.retry(exc=exc, countdown=60 * (2**task.request.retries))
        except ValueError as exc:
            logger.warning(
                "content.first_comment.value_error",
                post_id=post_id,
                error=str(exc),
            )
            return {"status": "skipped", "reason": str(exc)}


# ── refresh_linkedin_tokens (Phase 3B Beat) ───────────────────────────


@celery_app.task(
    bind=True,
    name="workers.content.refresh_linkedin_tokens",
    queue="content",
)
def refresh_linkedin_tokens(self) -> dict:  # type: ignore[no-untyped-def]
    """
    Beat job diario: renova proativamente access_tokens LinkedIn de contas
    com expires_at < now() + 24h e refresh_token presente.
    """
    return asyncio.run(_refresh_linkedin_tokens_async())


async def _refresh_linkedin_tokens_async() -> dict:
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import select

    from core.database import WorkerSessionLocal
    from models.content_linkedin_account import ContentLinkedInAccount
    from services.content.linkedin_client import LinkedInClientError
    from services.content.token_refresh import refresh_and_persist

    threshold = datetime.now(UTC) + timedelta(hours=24)
    refreshed = 0
    failed = 0

    async with WorkerSessionLocal() as db:
        result = await db.execute(
            select(ContentLinkedInAccount).where(
                ContentLinkedInAccount.is_active.is_(True),
                ContentLinkedInAccount.refresh_token.isnot(None),
                ContentLinkedInAccount.token_expires_at.isnot(None),
                ContentLinkedInAccount.token_expires_at <= threshold,
            )
        )
        accounts = list(result.scalars().all())
        for account in accounts:
            try:
                await refresh_and_persist(db, account)
                refreshed += 1
            except (LinkedInClientError, ValueError) as exc:
                failed += 1
                logger.error(
                    "content.token_refresh_beat.failed",
                    account_id=str(account.id),
                    tenant_id=str(account.tenant_id),
                    error=str(exc),
                )

    logger.info(
        "content.token_refresh_beat.done",
        refreshed=refreshed,
        failed=failed,
        candidates=len(accounts) if accounts else 0,
    )
    return {"refreshed": refreshed, "failed": failed}


# ── purge_old_deleted_posts (Phase 3C Beat) ───────────────────────────


@celery_app.task(
    bind=True,
    name="workers.content.purge_old_deleted_posts",
    queue="content",
)
def purge_old_deleted_posts(self) -> dict:  # type: ignore[no-untyped-def]
    """
    Beat job semanal: hard-delete posts com deleted_at < now() - 30d.
    """
    return asyncio.run(_purge_old_deleted_posts_async())


async def _purge_old_deleted_posts_async() -> dict:
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import delete

    from core.database import WorkerSessionLocal
    from models.content_post import ContentPost

    cutoff = datetime.now(UTC) - timedelta(days=30)
    async with WorkerSessionLocal() as db:
        result = await db.execute(
            delete(ContentPost).where(
                ContentPost.deleted_at.isnot(None),
                ContentPost.deleted_at < cutoff,
            )
        )
        await db.commit()
        deleted_count = result.rowcount or 0

    logger.info("content.purge_deleted.done", purged=deleted_count, cutoff=str(cutoff))
    return {"purged": deleted_count}
