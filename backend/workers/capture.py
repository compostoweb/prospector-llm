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

  run_apify_maps_daily()
    — Beat task (08h). Lê CaptureScheduleConfig por tenant. Motor de rotação:
      escolhe um combo (termo × local) por vez, cria LeadList diária descritiva,
      incrementa maps_combo_index.

  run_apify_linkedin_daily()
    — Beat task (09h). Mesmo padrão mas cicla b2b_cities via b2b_rotation_index.

Comportamento de inserção (_persist_leads):
  - Strict dedup: pula se linkedin_url OU website já existir no tenant
  - Leads sem nenhum identificador (linkedin_url e website) são descartados
  - Nunca sobrescreve lead existente
  - Preenche capture_query e associa à daily_list_id quando fornecidos
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

import structlog

from integrations.apify_client import ApifyClient, ApifyLeadRaw
from models.enums import LeadSource, LeadStatus
from workers.celery_app import celery_app

logger = structlog.get_logger()


# ── Tasks manuais ──────────────────────────────────────────────────────


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

    return asyncio.run(_run_apify_maps_async(queries, max_items, tenant_id, self))


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

    return asyncio.run(_run_apify_linkedin_async(titles, locations, max_items, tenant_id, self))


# ── Tasks agendadas (beat) — motor de rotação por tenant ─────────────


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
    Para cada tenant ativo com CaptureScheduleConfig google_maps ativa:
      - Escolhe o próximo combo (termo × local) via maps_combo_index
      - Cria uma LeadList diária com nome descritivo
      - Incrementa o índice de rotação
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
    Para cada tenant ativo com CaptureScheduleConfig b2b_database ativa:
      - Escolhe a próxima cidade via b2b_rotation_index
      - Cria uma LeadList diária com nome descritivo
      - Incrementa o índice de rotação
    """
    return asyncio.run(_run_apify_linkedin_daily_async(self))


# ── Motor de rotação: Google Maps ────────────────────────────────────


async def _run_apify_maps_daily_async(task) -> dict:
    from sqlalchemy import select

    from core.database import WorkerSessionLocal
    from models.capture_schedule import CaptureScheduleConfig
    from models.tenant import Tenant

    async with WorkerSessionLocal() as root_session:
        result = await root_session.execute(
            select(CaptureScheduleConfig)
            .join(Tenant, Tenant.id == CaptureScheduleConfig.tenant_id)
            .where(
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
        terms = cfg.maps_search_terms or []
        # Usa maps_locations (lista de rotação) se preenchido; fallback para maps_location
        locations = cfg.maps_locations or ([cfg.maps_location] if cfg.maps_location else [])

        if not terms or not locations:
            logger.info(
                "capture.maps_daily.tenant_skipped",
                tenant_id=str(cfg.tenant_id),
                reason="termos ou localidades não configurados",
            )
            continue

        # Produto cartesiano: [(term, loc), ...]
        combos = [(term, loc) for term in terms for loc in locations]
        combo_index = cfg.maps_combo_index % len(combos)
        term, location = combos[combo_index]

        today_str = datetime.now(UTC).strftime("%d/%m/%y")
        list_name = f"Maps {today_str} — {term} em {location}"[:200]
        list_desc = (
            f"Captura automática Google Maps | Termo: {term} | Local: {location} | {today_str}"
        )

        try:
            list_id = await _create_daily_list(
                tenant_id=cfg.tenant_id,
                name=list_name,
                description=list_desc,
            )

            client = ApifyClient()
            try:
                leads_raw = await client.run_google_maps(
                    [term], cfg.max_items, location_query=location
                )
            except Exception as exc:
                logger.error(
                    "capture.maps_daily.apify_error",
                    tenant_id=str(cfg.tenant_id),
                    error=str(exc),
                )
                raise task.retry(exc=exc) from exc
            finally:
                await client.aclose()

            outcome = await _persist_leads(
                leads_raw=leads_raw,
                source=LeadSource.APIFY_MAPS,
                tenant_id=str(cfg.tenant_id),
                search_query=term,
                daily_list_id=list_id,
            )
            total["received"] += outcome.get("received", 0)
            total["inserted"] += outcome.get("inserted", 0)
            total["skipped"] += outcome.get("skipped", 0)

            await _update_rotation_state(
                cfg_id=cfg.id,
                new_combo_index=cfg.maps_combo_index + 1,
                last_list_id=list_id,
            )

            await _log_execution(
                tenant_id=cfg.tenant_id,
                capture_config_id=cfg.id,
                source="google_maps",
                list_id=list_id,
                list_name=list_name,
                combo_label=f"{term} em {location}",
                outcome=outcome,
            )

            logger.info(
                "capture.maps_daily.tenant_done",
                tenant_id=str(cfg.tenant_id),
                term=term,
                location=location,
                list_name=list_name,
                **{k: v for k, v in outcome.items()},
            )
        except Exception as exc:
            if not hasattr(exc, "celery_task_error"):
                logger.error(
                    "capture.maps_daily.tenant_error",
                    tenant_id=str(cfg.tenant_id),
                    error=str(exc),
                )
                await _log_execution(
                    tenant_id=cfg.tenant_id,
                    capture_config_id=cfg.id,
                    source="google_maps",
                    list_id=None,
                    list_name=None,
                    combo_label=None,
                    outcome=None,
                    status="failed",
                    error_message=str(exc),
                )

    logger.info("capture.maps_daily.done", **total)
    return total


# ── Motor de rotação: B2B ─────────────────────────────────────────────


async def _run_apify_linkedin_daily_async(task) -> dict:
    from sqlalchemy import select

    from core.database import WorkerSessionLocal
    from models.capture_schedule import CaptureScheduleConfig
    from models.tenant import Tenant

    async with WorkerSessionLocal() as root_session:
        result = await root_session.execute(
            select(CaptureScheduleConfig)
            .join(Tenant, Tenant.id == CaptureScheduleConfig.tenant_id)
            .where(
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
        cities = cfg.b2b_cities or []
        b2b_locations = cfg.b2b_locations or []

        if not titles or not cities:
            logger.info(
                "capture.linkedin_daily.tenant_skipped",
                tenant_id=str(cfg.tenant_id),
                reason="titles ou cidades não configurados",
            )
            continue

        city_index = cfg.b2b_rotation_index % len(cities)
        city = cities[city_index]

        today_str = datetime.now(UTC).strftime("%d/%m/%y")
        titles_preview = ", ".join(titles[:3])
        list_name = f"B2B {today_str} — {city} | {titles_preview}"[:200]
        list_desc = (
            f"Captura automática B2B | Cidade: {city} | Cargos: {titles_preview} | {today_str}"
        )

        try:
            list_id = await _create_daily_list(
                tenant_id=cfg.tenant_id,
                name=list_name,
                description=list_desc,
            )

            client = ApifyClient()
            try:
                leads_raw = await client.run_b2b_leads(
                    job_titles=titles,
                    locations=b2b_locations or None,
                    cities=[city],
                    max_items=cfg.max_items,
                )
            except Exception as exc:
                logger.error(
                    "capture.linkedin_daily.apify_error",
                    tenant_id=str(cfg.tenant_id),
                    error=str(exc),
                )
                raise task.retry(exc=exc) from exc
            finally:
                await client.aclose()

            search_query = f"{titles_preview} em {city}"
            outcome = await _persist_leads(
                leads_raw=leads_raw,
                source=LeadSource.APIFY_LINKEDIN,
                tenant_id=str(cfg.tenant_id),
                search_query=search_query,
                daily_list_id=list_id,
            )
            total["received"] += outcome.get("received", 0)
            total["inserted"] += outcome.get("inserted", 0)
            total["skipped"] += outcome.get("skipped", 0)

            await _update_b2b_rotation_state(
                cfg_id=cfg.id,
                new_rotation_index=cfg.b2b_rotation_index + 1,
                last_list_id=list_id,
            )

            combo_label = f"{titles_preview} — {city}"
            await _log_execution(
                tenant_id=cfg.tenant_id,
                capture_config_id=cfg.id,
                source="b2b_database",
                list_id=list_id,
                list_name=list_name,
                combo_label=combo_label,
                outcome=outcome,
            )

            logger.info(
                "capture.linkedin_daily.tenant_done",
                tenant_id=str(cfg.tenant_id),
                city=city,
                list_name=list_name,
                **{k: v for k, v in outcome.items()},
            )
        except Exception as exc:
            if not hasattr(exc, "celery_task_error"):
                logger.error(
                    "capture.linkedin_daily.tenant_error",
                    tenant_id=str(cfg.tenant_id),
                    error=str(exc),
                )
                await _log_execution(
                    tenant_id=cfg.tenant_id,
                    capture_config_id=cfg.id,
                    source="b2b_database",
                    list_id=None,
                    list_name=None,
                    combo_label=None,
                    outcome=None,
                    status="failed",
                    error_message=str(exc),
                )

    logger.info("capture.linkedin_daily.done", **total)
    return total


# ── Helpers de banco de dados ─────────────────────────────────────────


async def _log_execution(
    tenant_id: uuid.UUID,
    capture_config_id: uuid.UUID,
    source: str,
    list_id: uuid.UUID | None,
    list_name: str | None,
    combo_label: str | None,
    outcome: dict | None,
    status: str = "success",
    error_message: str | None = None,
) -> None:
    """Registra uma execução de captura no histórico."""
    from core.database import WorkerSessionLocal
    from models.capture_execution_log import CaptureExecutionLog

    async with WorkerSessionLocal() as session:
        log = CaptureExecutionLog(
            tenant_id=tenant_id,
            capture_config_id=capture_config_id,
            source=source,
            list_id=list_id,
            list_name=list_name,
            combo_label=combo_label,
            leads_received=outcome.get("received", 0) if outcome else 0,
            leads_inserted=outcome.get("inserted", 0) if outcome else 0,
            leads_skipped=outcome.get("skipped", 0) if outcome else 0,
            status=status,
            error_message=error_message,
        )
        session.add(log)
        await session.commit()


async def _create_daily_list(
    tenant_id: uuid.UUID,
    name: str,
    description: str,
) -> uuid.UUID:
    """Cria uma LeadList diária para agrupar os leads capturados."""
    from core.database import get_worker_session
    from models.lead_list import LeadList

    created_id: uuid.UUID | None = None

    async for db in get_worker_session(tenant_id):
        lead_list = LeadList(
            tenant_id=tenant_id,
            name=name,
            description=description,
        )
        db.add(lead_list)
        await db.flush()
        created_id = lead_list.id
        await db.commit()

    if created_id is None:
        raise RuntimeError(f"Falha ao criar LeadList para tenant {tenant_id}")
    return created_id


async def _update_rotation_state(
    cfg_id: uuid.UUID,
    new_combo_index: int,
    last_list_id: uuid.UUID,
) -> None:
    """Atualiza maps_combo_index, last_run_at e last_list_id após execução de Maps."""
    from sqlalchemy import update

    from core.database import WorkerSessionLocal
    from models.capture_schedule import CaptureScheduleConfig

    async with WorkerSessionLocal() as session:
        await session.execute(
            update(CaptureScheduleConfig)
            .where(CaptureScheduleConfig.id == cfg_id)
            .values(
                maps_combo_index=new_combo_index,
                last_run_at=datetime.now(UTC),
                last_list_id=last_list_id,
            )
        )
        await session.commit()


async def _update_b2b_rotation_state(
    cfg_id: uuid.UUID,
    new_rotation_index: int,
    last_list_id: uuid.UUID,
) -> None:
    """Atualiza b2b_rotation_index, last_run_at e last_list_id após execução de B2B."""
    from sqlalchemy import update

    from core.database import WorkerSessionLocal
    from models.capture_schedule import CaptureScheduleConfig

    async with WorkerSessionLocal() as session:
        await session.execute(
            update(CaptureScheduleConfig)
            .where(CaptureScheduleConfig.id == cfg_id)
            .values(
                b2b_rotation_index=new_rotation_index,
                last_run_at=datetime.now(UTC),
                last_list_id=last_list_id,
            )
        )
        await session.commit()


# ── Implementações async (tarefas manuais) ────────────────────────────


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
        leads_raw = await client.run_b2b_leads(
            job_titles=titles,
            locations=locations,
            max_items=max_items,
        )
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
    search_query: str | None = None,
    daily_list_id: uuid.UUID | None = None,
) -> dict:
    """
    Persiste a lista de leads brutos no banco.

    Regras de dedup (strict — nunca sobrescreve):
      - Se linkedin_url já existe no tenant → skipa
      - Se website já existe no tenant (e não é None) → skipa
      - Leads sem linkedin_url E sem website → descarta

    Novos leads recebem capture_query e são adicionados à daily_list se fornecida.
    """
    from sqlalchemy import select

    from core.database import WorkerSessionLocal, get_worker_session
    from models.lead import Lead
    from models.lead_list import lead_list_members

    tid = uuid.UUID(tenant_id)
    inserted = 0
    skipped = 0

    # Pré-carrega conjuntos de dedup em lote para evitar N+1 queries
    async with WorkerSessionLocal() as check_session:
        url_result = await check_session.execute(
            select(Lead.linkedin_url).where(
                Lead.tenant_id == tid,
                Lead.linkedin_url.is_not(None),
            )
        )
        existing_urls: set[str] = {row[0] for row in url_result.all()}

        ws_result = await check_session.execute(
            select(Lead.website).where(
                Lead.tenant_id == tid,
                Lead.website.is_not(None),
            )
        )
        existing_websites: set[str] = {row[0] for row in ws_result.all()}

    seen_urls: set[str] = set()
    seen_websites: set[str] = set()

    async for db in get_worker_session(tid):
        for raw in leads_raw:
            # Descarta leads sem identificador usável
            if not raw.linkedin_url and not raw.website:
                skipped += 1
                continue

            # Dedup por linkedin_url
            if raw.linkedin_url:
                if raw.linkedin_url in existing_urls or raw.linkedin_url in seen_urls:
                    skipped += 1
                    continue
                seen_urls.add(raw.linkedin_url)

            # Dedup por website
            if raw.website:
                if raw.website in existing_websites or raw.website in seen_websites:
                    skipped += 1
                    continue
                seen_websites.add(raw.website)

            lead = Lead(
                tenant_id=tid,
                name=raw.name or "Desconhecido",
                company=raw.company,
                website=raw.website,
                linkedin_url=raw.linkedin_url,
                city=raw.city,
                segment=raw.segment,
                phone=raw.phone,
                capture_query=search_query,
                source=source,
                status=LeadStatus.RAW,
            )
            db.add(lead)
            await db.flush()

            # Associa à lista diária
            if daily_list_id is not None:
                await db.execute(
                    lead_list_members.insert().values(
                        lead_list_id=daily_list_id,
                        lead_id=lead.id,
                    )
                )

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
