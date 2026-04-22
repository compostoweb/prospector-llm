"""
workers/enrich.py

Task Celery para enriquecimento de leads com status RAW.

Task:
  enrich_pending_batch(tenant_id, batch_size)
    — Busca até batch_size leads com status=RAW
    — Para cada lead: descobre e-mail → valida → calcula score → persiste
    — Fila: "enrich"

Pipeline por lead:
  1. EmailFinderService.find()    — cascata Prospeo → Hunter → Apollo
  2. ZeroBounce valida e-mail     — já integrado no EmailFinderService
  3. ContextFetcher.fetch()       — busca contexto do website (assíncrono, para AI)
  4. LeadScorer.score()           — calcula score 0–100
  5. UPDATE leads SET status=ENRICHED, enriched_at=now()
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from urllib.parse import urlparse

import structlog
from sqlalchemy import select

from integrations.context_fetcher import context_fetcher
from models.enums import EmailType, LeadStatus
from models.lead import Lead
from services.email_finder import EmailFinderService
from services.lead_scorer import lead_scorer
from workers.celery_app import celery_app

logger = structlog.get_logger()

_BATCH_SIZE = 50


def _status_after_enrichment(current_status: LeadStatus) -> LeadStatus:
    """
    Preserva estados mais avançados da jornada quando um enrich roda depois.

    Caso típico: lead é criado, inscrito na cadência e o worker de enrich termina em
    seguida. Nesse caso, não podemos rebaixar IN_CADENCE para ENRICHED.
    """
    if current_status in {LeadStatus.IN_CADENCE, LeadStatus.CONVERTED, LeadStatus.ARCHIVED}:
        return current_status
    return LeadStatus.ENRICHED


@celery_app.task(
    bind=True,
    name="workers.enrich.enrich_pending_batch",
    max_retries=1,
    default_retry_delay=120,
    queue="enrich",
)
def enrich_pending_batch(
    self,
    tenant_id: str | None = None,
    batch_size: int = _BATCH_SIZE,
) -> dict:
    """
    Enriquece lotes de leads RAW.

    Quando chamado pelo Beat (sem args): itera TODOS os tenants ativos.
    Quando chamado com tenant_id: processa apenas aquele tenant.

    Retorna: {"total_processed": N, "total_enriched": M, "total_failed": K}
    """
    if tenant_id:
        result = asyncio.run(_enrich_batch_async(tenant_id, batch_size, self))
        return {
            "total_processed": result.get("processed", 0),
            "total_enriched": result.get("enriched", 0),
            "total_failed": result.get("failed", 0),
        }
    return asyncio.run(_enrich_all_tenants_async(batch_size, self))


async def _enrich_all_tenants_async(batch_size: int, task) -> dict:
    """Processa todos os tenants ativos — chamado pelo Beat a cada 30min."""
    from core.database import WorkerSessionLocal
    from models.tenant import Tenant

    total_processed = 0
    total_enriched = 0
    total_failed = 0

    async with WorkerSessionLocal() as root_session:
        tenants_result = await root_session.execute(
            select(Tenant).where(Tenant.is_active.is_(True))
        )
        tenants = list(tenants_result.scalars().all())

    for tenant in tenants:
        try:
            batch_result = await _enrich_batch_async(str(tenant.id), batch_size, task)
            total_processed += batch_result.get("processed", 0)
            total_enriched += batch_result.get("enriched", 0)
            total_failed += batch_result.get("failed", 0)
        except Exception as exc:
            logger.error(
                "enrich.tenant_error",
                tenant_id=str(tenant.id),
                error=str(exc),
            )
            total_failed += 1

    logger.info(
        "enrich.batch_all_tenants.done",
        tenants=len(tenants),
        total_processed=total_processed,
        total_enriched=total_enriched,
        total_failed=total_failed,
    )
    return {
        "total_processed": total_processed,
        "total_enriched": total_enriched,
        "total_failed": total_failed,
    }


@celery_app.task(
    bind=True,
    name="workers.enrich.enrich_lead",
    max_retries=3,
    default_retry_delay=60,
    queue="enrich",
)
def enrich_lead(
    self,
    lead_id: str,
    tenant_id: str,
) -> dict:
    """
    Enriquece um único lead por ID.
    Usado pela API quando um lead é criado com enrich=true.

    Retorna: {"lead_id": lead_id, "status": "enriched"|"failed"}
    """
    return asyncio.run(_enrich_single_async(lead_id, tenant_id, self))


async def _enrich_single_async(
    lead_id: str,
    tenant_id: str,
    task,
) -> dict:
    from core.database import get_worker_session

    tid = uuid.UUID(tenant_id)
    lid = uuid.UUID(lead_id)
    email_finder = EmailFinderService()

    try:
        async for db in get_worker_session(tid):
            result = await db.execute(select(Lead).where(Lead.id == lid, Lead.tenant_id == tid))
            lead = result.scalar_one_or_none()
            if lead is None:
                logger.warning("enrich.single_not_found", lead_id=lead_id)
                return {"lead_id": lead_id, "status": "not_found"}

            try:
                await _enrich_lead(lead, email_finder)
                lead.status = _status_after_enrichment(lead.status)
                lead.enriched_at = datetime.now(tz=UTC)
                lead.score = float(lead_scorer.score(lead))
                await db.commit()
                logger.info("enrich.single_done", lead_id=lead_id)
                return {"lead_id": lead_id, "status": "enriched"}
            except Exception as exc:
                logger.error("enrich.single_failed", lead_id=lead_id, error=str(exc))
                try:
                    raise task.retry(exc=exc)
                except Exception:
                    return {"lead_id": lead_id, "status": "failed"}
    finally:
        await email_finder.aclose()

    return {"lead_id": lead_id, "status": "not_found"}


async def _enrich_batch_async(
    tenant_id: str,
    batch_size: int,
    task,
) -> dict:
    from core.database import get_worker_session

    tid = uuid.UUID(tenant_id)
    email_finder = EmailFinderService()

    enriched_count = 0
    failed_count = 0
    processed_count = 0

    try:
        async for db in get_worker_session(tid):
            # Busca lote de leads RAW
            result = await db.execute(
                select(Lead)
                .where(
                    Lead.tenant_id == tid,
                    Lead.status == LeadStatus.RAW,
                )
                .order_by(Lead.created_at.asc())
                .limit(batch_size)
            )
            leads: list[Lead] = list(result.scalars().all())

            if not leads:
                logger.info("enrich.batch_empty", tenant_id=tenant_id)
                return {"processed": 0, "enriched": 0, "failed": 0}

            processed_count = len(leads)
            logger.info("enrich.batch_started", tenant_id=tenant_id, count=len(leads))

            for lead in leads:
                try:
                    await _enrich_lead(lead, email_finder)
                    lead.status = _status_after_enrichment(lead.status)
                    lead.enriched_at = datetime.now(tz=UTC)
                    lead.score = float(lead_scorer.score(lead))
                    enriched_count += 1
                except Exception as exc:  # noqa: BLE001
                    logger.error(
                        "enrich.lead_failed",
                        lead_id=str(lead.id),
                        error=str(exc),
                    )
                    failed_count += 1

            await db.commit()

    finally:
        await email_finder.aclose()

    logger.info(
        "enrich.batch_done",
        tenant_id=tenant_id,
        processed=processed_count,
        enriched=enriched_count,
        failed=failed_count,
    )
    return {
        "processed": enriched_count + failed_count,
        "enriched": enriched_count,
        "failed": failed_count,
    }


async def _enrich_lead(lead: Lead, email_finder: EmailFinderService) -> None:
    """
    Executa o pipeline de enriquecimento para um único lead.
    Todas as falhas individuais são toleradas (não relança exceção).
    """
    # ── 1. Descoberta de e-mail ───────────────────────────────────────
    domain = _extract_domain(lead.website) if lead.website else None
    first_name, last_name = _split_name(lead.name)

    email_result = await email_finder.find(
        first_name=first_name,
        last_name=last_name,
        domain=domain,
        linkedin_url=lead.linkedin_url,
        existing_email=lead.email_corporate,
    )

    if email_result:
        if email_result.email_type == EmailType.CORPORATE:
            lead.email_corporate = email_result.email
            lead.email_corporate_source = email_result.source
            lead.email_corporate_verified = email_result.verified
        else:
            # Pessoal — armazena mas não sobrescreve corporativo
            if not lead.email_personal:
                lead.email_personal = email_result.email
                lead.email_personal_source = email_result.source

    # ── 2. Contexto do website (pré-aquece cache para o AI Composer) ──
    if lead.website:
        try:
            await context_fetcher.fetch_from_website(lead.website)
        except Exception as exc:  # noqa: BLE001
            logger.warning("enrich.context_failed", lead_id=str(lead.id), error=str(exc))


# ── Helpers ───────────────────────────────────────────────────────────


def _split_name(full_name: str) -> tuple[str, str]:
    """Divide nome completo em primeiro + sobrenome."""
    parts = full_name.strip().split()
    if len(parts) == 0:
        return ("", "")
    if len(parts) == 1:
        return (parts[0], "")
    return (parts[0], " ".join(parts[1:]))


def _extract_domain(website: str) -> str | None:
    """Extrai o domínio limpo de uma URL."""
    try:
        host = urlparse(website).hostname or ""
        return host.removeprefix("www.") or None
    except Exception:  # noqa: BLE001
        return None
