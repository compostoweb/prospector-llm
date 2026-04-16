"""
workers/enrichment_queue.py

Task Celery para processamento automático de filas de enriquecimento LinkedIn.

Fluxo:
  1. Beat chama process_enrichment_queue() a cada hora
  2. Busca todos os EnrichmentJobs com status "pending" ou "running"
  3. Para cada job, pega o próximo batch: linkedin_urls[processed_count : processed_count + batch_size]
  4. Envia ao Apify (run_linkedin_enrichment) e persiste leads no DB
  5. Incrementa processed_count; quando processed_count >= total_count, status = "done"

Benefícios:
  - 200 URLs viram 4 batches de 50 processados automaticamente ao longo de 4 horas
  - Zero intervenção manual após criação do job
  - Progresso visível em tempo real via GET /leads/enrichment-jobs
"""

from __future__ import annotations

import asyncio
import uuid

import structlog

from workers.celery_app import celery_app

logger = structlog.get_logger()


# ── Task Beat ──────────────────────────────────────────────────────────

@celery_app.task(
    bind=True,
    name="workers.enrichment_queue.process_enrichment_queue",
    max_retries=1,
    default_retry_delay=120,
    queue="enrich",
)
def process_enrichment_queue(self) -> dict:
    """
    Processa um batch de cada EnrichmentJob pendente/em andamento de todos os tenants.
    Chamado automaticamente pelo Celery Beat a cada hora.
    """
    return asyncio.run(_process_all_jobs_async(self))


# ── Lógica assíncrona ─────────────────────────────────────────────────

async def _process_all_jobs_async(task) -> dict:
    """Itera todos os jobs ativos e processa um batch por job."""
    from sqlalchemy import select
    from core.database import WorkerSessionLocal
    from models.enrichment_job import EnrichmentJob

    total_jobs = 0
    total_leads_inserted = 0

    async with WorkerSessionLocal() as session:
        result = await session.execute(
            select(EnrichmentJob).where(
                EnrichmentJob.status.in_(["pending", "running"])
            )
        )
        jobs = list(result.scalars().all())

    for job in jobs:
        try:
            inserted = await _process_job_batch_async(job)
            total_leads_inserted += inserted
            total_jobs += 1
        except Exception as exc:
            logger.error(
                "enrichment_queue.job_error",
                job_id=str(job.id),
                tenant_id=str(job.tenant_id),
                error=str(exc),
            )
            # Marca o job como failed
            await _update_job_status(job.id, "failed", error_message=str(exc))

    logger.info(
        "enrichment_queue.cycle_done",
        jobs_processed=total_jobs,
        leads_inserted=total_leads_inserted,
    )
    return {"jobs_processed": total_jobs, "leads_inserted": total_leads_inserted}


async def _process_job_batch_async(job) -> int:
    """
    Processa um batch do job.
    Retorna o número de leads inseridos.
    """
    from integrations.apify_client import ApifyClient
    from models.enums import LeadSource

    # Calcula o próximo batch
    start = job.processed_count
    end = min(start + job.batch_size, job.total_count)
    batch_urls = job.linkedin_urls[start:end]

    if not batch_urls:
        # Nada a processar — marca como done
        await _update_job_status(job.id, "done")
        return 0

    logger.info(
        "enrichment_queue.batch_start",
        job_id=str(job.id),
        batch_start=start,
        batch_end=end,
        total=job.total_count,
    )

    # Marca como running
    await _update_job_status(job.id, "running")

    # Chama o Apify
    client = ApifyClient()
    try:
        leads_raw = await client.run_linkedin_enrichment(
            linkedin_urls=batch_urls,
            max_items=len(batch_urls),
        )
    finally:
        await client.aclose()

    # Persiste no banco
    inserted = await _persist_enrichment_leads(
        leads_raw=leads_raw,
        tenant_id=job.tenant_id,
        target_list_id=job.target_list_id,
        source=LeadSource.APIFY_LINKEDIN,
    )

    # Atualiza progresso
    new_processed = end
    new_status = "done" if new_processed >= job.total_count else "running"
    await _update_job_progress(job.id, new_processed, new_status)

    logger.info(
        "enrichment_queue.batch_done",
        job_id=str(job.id),
        processed=new_processed,
        total=job.total_count,
        inserted=inserted,
        status=new_status,
    )
    return inserted


