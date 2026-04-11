from __future__ import annotations

from integrations.apify_client import ApifyLeadRaw, apify_client
from models.enums import LeadSource
from schemas.lead import LeadGeneratedPreviewItem, LeadGenerationPreviewRequest
from services.lead_management import candidate_origin_label


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
        raw_items = await apify_client.run_linkedin_enrichment(
            linkedin_urls=body.linkedin_urls or [],
            max_items=body.limit,
        )
        source = LeadSource.APIFY_LINKEDIN

    return [
        _normalize_preview_item(item, body.source, source, index)
        for index, item in enumerate(raw_items, start=1)
        if item.name
    ]


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
