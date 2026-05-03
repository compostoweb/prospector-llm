"""
workers/content_lm_sync.py

Tasks Celery para sincronizar leads capturados com o SendPulse.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog

from workers.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(
    bind=True,
    name="workers.content_lm_sync.sync_lm_lead_to_sendpulse",
    max_retries=3,
    default_retry_delay=60,
    queue="content",
)
def sync_lm_lead_to_sendpulse(self, lm_lead_id: str, tenant_id: str) -> dict[str, object]:
    return asyncio.run(_sync_lm_lead_async(lm_lead_id, tenant_id, self))


async def _sync_lm_lead_async(lm_lead_id: str, tenant_id: str, task: Any) -> dict[str, object]:
    from sqlalchemy import select

    from core.database import get_worker_session
    from integrations.sendpulse_client import SendPulseClient, SendPulseClientError
    from models.content_lead_magnet import ContentLeadMagnet
    from models.content_lm_lead import ContentLMLead

    tid = uuid.UUID(tenant_id)
    lid = uuid.UUID(lm_lead_id)

    async for db in get_worker_session(tid):
        result = await db.execute(
            select(ContentLMLead, ContentLeadMagnet)
            .join(ContentLeadMagnet, ContentLeadMagnet.id == ContentLMLead.lead_magnet_id)
            .where(
                ContentLMLead.id == lid,
                ContentLMLead.tenant_id == tid,
            )
        )
        row = result.first()
        if row is None:
            logger.warning("content.lm_sync.lead_not_found", lm_lead_id=lm_lead_id, tenant_id=tenant_id)
            return {"status": "skipped", "reason": "not_found"}

        lm_lead, lead_magnet = row

        if lm_lead.sendpulse_sync_status == "synced" and lm_lead.sendpulse_subscriber_id:
            return {"status": "skipped", "reason": "already_synced"}

        if not lead_magnet.sendpulse_list_id:
            lm_lead.sendpulse_sync_status = "skipped"
            lm_lead.sendpulse_last_error = "Lead magnet sem sendpulse_list_id configurado"
            await db.commit()
            return {"status": "skipped", "reason": "missing_list_id"}

        client = SendPulseClient()
        lm_lead.sendpulse_sync_status = "processing"
        await db.commit()

        try:
            response = await client.add_subscriber_to_list(
                list_id=lead_magnet.sendpulse_list_id,
                email=lm_lead.email,
                name=lm_lead.name,
                variables={
                    "company": lm_lead.company,
                    "role": lm_lead.role,
                    "phone": lm_lead.phone,
                    "lead_magnet": lead_magnet.title,
                    "origin": lm_lead.origin,
                },
            )
            subscriber_id = _extract_subscriber_id(response)
            if subscriber_id is None:
                logger.warning(
                    "content.lm_sync.subscriber_id_missing",
                    lm_lead_id=lm_lead_id,
                    tenant_id=tenant_id,
                    list_id=lead_magnet.sendpulse_list_id,
                )

            lm_lead.sendpulse_list_id = lead_magnet.sendpulse_list_id
            lm_lead.sendpulse_subscriber_id = subscriber_id
            lm_lead.sendpulse_sync_status = "synced"
            lm_lead.sendpulse_last_error = None
            lm_lead.sendpulse_last_synced_at = datetime.now(timezone.utc)
            if lm_lead.sequence_status == "pending":
                lm_lead.sequence_status = "active"
            await db.commit()

            logger.info(
                "content.lm_sync.synced",
                lm_lead_id=lm_lead_id,
                tenant_id=tenant_id,
                list_id=lead_magnet.sendpulse_list_id,
            )
            return {
                "status": "synced",
                "lm_lead_id": lm_lead_id,
                "subscriber_id": subscriber_id,
            }
        except SendPulseClientError as exc:
            lm_lead.sendpulse_sync_status = "failed"
            lm_lead.sendpulse_last_error = str(exc)
            await db.commit()
            logger.error(
                "content.lm_sync.sendpulse_error",
                lm_lead_id=lm_lead_id,
                tenant_id=tenant_id,
                error=str(exc),
                retries=task.request.retries,
            )
            raise task.retry(exc=exc)
        except Exception as exc:  # noqa: BLE001
            lm_lead.sendpulse_sync_status = "failed"
            lm_lead.sendpulse_last_error = str(exc)
            await db.commit()
            logger.error(
                "content.lm_sync.unexpected_error",
                lm_lead_id=lm_lead_id,
                tenant_id=tenant_id,
                error=str(exc),
                retries=task.request.retries,
            )
            raise task.retry(exc=exc)

    return {"status": "skipped", "reason": "session_unavailable"}


def _extract_subscriber_id(response: dict) -> str | None:
    candidates = (
        response.get("id"),
        response.get("subscriber_id"),
        response.get("result", {}).get("id") if isinstance(response.get("result"), dict) else None,
        response.get("data", {}).get("id") if isinstance(response.get("data"), dict) else None,
    )
    for candidate in candidates:
        if candidate:
            return str(candidate)
    return None


@celery_app.task(
    bind=True,
    name="workers.content_lm_sync.send_lm_delivery_email",
    max_retries=3,
    default_retry_delay=90,
    queue="content",
)
def send_lm_delivery_email(self, lm_lead_id: str, tenant_id: str) -> dict[str, object]:
    return asyncio.run(_send_lm_delivery_email_async(lm_lead_id, tenant_id, self))


async def _send_lm_delivery_email_async(
    lm_lead_id: str,
    tenant_id: str,
    task: Any,
) -> dict[str, object]:
    from sqlalchemy import select

    from core.database import get_worker_session
    from models.content_lead_magnet import ContentLeadMagnet
    from models.content_lm_lead import ContentLMLead
    from services.notification import send_lead_magnet_delivery_email

    tid = uuid.UUID(tenant_id)
    lid = uuid.UUID(lm_lead_id)

    async for db in get_worker_session(tid):
        result = await db.execute(
            select(ContentLMLead, ContentLeadMagnet)
            .join(ContentLeadMagnet, ContentLeadMagnet.id == ContentLMLead.lead_magnet_id)
            .where(ContentLMLead.id == lid, ContentLMLead.tenant_id == tid)
        )
        row = result.first()
        if row is None:
            logger.warning(
                "content.lm_delivery.lead_not_found",
                lm_lead_id=lm_lead_id,
                tenant_id=tenant_id,
            )
            return {"status": "skipped", "reason": "not_found"}

        lm_lead, lead_magnet = row
        if lead_magnet.type == "calculator":
            return {"status": "skipped", "reason": "calculator"}

        sent = await send_lead_magnet_delivery_email(lm_lead=lm_lead, lead_magnet=lead_magnet)
        if sent:
            return {"status": "sent", "lm_lead_id": lm_lead_id}

        exc = RuntimeError("Falha ao enviar email de entrega do lead magnet")
        logger.error(
            "content.lm_delivery.failed",
            lm_lead_id=lm_lead_id,
            tenant_id=tenant_id,
            retries=task.request.retries,
        )
        raise task.retry(exc=exc)

    return {"status": "skipped", "reason": "session_unavailable"}