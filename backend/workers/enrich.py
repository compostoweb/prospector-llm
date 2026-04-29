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
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlparse

import structlog
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from core.config import settings
from integrations.context_fetcher import context_fetcher
from integrations.unipile_client import unipile_client
from models.enums import ContactQualityBucket, EmailType, LeadStatus
from models.lead import Lead
from services.email_finder import EmailFinderService
from services.lead_management import (
    additional_lead_email_specs,
    build_lead_contact_point_specs,
    build_lead_email_specs,
    lead_email_specs_from_lead,
    replace_lead_contact_points,
    replace_lead_email_records,
)
from services.lead_scorer import lead_scorer
from workers.celery_app import celery_app

logger = structlog.get_logger()

_BATCH_SIZE = 50


@dataclass(frozen=True)
class LinkedInCrosscheck:
    profile_id: str | None
    current_company: str | None
    company_match: bool | None


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
    include_mobile: bool = True,
    force_refresh: bool = False,
) -> dict:
    """
    Enriquece um único lead por ID.
    Usado pela API quando um lead é criado com enrich=true.

    Retorna: {"lead_id": lead_id, "status": "enriched"|"failed"}
    """
    return asyncio.run(
        _enrich_single_async(
            lead_id,
            tenant_id,
            self,
            include_mobile=include_mobile,
            force_refresh=force_refresh,
        )
    )


async def _enrich_single_async(
    lead_id: str,
    tenant_id: str,
    task,
    *,
    include_mobile: bool,
    force_refresh: bool,
) -> dict:
    from core.database import get_worker_session

    tid = uuid.UUID(tenant_id)
    lid = uuid.UUID(lead_id)
    email_finder = EmailFinderService()

    try:
        async for db in get_worker_session(tid):
            result = await db.execute(
                select(Lead)
                .where(Lead.id == lid, Lead.tenant_id == tid)
                .options(selectinload(Lead.emails), selectinload(Lead.contact_points))  # type: ignore[arg-type]
            )
            lead = result.scalar_one_or_none()
            if lead is None:
                logger.warning("enrich.single_not_found", lead_id=lead_id)
                return {"lead_id": lead_id, "status": "not_found"}

            try:
                await _enrich_lead(
                    db,
                    lead,
                    email_finder,
                    include_mobile=include_mobile,
                    force_refresh=force_refresh,
                )
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
                .options(selectinload(Lead.emails), selectinload(Lead.contact_points))  # type: ignore[arg-type]
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
                    await _enrich_lead(
                        db,
                        lead,
                        email_finder,
                        include_mobile=True,
                        force_refresh=False,
                    )
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


