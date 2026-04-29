from __future__ import annotations

import asyncio

import structlog

from core.config import settings
from integrations.apify_client import ApifyLeadRaw, apify_client
from integrations.unipile_client import unipile_client
from models.enums import ContactQualityBucket, LeadSource
from schemas.lead import LeadGeneratedPreviewItem, LeadGenerationPreviewRequest
from services.lead_management import candidate_origin_label

logger = structlog.get_logger()


async def preview_generated_leads(
    body: LeadGenerationPreviewRequest,
) -> list[LeadGeneratedPreviewItem]:
    if body.source == "google_maps":
        queries = body.search_terms or []
        if not queries and body.location_query:
            queries = [body.location_query]
        raw_items = await apify_client.run_google_maps(
            search_queries=queries,
            location_query=body.location_query,
            categories=body.categories,
            max_items=body.limit,
        )
        source = LeadSource.APIFY_MAPS
    elif body.source == "b2b_database":
        raw_items = await apify_client.run_b2b_leads(
            actor_key=body.b2b_actor_key,
            job_titles=body.job_titles,
            locations=body.locations,
            cities=body.cities,
            industries=body.industries,
            company_keywords=body.company_keywords,
            company_sizes=body.company_sizes,
            email_status=body.email_status,
            max_items=body.limit,
        )
        source = LeadSource.API
    else:
        # Trunca antes de enviar ao Apify — evitar cobranças por URLs extras
        truncated_urls = (body.linkedin_urls or [])[: body.limit]
        raw_items = await apify_client.run_linkedin_enrichment(
            linkedin_urls=truncated_urls,
            max_items=body.limit,
        )
        source = LeadSource.APIFY_LINKEDIN

    logger.debug("lead_generation.raw_items", source=body.source, count=len(raw_items))
    if raw_items and body.source == "b2b_database":
        # Log do primeiro item para diagnosticar campos retornados pelo ator
        logger.debug("lead_generation.b2b_sample", fields=list(raw_items[0].extra.keys())[:30])

    items = [
        _normalize_preview_item(item, body.source, source, index)
        for index, item in enumerate(raw_items, start=1)
        if item.name or item.email_corporate or item.email_personal or item.linkedin_url
    ]

    discarded = len(raw_items) - len(items)
    if discarded:
        logger.warning(
            "lead_generation.items_discarded",
            source=body.source,
            discarded=discarded,
            reason="no_identifiers",
        )

    if body.negative_terms:
        items = _apply_negative_filter(items, body.negative_terms)

    if body.source == "b2b_database":
        items = _apply_same_role_company_limit(items, max_per_role=2)

    if body.source == "b2b_database" and body.verify_linkedin:
        items = await _verify_linkedin_positions(items)

    items = [_apply_preview_quality(item) for item in items]

    return items


def _apply_negative_filter(
    items: list[LeadGeneratedPreviewItem],
    negative_terms: list[str],
) -> list[LeadGeneratedPreviewItem]:
    """Descarta leads cujo cargo ou company_keywords contenha algum termo negativo (case-insensitive)."""
    terms_lower = [t.strip().lower() for t in negative_terms if t.strip()]
    if not terms_lower:
        return items

    def _matches_any(value: str | None) -> bool:
        if not value:
            return False
        v = value.lower()
        return any(term in v for term in terms_lower)

    return [
        item for item in items if not (_matches_any(item.job_title) or _matches_any(item.company))
    ]


def _apply_same_role_company_limit(
    items: list[LeadGeneratedPreviewItem],
    max_per_role: int = 2,
) -> list[LeadGeneratedPreviewItem]:
    """Limita a no máximo `max_per_role` pessoas com o mesmo cargo na mesma empresa."""
    from collections import defaultdict

    counts: dict[tuple[str, str], int] = defaultdict(int)
    result: list[LeadGeneratedPreviewItem] = []
    for item in items:
        company_key = (item.company or "").strip().lower()
        role_key = (item.job_title or "").strip().lower()
        key = (company_key, role_key)
        if counts[key] < max_per_role:
            counts[key] += 1
            result.append(item)
    discarded = len(items) - len(result)
    if discarded:
        logger.debug(
            "lead_generation.same_role_company_limit",
            discarded=discarded,
            max_per_role=max_per_role,
        )
    return result


