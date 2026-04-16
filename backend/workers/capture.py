"""
workers/capture.py

Tasks Celery para captura de leads via Apify.

Tasks:
  run_apify_maps(queries, max_items, tenant_id)
    — Executa o Apify Google Maps Actor e insere leads no banco
    — Fila: "capture"

  run_apify_linkedin(titles, locations, max_items, tenant_id)
    — Executa o Apify LinkedIn Actor e insere leads no banco
    — Fila: "capture"

Comportamento de inserção:
  - Faz upsert por linkedin_url (ignora duplicatas silenciosamente)
  - Leads sem linkedin_url e sem website são descartados (baixa qualidade)
  - Retorna dict com totais: received, inserted, skipped
"""

from __future__ import annotations

import asyncio
import uuid

import structlog

from integrations.apify_client import ApifyClient, ApifyLeadRaw
from models.enums import LeadSource, LeadStatus
from workers.celery_app import celery_app

logger = structlog.get_logger()


# ── Tasks ─────────────────────────────────────────────────────────────

@celery_app.task(
    bind=True,
    name="workers.capture.run_apify_maps",
    max_retries=3,
    default_retry_delay=60,
    queue="capture",
)
def run_apify_maps(
    self,
    queries: list[str],
    max_items: int = 100,
    tenant_id: str | None = None,
) -> dict:
    """
    Captura empresas via Google Maps Actor do Apify.

    Parâmetros:
      queries:   lista de termos de busca (ex: ["academias São Paulo"])
      max_items: máximo de resultados por query
      tenant_id: UUID do tenant (string) — obrigatório

    Retorna: {"received": N, "inserted": M, "skipped": K}
    """
    if not tenant_id:
        raise ValueError("tenant_id é obrigatório para captura de leads")

    return asyncio.run(
        _run_apify_maps_async(queries, max_items, tenant_id, self)
    )


@celery_app.task(
    bind=True,
    name="workers.capture.run_apify_linkedin",
    max_retries=3,
    default_retry_delay=60,
    queue="capture",
)
def run_apify_linkedin(
    self,
    titles: list[str],
    locations: list[str],
    max_items: int = 50,
    tenant_id: str | None = None,
) -> dict:
    """
    Captura perfis LinkedIn via Apify LinkedIn Actor.

    Parâmetros:
      titles:    cargos de interesse (ex: ["CEO", "Sócio"])
      locations: cidades/regiões (ex: ["São Paulo"])
      max_items: máximo total de resultados
      tenant_id: UUID do tenant (string) — obrigatório

    Retorna: {"received": N, "inserted": M, "skipped": K}
    """
    if not tenant_id:
        raise ValueError("tenant_id é obrigatório para captura de leads")

    return asyncio.run(
        _run_apify_linkedin_async(titles, locations, max_items, tenant_id, self)
    )


# ── Tasks agendadas (beat) — lê config por tenant do banco ──────────

@celery_app.task(
    bind=True,
    name="workers.capture.run_apify_maps_daily",
    max_retries=1,
    default_retry_delay=300,
    queue="capture",
)
def run_apify_maps_daily(self) -> dict:
    """
    Executada pelo Celery Beat (08h diário).
    Para cada tenant ativo que tiver uma CaptureScheduleConfig com
    source='google_maps' e is_active=True, dispara a captura.
    """
    return asyncio.run(_run_apify_maps_daily_async(self))


@celery_app.task(
    bind=True,
    name="workers.capture.run_apify_linkedin_daily",
    max_retries=1,
    default_retry_delay=300,
    queue="capture",
)
def run_apify_linkedin_daily(self) -> dict:
    """
    Executada pelo Celery Beat (09h diário).
    Para cada tenant ativo que tiver uma CaptureScheduleConfig com
    source='b2b_database' e is_active=True, dispara a captura.
    """
    return asyncio.run(_run_apify_linkedin_daily_async(self))


async def _run_apify_maps_daily_async(task) -> dict:
    from sqlalchemy import select
    from core.database import WorkerSessionLocal
    from models.capture_schedule import CaptureScheduleConfig
    from models.tenant import Tenant

    async with WorkerSessionLocal() as root_session:
        result = await root_session.execute(
            select(CaptureScheduleConfig).join(
                Tenant, Tenant.id == CaptureScheduleConfig.tenant_id
            ).where(
                CaptureScheduleConfig.source == "google_maps",
                CaptureScheduleConfig.is_active.is_(True),
                Tenant.is_active.is_(True),
            )
        )
        configs = list(result.scalars().all())

    if not configs:
        logger.info("capture.maps_daily.skipped", reason="nenhum tenant com config ativa")
        return {"tenants": 0, "skipped": True}

    total: dict = {"tenants": len(configs), "received": 0, "inserted": 0, "skipped": 0}
    for cfg in configs:
        queries = cfg.maps_search_terms or []
        if cfg.maps_location:
            queries = [f"{q} {cfg.maps_location}".strip() for q in queries] if queries else [cfg.maps_location]
        if not queries:
            logger.info("capture.maps_daily.tenant_skipped", tenant_id=str(cfg.tenant_id), reason="sem queries")
            continue
        try:
            outcome = await _run_apify_maps_async(queries, cfg.max_items, str(cfg.tenant_id), task)
            total["received"] += outcome.get("received", 0)
            total["inserted"] += outcome.get("inserted", 0)
            total["skipped"] += outcome.get("skipped", 0)
        except Exception as exc:
            logger.error("capture.maps_daily.tenant_error", tenant_id=str(cfg.tenant_id), error=str(exc))

    logger.info("capture.maps_daily.done", **total)
    return total


