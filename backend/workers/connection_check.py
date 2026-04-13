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
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from models.cadence import Cadence
from models.cadence_step import CadenceStep
from models.enums import Channel, StepStatus
from models.lead import Lead
from models.linkedin_account import LinkedInAccount
from models.tenant import TenantIntegration
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

        for lead in leads:
            checked += 1
            try:
                account_id = await _resolve_unipile_account_id_for_lead(lead, db)
                if not account_id:
                    logger.debug(
                        "connection_check.account_unresolved",
                        lead_id=str(lead.id),
                        tenant_id=str(lead.tenant_id),
                    )
                    continue

                status = await unipile_client.get_relation_status(
                    account_id=account_id,
                    linkedin_profile_id=lead.linkedin_profile_id,  # type: ignore[arg-type]
                )

                if status and status.upper() == "CONNECTED":
                    lead.linkedin_connection_status = "connected"
                    lead.linkedin_connected_at = datetime.now(tz=UTC)
                    connected += 1

                    # Cria ManualTasks se cadência semi-manual
                    step_result = await db.execute(
                        select(CadenceStep.cadence_id)
                        .where(CadenceStep.lead_id == lead.id)
                        .limit(1)
                    )
                    cadence_id = step_result.scalar_one_or_none()
                    if cadence_id:
                        cad_result = await db.execute(
                            select(Cadence).where(Cadence.id == cadence_id)
                        )
                        cadence = cad_result.scalar_one_or_none()
                        if cadence and cadence.mode == "semi_manual":
                            from services.manual_task_service import ManualTaskService

                            task_service = ManualTaskService()
                            await task_service.create_tasks_for_lead(lead, cadence, db)

                    logger.info(
                        "connection_check.connected",
                        lead_id=str(lead.id),
                    )

                else:
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
                        sent_at = None

                    reference = sent_at or lead.created_at
                    if reference and reference.tzinfo is None:
                        reference = reference.replace(tzinfo=UTC)

                    cutoff = datetime.now(tz=UTC) - timedelta(days=_EXPIRY_DAYS)
                    if reference and reference < cutoff:
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


async def _resolve_unipile_account_id_for_lead(lead: Lead, db: AsyncSession) -> str | None:
    from core.config import settings

    step_result = await db.execute(
        select(CadenceStep.cadence_id)
        .where(
            CadenceStep.lead_id == lead.id,
            CadenceStep.channel == Channel.LINKEDIN_CONNECT,
        )
        .order_by(CadenceStep.sent_at.desc().nulls_last(), CadenceStep.scheduled_at.desc())
        .limit(1)
    )
    cadence_id = step_result.scalar_one_or_none()
    if cadence_id is not None:
        cadence_result = await db.execute(select(Cadence).where(Cadence.id == cadence_id))
        cadence = cadence_result.scalar_one_or_none()
        if cadence and cadence.linkedin_account_id:
            account_result = await db.execute(
                select(LinkedInAccount).where(LinkedInAccount.id == cadence.linkedin_account_id)
            )
            account = account_result.scalar_one_or_none()
            if account is None:
                return None
            if account.provider_type == "native":
                return None
            if account.unipile_account_id:
                return account.unipile_account_id

    integration_result = await db.execute(
        select(TenantIntegration).where(TenantIntegration.tenant_id == lead.tenant_id)
    )
    integration = integration_result.scalar_one_or_none()
    if integration and integration.unipile_linkedin_account_id:
        return integration.unipile_linkedin_account_id

    return settings.UNIPILE_ACCOUNT_ID_LINKEDIN or None
