"""
workers/connection_check.py

Task Celery para verificação periódica de conexões LinkedIn pendentes.
Funciona como fallback quando o webhook relation_created não dispara.

Task:
  check_pending_connections()
    — Busca leads com linkedin_connection_status = "pending"
    — Verifica status via Unipile API
    — Se conectado: atualiza lead + cria ManualTasks (se cadência semi-manual)
    — Se pendente há mais de 14 dias: marca como expirado
    — Fila: "cadence"
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from models.cadence import Cadence
from models.cadence_step import CadenceStep
from models.enums import Channel, StepStatus
from models.lead import Lead
from models.tenant import Tenant
from workers.celery_app import celery_app

logger = structlog.get_logger()

_MAX_PER_TICK = 50
_EXPIRY_DAYS = 14


@celery_app.task(
    bind=True,
    name="workers.connection_check.check_pending_connections",
    max_retries=1,
    queue="cadence",
)
def check_pending_connections(self) -> dict:
    """Verifica status de conexões LinkedIn pendentes."""
    return asyncio.run(_check_async())


async def _check_async() -> dict:
    from core.config import settings
    from integrations.unipile_client import unipile_client

    engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    connected = 0
    expired = 0
    checked = 0

    async with session_factory() as db:
        # Busca leads com conexão pendente (sem filtro de tenant — task de sistema)
        result = await db.execute(
            select(Lead)
            .where(Lead.linkedin_connection_status == "pending")
            .where(Lead.linkedin_profile_id.isnot(None))
            .limit(_MAX_PER_TICK)
        )
        leads = list(result.scalars().all())

        if not leads:
            return {"checked": 0, "connected": 0, "expired": 0}

        account_id = settings.UNIPILE_ACCOUNT_ID_LINKEDIN or ""
        if not account_id:
            logger.warning("connection_check.no_account_id")
            return {"checked": 0, "connected": 0, "expired": 0, "error": "no_account_id"}

        for lead in leads:
            checked += 1
            try:
                status = await unipile_client.get_relation_status(
                    account_id=account_id,
                    linkedin_profile_id=lead.linkedin_profile_id,  # type: ignore[arg-type]
                )

                if status and status.upper() == "CONNECTED":
                    lead.linkedin_connection_status = "connected"
                    lead.linkedin_connected_at = datetime.now(tz=timezone.utc)
                    connected += 1

                    # Cria ManualTasks se cadência semi-manual
                    await _create_tasks_if_semi_manual(lead, db)

                    logger.info(
                        "connection_check.connected",
                        lead_id=str(lead.id),
                    )

                elif await _is_expired(lead, db):
                    lead.linkedin_connection_status = None
                    expired += 1
                    logger.info(
                        "connection_check.expired",
                        lead_id=str(lead.id),
                    )

            except Exception:
                logger.exception(
                    "connection_check.error",
                    lead_id=str(lead.id),
                )

        await db.commit()

    await engine.dispose()

    logger.info(
        "connection_check.done",
        checked=checked,
        connected=connected,
        expired=expired,
    )
    return {"checked": checked, "connected": connected, "expired": expired}


async def _create_tasks_if_semi_manual(lead: Lead, db: async_sessionmaker) -> None:  # type: ignore[type-arg]
    """Cria ManualTasks se o lead está em cadência semi-manual."""
    step_result = await db.execute(
        select(CadenceStep.cadence_id)
        .where(CadenceStep.lead_id == lead.id)
        .limit(1)
    )
    cadence_id = step_result.scalar_one_or_none()
    if not cadence_id:
        return

    cad_result = await db.execute(
        select(Cadence).where(Cadence.id == cadence_id)
    )
    cadence = cad_result.scalar_one_or_none()

    if cadence and cadence.mode == "semi_manual":
        from services.manual_task_service import ManualTaskService
        task_service = ManualTaskService()
        await task_service.create_tasks_for_lead(lead, cadence, db)


def _is_expired(lead: Lead) -> bool:
    """Mantido por compatibilidade — use _is_expired() async para precisão."""
    if not lead.created_at:
        return False
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=_EXPIRY_DAYS)
    return lead.created_at < cutoff


async def _is_expired(lead: Lead, db) -> bool:  # type: ignore[misc]
    """
    Verifica se o convite de conexão expirou (mais de 14 dias desde o envio).
    Usa sent_at do step LINKEDIN_CONNECT para precisão — fallback para lead.created_at.
    """
    sent_at: datetime | None = None
    try:
        step_result = await db.execute(
            select(CadenceStep)
            .where(CadenceStep.lead_id == lead.id)
            .where(CadenceStep.channel == Channel.LINKEDIN_CONNECT)
            .where(CadenceStep.status == StepStatus.SENT)
            .limit(1)
        )
        step = step_result.scalar_one_or_none()
        if step:
            sent_at = step.sent_at
    except Exception:
        pass

    reference = sent_at or lead.created_at
    if not reference:
        return False
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=_EXPIRY_DAYS)
    return reference < cutoff