async def _run_apify_linkedin_daily_async(task) -> dict:
    from sqlalchemy import select
    from core.database import WorkerSessionLocal
    from models.capture_schedule import CaptureScheduleConfig
    from models.tenant import Tenant

    async with WorkerSessionLocal() as root_session:
        result = await root_session.execute(
            select(CaptureScheduleConfig).join(
                Tenant, Tenant.id == CaptureScheduleConfig.tenant_id
            ).where(
                CaptureScheduleConfig.source == "b2b_database",
                CaptureScheduleConfig.is_active.is_(True),
                Tenant.is_active.is_(True),
            )
        )
        configs = list(result.scalars().all())

    if not configs:
        logger.info("capture.linkedin_daily.skipped", reason="nenhum tenant com config ativa")
        return {"tenants": 0, "skipped": True}

    total: dict = {"tenants": len(configs), "received": 0, "inserted": 0, "skipped": 0}
    for cfg in configs:
        titles = cfg.b2b_job_titles or []
        locations = cfg.b2b_locations or cfg.b2b_cities or []
        if not titles or not locations:
            logger.info(
                "capture.linkedin_daily.tenant_skipped",
                tenant_id=str(cfg.tenant_id),
                reason="titles ou locations vazios",
            )
            continue
        try:
            outcome = await _run_apify_linkedin_async(titles, locations, cfg.max_items, str(cfg.tenant_id), task)
            total["received"] += outcome.get("received", 0)
            total["inserted"] += outcome.get("inserted", 0)
            total["skipped"] += outcome.get("skipped", 0)
        except Exception as exc:
            logger.error("capture.linkedin_daily.tenant_error", tenant_id=str(cfg.tenant_id), error=str(exc))

    logger.info("capture.linkedin_daily.done", **total)
    return total


# ── Implementações async ──────────────────────────────────────────────

async def _run_apify_maps_async(
    queries: list[str],
    max_items: int,
    tenant_id: str,
    task,
) -> dict:
    client = ApifyClient()
    try:
        leads_raw = await client.run_google_maps(queries, max_items)
    except Exception as exc:
        logger.error("capture.maps.apify_error", error=str(exc), tenant_id=tenant_id)
        raise task.retry(exc=exc) from exc
    finally:
        await client.aclose()

    return await _persist_leads(
        leads_raw=leads_raw,
        source=LeadSource.APIFY_MAPS,
        tenant_id=tenant_id,
    )


async def _run_apify_linkedin_async(
    titles: list[str],
    locations: list[str],
    max_items: int,
    tenant_id: str,
    task,
) -> dict:
    client = ApifyClient()
    try:
        leads_raw = await client.run_linkedin_search(titles, locations, max_items)
    except Exception as exc:
        logger.error("capture.linkedin.apify_error", error=str(exc), tenant_id=tenant_id)
        raise task.retry(exc=exc) from exc
    finally:
        await client.aclose()

    return await _persist_leads(
        leads_raw=leads_raw,
        source=LeadSource.APIFY_LINKEDIN,
        tenant_id=tenant_id,
    )


async def _persist_leads(
    leads_raw: list[ApifyLeadRaw],
    source: LeadSource,
    tenant_id: str,
) -> dict:
    """
    Persiste a lista de leads brutos no banco.
    Ignora leads sem identificador único (linkedin_url e website ausentes).
    Usa INSERT ... ON CONFLICT DO NOTHING para evitar duplicatas por linkedin_url.
    """
    from core.database import get_worker_session

    tid = uuid.UUID(tenant_id)
    inserted = 0
    skipped = 0

    async for db in get_worker_session(tid):
        for raw in leads_raw:
            # Descarta leads sem nenhum identificador usável
            if not raw.linkedin_url and not raw.website:
                skipped += 1
                continue

            # Verifica duplicata por linkedin_url
            if raw.linkedin_url:
                from sqlalchemy import select
                from models.lead import Lead
                existing = await db.execute(
                    select(Lead.id).where(
                        Lead.tenant_id == tid,
                        Lead.linkedin_url == raw.linkedin_url,
                    )
                )
                if existing.scalar_one_or_none():
                    skipped += 1
                    continue

            from models.lead import Lead
            lead = Lead(
                tenant_id=tid,
                name=raw.name or "Desconhecido",
                company=raw.company,
                website=raw.website,
                linkedin_url=raw.linkedin_url,
                city=raw.city,
                segment=raw.segment,
                phone=raw.phone,
                source=source,
                status=LeadStatus.RAW,
            )
            db.add(lead)
            inserted += 1

        await db.commit()

    logger.info(
        "capture.persist_done",
        source=source.value,
        tenant_id=tenant_id,
        received=len(leads_raw),
        inserted=inserted,
        skipped=skipped,
    )
    return {"received": len(leads_raw), "inserted": inserted, "skipped": skipped}