async def _enrich_lead(
    db,
    lead: Lead,
    email_finder: EmailFinderService,
    *,
    include_mobile: bool,
    force_refresh: bool,
) -> None:
    """
    Executa o pipeline de enriquecimento para um único lead.
    Todas as falhas individuais são toleradas (não relança exceção).
    """
    # ── 1. Descoberta de e-mail ───────────────────────────────────────
    domain = _extract_domain(lead.website) if lead.website else None
    first_name, last_name = _split_name(lead.name)
    linkedin_crosscheck = await _resolve_linkedin_crosscheck(lead)
    prospeo_enrichment = await email_finder.enrich_person(
        first_name,
        last_name,
        domain,
        include_mobile=include_mobile,
    )

    email_result = await email_finder.find(
        first_name=first_name,
        last_name=last_name,
        domain=domain,
        linkedin_url=lead.linkedin_url,
        existing_email=None if force_refresh else lead.email_corporate,
        prospeo_enrichment=prospeo_enrichment,
    )

    if email_result and linkedin_crosscheck is not None:
        email_result = email_finder.apply_linkedin_company_signal(
            email_result,
            company_match=linkedin_crosscheck.company_match,
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

    phone_source: str | None = None
    phone_verified = False
    phone_verification_status: str | None = None
    phone_quality_score: float | None = None
    phone_quality_bucket: ContactQualityBucket | None = None
    phone_evidence: dict[str, object] | None = None

    if prospeo_enrichment and prospeo_enrichment.mobile:
        (
            phone_quality_score,
            phone_quality_bucket,
            phone_verified,
        ) = _assess_phone_quality(prospeo_enrichment.mobile_status)
        phone_source = "prospeo"
        phone_verification_status = prospeo_enrichment.mobile_status
        phone_evidence = {
            "provider": "prospeo",
            "mobile_status": prospeo_enrichment.mobile_status,
            "linkedin_company_match": (
                linkedin_crosscheck.company_match if linkedin_crosscheck is not None else None
            ),
        }
        if not lead.phone or phone_verified:
            lead.phone = prospeo_enrichment.mobile

    await replace_lead_email_records(
        db,
        lead=lead,
        specs=build_lead_email_specs(
            email_corporate=lead.email_corporate,
            email_corporate_source=lead.email_corporate_source,
            email_corporate_verified=lead.email_corporate_verified,
            email_corporate_verification_status=(
                email_result.verification_status
                if email_result and email_result.email_type == EmailType.CORPORATE
                else None
            ),
            email_corporate_quality_score=(
                email_result.quality_score
                if email_result and email_result.email_type == EmailType.CORPORATE
                else None
            ),
            email_corporate_quality_bucket=(
                email_result.quality_bucket
                if email_result and email_result.email_type == EmailType.CORPORATE
                else None
            ),
            email_personal=lead.email_personal,
            email_personal_source=lead.email_personal_source,
            email_personal_verification_status=(
                email_result.verification_status
                if email_result and email_result.email_type == EmailType.PERSONAL
                else None
            ),
            email_personal_quality_score=(
                email_result.quality_score
                if email_result and email_result.email_type == EmailType.PERSONAL
                else None
            ),
            email_personal_quality_bucket=(
                email_result.quality_bucket
                if email_result and email_result.email_type == EmailType.PERSONAL
                else None
            ),
            extra_emails=additional_lead_email_specs(lead),
        ),
    )
    email_evidence_by_value: dict[str, dict[str, object] | None] = {}
    if email_result:
        email_evidence_by_value[email_result.email] = {
            "provider": email_result.source,
            "finder_confidence": email_result.confidence,
            "linkedin_company_match": (
                linkedin_crosscheck.company_match if linkedin_crosscheck is not None else None
            ),
            "linkedin_profile_id": (
                linkedin_crosscheck.profile_id if linkedin_crosscheck is not None else None
            ),
        }

    await replace_lead_contact_points(
        db,
        lead=lead,
        specs=build_lead_contact_point_specs(
            email_specs=lead_email_specs_from_lead(lead),
            email_evidence_by_value=email_evidence_by_value,
            phone=lead.phone,
            phone_source=phone_source,
            phone_verified=phone_verified,
            phone_verification_status=phone_verification_status,
            phone_quality_score=phone_quality_score,
            phone_quality_bucket=phone_quality_bucket,
            phone_evidence_json=phone_evidence,
            phone_metadata_json=(
                {"linkedin_profile_id": linkedin_crosscheck.profile_id}
                if linkedin_crosscheck is not None and linkedin_crosscheck.profile_id
                else None
            ),
        ),
    )

    # ── 2. Contexto do website (pré-aquece cache para o AI Composer) ──
    if lead.website:
        try:
            await context_fetcher.fetch_from_website(lead.website)
        except Exception as exc:  # noqa: BLE001
            logger.warning("enrich.context_failed", lead_id=str(lead.id), error=str(exc))


async def _resolve_linkedin_crosscheck(lead: Lead) -> LinkedInCrosscheck | None:
    account_id = settings.UNIPILE_ACCOUNT_ID_LINKEDIN or ""
    if not account_id or (not lead.linkedin_url and not lead.linkedin_profile_id):
        return None

    original_company = lead.company
    current_company: str | None = None
    profile_id = lead.linkedin_profile_id

    if lead.linkedin_url:
        try:
            profile = await unipile_client.get_linkedin_profile(account_id, lead.linkedin_url)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "enrich.linkedin_profile_failed",
                lead_id=str(lead.id),
                error=str(exc),
            )
            profile = None

        if profile is not None:
            profile_id = profile.profile_id or profile_id
            current_company = profile.company or current_company

    if profile_id and not current_company:
        try:
            current_company = await unipile_client.fetch_profile_company(account_id, profile_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "enrich.linkedin_company_failed",
                lead_id=str(lead.id),
                linkedin_profile_id=profile_id,
                error=str(exc),
            )

    if profile_id:
        lead.linkedin_profile_id = profile_id
    if not original_company and current_company:
        lead.company = current_company

    company_match = _companies_match(original_company, current_company)
    lead.linkedin_current_company = current_company
    lead.linkedin_checked_at = datetime.now(tz=UTC)
    lead.linkedin_mismatch = False if company_match is None else (not company_match)
    if current_company:
        logger.info(
            "enrich.linkedin_crosscheck",
            lead_id=str(lead.id),
            linkedin_profile_id=profile_id,
            current_company=current_company,
            company_match=company_match,
        )
    return LinkedInCrosscheck(
        profile_id=profile_id,
        current_company=current_company,
        company_match=company_match,
    )


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


def _companies_match(left: str | None, right: str | None) -> bool | None:
    left_token = _company_token(left)
    right_token = _company_token(right)
    if not left_token or not right_token:
        return None
    return left_token in right_token or right_token in left_token


def _company_token(value: str | None) -> str:
    return " ".join((value or "").strip().lower().split())


def _assess_phone_quality(status: str | None) -> tuple[float, ContactQualityBucket, bool]:
    normalized = (status or "").strip().upper()
    if normalized in {"VERIFIED", "VALID"}:
        return 0.95, ContactQualityBucket.GREEN, True
    if normalized in {"FOUND", "UNKNOWN", "UNVERIFIED", "LIKELY"}:
        return 0.55, ContactQualityBucket.ORANGE, False
    return 0.0, ContactQualityBucket.RED, False