def _normalize_preview_item(
    item: ApifyLeadRaw,
    source_key: str,
    source: LeadSource,
    index: int,
) -> LeadGeneratedPreviewItem:
    return LeadGeneratedPreviewItem(
        preview_id=f"{source_key}:{index}",
        name=item.name,
        first_name=item.first_name,
        last_name=item.last_name,
        job_title=item.job_title,
        company=item.company,
        company_domain=item.company_domain,
        website=item.website,
        industry=item.industry,
        company_size=item.company_size,
        linkedin_url=item.linkedin_url,
        linkedin_profile_id=item.linkedin_profile_id,
        city=item.city,
        location=item.location or item.city,
        segment=item.segment,
        phone=item.phone,
        email_corporate=item.email_corporate,
        email_personal=item.email_personal,
        notes=item.notes,
        source=source,
        origin_key=source_key,
        origin_label=candidate_origin_label(source_key),
    )


def _apply_preview_quality(item: LeadGeneratedPreviewItem) -> LeadGeneratedPreviewItem:
    quality_bucket, quality_score = _score_preview_contact_quality(item)
    return item.model_copy(
        update={
            "quality_bucket": quality_bucket,
            "quality_score": quality_score,
        }
    )


def _score_preview_contact_quality(
    item: LeadGeneratedPreviewItem,
) -> tuple[ContactQualityBucket | None, float | None]:
    has_corporate_email = bool(item.email_corporate)
    has_personal_email = bool(item.email_personal)
    has_phone = bool(item.phone)

    if not has_corporate_email and not has_personal_email and not has_phone:
        return None, None

    if item.li_outdated and (has_corporate_email or has_personal_email):
        return ContactQualityBucket.RED, 0.20

    if has_corporate_email and item.li_verified:
        return ContactQualityBucket.GREEN, 0.85

    if has_corporate_email:
        return ContactQualityBucket.ORANGE, 0.65

    if has_personal_email and item.li_verified:
        return ContactQualityBucket.ORANGE, 0.55

    if has_personal_email:
        return ContactQualityBucket.ORANGE, 0.50

    return ContactQualityBucket.ORANGE, 0.45


async def _verify_linkedin_positions(
    items: list[LeadGeneratedPreviewItem],
) -> list[LeadGeneratedPreviewItem]:
    """
    Verifica cargo e empresa atuais dos leads via Unipile (LinkedIn profile scrape).
    Usa a conta LinkedIn configurada em UNIPILE_ACCOUNT_ID_LINKEDIN.
    Dispara até 5 requests simultâneos para não sobrecarregar o rate limit.
    """
    account_id = settings.UNIPILE_ACCOUNT_ID_LINKEDIN
    if not account_id:
        logger.warning(
            "lead_generation.linkedin_verify.skipped",
            reason="UNIPILE_ACCOUNT_ID_LINKEDIN not configured",
        )
        return items

    leads_with_url = [(i, item) for i, item in enumerate(items) if item.linkedin_url]
    if not leads_with_url:
        return items

    logger.info("lead_generation.linkedin_verify.start", total_urls=len(leads_with_url))

    # Semáforo: máximo 5 chamadas Unipile simultâneas
    sem = asyncio.Semaphore(5)

    async def _fetch_one(linkedin_url: str) -> tuple[str | None, str | None]:
        """Retorna (headline, current_company) ou (None, None) em caso de erro."""
        async with sem:
            try:
                profile = await unipile_client.get_linkedin_profile(
                    account_id=account_id,
                    linkedin_url=linkedin_url,
                )
                if profile is None:
                    return None, None
                return profile.headline, profile.company
            except Exception as exc:
                logger.debug(
                    "lead_generation.linkedin_verify.fetch_failed",
                    url=linkedin_url,
                    error=str(exc),
                )
                return None, None

    # Dispara todos em paralelo (limitado pelo semáforo)
    tasks = [_fetch_one(item.linkedin_url) for _, item in leads_with_url]  # type: ignore[arg-type]
    results = await asyncio.gather(*tasks)

    verified_count = sum(1 for h, _ in results if h is not None)
    logger.info("lead_generation.linkedin_verify.done", verified=verified_count)

    def _token(v: str | None) -> str:
        return (v or "").strip().lower()

    def _titles_differ(stored: str | None, current: str | None) -> bool:
        if not stored or not current:
            return False
        s, c = _token(stored), _token(current)
        # Não marca como desatualizado se um contém o outro (headline do LinkedIn
        # costuma ser frase longa que inclui o cargo curto do pipelinelabs)
        return s not in c and c not in s

    # Monta resultado final
    result = list(items)
    for (idx, item), (current_title, current_company) in zip(leads_with_url, results):
        if current_title is None and current_company is None:
            continue  # scrape falhou — mantém item original sem li_verified

        title_changed = _titles_differ(item.job_title, current_title)
        company_changed = bool(current_company) and _token(current_company) != _token(item.company)

        result[idx] = item.model_copy(
            update={
                "li_verified": True,
                "li_current_title": current_title,
                "li_current_company": current_company,
                "li_outdated": title_changed or company_changed,
            }
        )

    return result
