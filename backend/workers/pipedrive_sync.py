from __future__ import annotations

import asyncio
import uuid

import structlog

from core.database import get_worker_session
from services.pipedrive_sync_service import sync_reply_to_pipedrive
from workers.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(
    bind=True,
    name="workers.pipedrive_sync.sync_reply_to_pipedrive",
    max_retries=2,
    default_retry_delay=120,
    queue="dispatch",
)
def sync_reply_to_pipedrive_task(self, interaction_id: str, tenant_id: str) -> dict:
    return asyncio.run(_sync_reply_to_pipedrive_async(interaction_id, tenant_id, self))


async def _sync_reply_to_pipedrive_async(interaction_id: str, tenant_id: str, task) -> dict:
    try:
        interaction_uuid = uuid.UUID(interaction_id)
        tenant_uuid = uuid.UUID(tenant_id)
    except ValueError:
        logger.warning(
            "pipedrive.reply_sync.invalid_ids",
            interaction_id=interaction_id,
            tenant_id=tenant_id,
        )
        return {"status": "invalid_ids", "interaction_id": interaction_id}

    try:
        async for db in get_worker_session(tenant_uuid):
            result = await sync_reply_to_pipedrive(
                db=db,
                tenant_id=tenant_uuid,
                interaction_id=interaction_uuid,
            )
            return {
                "status": result.status,
                "interaction_id": str(result.interaction_id),
                "person_id": result.person_id,
                "deal_id": result.deal_id,
                "error": result.error,
            }
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "pipedrive.reply_sync.error",
            interaction_id=interaction_id,
            tenant_id=tenant_id,
            error=str(exc),
        )
        raise task.retry(exc=RuntimeError(f"{type(exc).__name__}: {exc}"))

    return {"status": "error", "interaction_id": interaction_id, "error": "no_session"}
