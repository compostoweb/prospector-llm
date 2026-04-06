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
from datetime import datetime, timezone

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
    return asyncio.run(
        _publish_async(post_id, tenant_id, self)
    )


async def _publish_async(post_id: str, tenant_id: str, task) -> dict:  # type: ignore[type-arg]
    from core.database import get_worker_session
    from services.content.publisher import publish_now
    from services.content.linkedin_client import LinkedInClientError

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
            return {
                "status": "published",
                "post_id": post_id,
                "linkedin_post_urn": updated_post.linkedin_post_urn,
            }
        except LinkedInClientError as exc:
            logger.error(
                "content.publish_task.linkedin_error",
                post_id=post_id,
                error=exc.detail,
                retries=task.request.retries,
            )
            raise task.retry(exc=exc)
        except ValueError as exc:
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
    return asyncio.run(
        _cancel_async(post_id, tenant_id, self)
    )


async def _cancel_async(post_id: str, tenant_id: str, task) -> dict:  # type: ignore[type-arg]
    from core.database import get_worker_session
    from services.content.publisher import cancel_schedule
    from services.content.linkedin_client import LinkedInClientError

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
    from sqlalchemy import select
    from core.database import WorkerSessionLocal
    from models.content_post import ContentPost

    now = datetime.now(timezone.utc)

    # Usa sessao sem RLS para varrer todos os tenants (task global do Beat)
    async with WorkerSessionLocal() as db:
        result = await db.execute(
            select(ContentPost.id, ContentPost.tenant_id)
            .where(
                ContentPost.status == "scheduled",
                ContentPost.publish_date <= now,
            )
            .limit(100)
        )
        rows = result.all()

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