async def _persist_enrichment_leads(
    leads_raw,
    tenant_id: uuid.UUID,
    target_list_id: uuid.UUID | None,
    source,
) -> int:
    """
    Persiste leads enriquecidos garantindo dedup e associando à lista alvo.
    Reutiliza a mesma lógica de dedup do capture worker.
    """
    from sqlalchemy import select
    from core.database import WorkerSessionLocal, get_worker_session
    from models.lead import Lead
    from models.lead_list import lead_list_members
    from models.enums import LeadStatus

    inserted = 0

    # Pré-carrega conjuntos de dedup
    async with WorkerSessionLocal() as check_session:
        url_result = await check_session.execute(
            select(Lead.linkedin_url).where(
                Lead.tenant_id == tenant_id,
                Lead.linkedin_url.is_not(None),
            )
        )
        existing_urls: set[str] = {row[0] for row in url_result.all()}

        ws_result = await check_session.execute(
            select(Lead.website).where(
                Lead.tenant_id == tenant_id,
                Lead.website.is_not(None),
            )
        )
        existing_websites: set[str] = {row[0] for row in ws_result.all()}

    seen_urls: set[str] = set()
    seen_websites: set[str] = set()

    async for db in get_worker_session(tenant_id):
        list_member_pairs: list[tuple[uuid.UUID, uuid.UUID]] = []

        for raw in leads_raw:
            if not raw.linkedin_url and not raw.website:
                continue

            if raw.linkedin_url:
                if raw.linkedin_url in existing_urls or raw.linkedin_url in seen_urls:
                    continue
                seen_urls.add(raw.linkedin_url)

            if raw.website:
                if raw.website in existing_websites or raw.website in seen_websites:
                    continue
                seen_websites.add(raw.website)

            if not raw.name:
                continue

            lead = Lead(
                tenant_id=tenant_id,
                name=raw.name,
                first_name=raw.first_name,
                last_name=raw.last_name,
                job_title=raw.job_title,
                company=raw.company,
                company_domain=raw.company_domain,
                website=raw.website,
                industry=raw.industry,
                company_size=raw.company_size,
                linkedin_url=raw.linkedin_url,
                linkedin_profile_id=raw.linkedin_profile_id,
                city=raw.city,
                location=raw.location or raw.city,
                phone=raw.phone,
                email_corporate=raw.email_corporate,
                email_personal=raw.email_personal,
                source=source,
                status=LeadStatus.RAW,
            )
            db.add(lead)
            await db.flush()
            inserted += 1

            if target_list_id is not None:
                list_member_pairs.append((target_list_id, lead.id))

        if list_member_pairs:
            await db.execute(
                lead_list_members.insert().prefix_with("ON CONFLICT DO NOTHING"),
                [
                    {"lead_list_id": str(ll_id), "lead_id": str(l_id)}
                    for ll_id, l_id in list_member_pairs
                ],
            )

        await db.commit()

    return inserted


async def _update_job_status(
    job_id: uuid.UUID,
    status: str,
    error_message: str | None = None,
) -> None:
    from sqlalchemy import update
    from core.database import WorkerSessionLocal
    from models.enrichment_job import EnrichmentJob

    values: dict = {"status": status}
    if error_message is not None:
        values["error_message"] = error_message

    async with WorkerSessionLocal() as session:
        await session.execute(
            update(EnrichmentJob).where(EnrichmentJob.id == job_id).values(**values)
        )
        await session.commit()


async def _update_job_progress(
    job_id: uuid.UUID,
    processed_count: int,
    status: str,
) -> None:
    from sqlalchemy import update
    from core.database import WorkerSessionLocal
    from models.enrichment_job import EnrichmentJob

    async with WorkerSessionLocal() as session:
        await session.execute(
            update(EnrichmentJob)
            .where(EnrichmentJob.id == job_id)
            .values(processed_count=processed_count, status=status)
        )
        await session.commit()
