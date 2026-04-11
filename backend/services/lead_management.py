from __future__ import annotations

import uuid
from collections.abc import Iterable

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.cadence_step import CadenceStep
from models.content_calculator_result import ContentCalculatorResult
from models.content_lm_lead import ContentLMLead
from models.enums import LeadSource, LeadStatus
from models.interaction import Interaction
from models.lead import Lead
from models.lead_list import LeadList, lead_list_members
from models.lead_tag import LeadTag
from models.manual_task import ManualTask
from models.sandbox import SandboxStep
from schemas.lead import LeadGeneratedPreviewItem, LeadListSummary, LeadResponse

STATUS_RANK: dict[LeadStatus, int] = {
    LeadStatus.ARCHIVED: 0,
    LeadStatus.RAW: 1,
    LeadStatus.ENRICHED: 2,
    LeadStatus.IN_CADENCE: 3,
    LeadStatus.CONVERTED: 4,
}


def infer_lead_origin(lead: Lead) -> tuple[str, str, str | None]:
    note_detail = _extract_origin_note(lead.notes)
    sources = {lead.email_corporate_source, lead.email_personal_source}

    if "lead_magnet" in sources or _note_mentions(lead.notes, "Origem inbound:"):
        return "lead_magnet", "Lead magnet do Content Hub", note_detail
    if "apify_b2b_database" in sources or _note_mentions(lead.notes, "Base B2B (Apify)"):
        return "apify_b2b_database", "Base B2B via Apify", note_detail
    if "apify_linkedin_enrichment" in sources or _note_mentions(
        lead.notes, "Enriquecimento LinkedIn"
    ):
        return "apify_linkedin_enrichment", "Enriquecimento LinkedIn (Apify)", note_detail

    if lead.source == LeadSource.APIFY_MAPS:
        return "apify_maps", "Google Maps (Apify)", note_detail
    if lead.source == LeadSource.APIFY_LINKEDIN:
        return "apify_linkedin", "Apify LinkedIn", note_detail
    if lead.source == LeadSource.LINKEDIN_SEARCH:
        return "linkedin_search", "Busca LinkedIn", note_detail
    if lead.source == LeadSource.IMPORT:
        return "import", "Importação", note_detail
    if lead.source == LeadSource.API:
        return "internal_api", "Ferramenta interna/API", note_detail
    return "manual", "Manual", note_detail


def serialize_lead(lead: Lead) -> LeadResponse:
    base = LeadResponse.model_validate(lead).model_dump()
    origin_key, origin_label, origin_detail = infer_lead_origin(lead)
    lead_lists = lead.lists or []
    return LeadResponse(
        **base,
        lead_lists=[
            LeadListSummary(id=lead_list.id, name=lead_list.name) for lead_list in lead_lists
        ],
        origin_key=origin_key,
        origin_label=origin_label,
        origin_detail=origin_detail,
    )


async def get_lead_with_lists(
    lead_id: uuid.UUID,
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> Lead | None:
    result = await db.execute(
        select(Lead)
        .where(Lead.id == lead_id, Lead.tenant_id == tenant_id)
        .options(selectinload(Lead.lists))  # type: ignore[arg-type]
    )
    return result.scalar_one_or_none()


async def find_existing_lead(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    item: LeadGeneratedPreviewItem,
) -> Lead | None:
    lookups: list[tuple[str, str | None]] = [
        ("linkedin_profile_id", item.linkedin_profile_id),
        ("linkedin_url", item.linkedin_url),
        ("email_corporate", item.email_corporate),
        ("email_personal", item.email_personal),
        ("phone", item.phone),
    ]

    for field_name, value in lookups:
        if not value:
            continue
        result = await db.execute(
            select(Lead)
            .where(getattr(Lead, field_name) == value, Lead.tenant_id == tenant_id)
            .options(selectinload(Lead.lists))  # type: ignore[arg-type]
            .limit(1)
        )
        lead = result.scalar_one_or_none()
        if lead is not None:
            return lead
    return None


async def ensure_list_membership(
    db: AsyncSession,
    *,
    lead_id: uuid.UUID,
    list_id: uuid.UUID | None,
) -> None:
    if list_id is None:
        return
    await db.execute(
        pg_insert(lead_list_members)
        .values(lead_list_id=list_id, lead_id=lead_id)
        .on_conflict_do_nothing()
    )


async def get_or_create_list(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    list_id: uuid.UUID | None,
    create_list_name: str | None,
) -> LeadList | None:
    if list_id is not None:
        result = await db.execute(
            select(LeadList).where(LeadList.id == list_id, LeadList.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    if not create_list_name or not create_list_name.strip():
        return None

    lead_list = LeadList(tenant_id=tenant_id, name=create_list_name.strip())
    db.add(lead_list)
    await db.flush()
    return lead_list


async def merge_leads(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    primary_lead_id: uuid.UUID,
    secondary_lead_ids: Iterable[uuid.UUID],
) -> Lead:
    secondary_ids = list(dict.fromkeys(secondary_lead_ids))
    target_ids = [primary_lead_id, *secondary_ids]
    result = await db.execute(
        select(Lead)
        .where(Lead.tenant_id == tenant_id, Lead.id.in_(target_ids))
        .options(selectinload(Lead.lists))  # type: ignore[arg-type]
    )
    leads = result.scalars().all()
    lead_map = {lead.id: lead for lead in leads}
    primary = lead_map[primary_lead_id]
    secondary_leads = [lead_map[lead_id] for lead_id in secondary_ids if lead_id in lead_map]

    for secondary in secondary_leads:
        _merge_lead_fields(primary, secondary)

    await _merge_memberships(db, primary.id, secondary_leads)
    await _merge_tags(db, tenant_id, primary.id, secondary_ids)

    await db.execute(
        update(Interaction)
        .where(Interaction.tenant_id == tenant_id, Interaction.lead_id.in_(secondary_ids))
        .values(lead_id=primary.id)
    )
    await db.execute(
        update(CadenceStep)
        .where(CadenceStep.tenant_id == tenant_id, CadenceStep.lead_id.in_(secondary_ids))
        .values(lead_id=primary.id)
    )
    await db.execute(
        update(ManualTask)
        .where(ManualTask.tenant_id == tenant_id, ManualTask.lead_id.in_(secondary_ids))
        .values(lead_id=primary.id)
    )
    await db.execute(
        update(SandboxStep)
        .where(SandboxStep.tenant_id == tenant_id, SandboxStep.lead_id.in_(secondary_ids))
        .values(lead_id=primary.id)
    )
    await db.execute(
        update(ContentLMLead)
        .where(ContentLMLead.tenant_id == tenant_id, ContentLMLead.lead_id.in_(secondary_ids))
        .values(lead_id=primary.id)
    )
    await db.execute(
        update(ContentCalculatorResult)
        .where(
            ContentCalculatorResult.tenant_id == tenant_id,
            ContentCalculatorResult.lead_id.in_(secondary_ids),
        )
        .values(lead_id=primary.id)
    )

    for secondary in secondary_leads:
        await db.delete(secondary)

    await db.commit()
    refreshed = await get_lead_with_lists(primary.id, tenant_id, db)
    if refreshed is None:
        raise RuntimeError("Lead principal não encontrado após merge.")
    return refreshed


def candidate_origin_label(source: str) -> str:
    if source == "google_maps":
        return "Google Maps (Apify)"
    if source == "b2b_database":
        return "Base B2B via Apify"
    return "Enriquecimento LinkedIn (Apify)"


def candidate_to_lead_source(source: str) -> LeadSource:
    if source == "google_maps":
        return LeadSource.APIFY_MAPS
    if source == "linkedin_enrichment":
        return LeadSource.APIFY_LINKEDIN
    return LeadSource.API


def apply_candidate_to_lead(
    lead: Lead,
    item: LeadGeneratedPreviewItem,
    *,
    source: str,
    overwrite_missing_only: bool,
) -> None:
    values: dict[str, str | None] = {
        "name": item.name,
        "first_name": item.first_name,
        "last_name": item.last_name,
        "job_title": item.job_title,
        "company": item.company,
        "company_domain": item.company_domain,
        "website": item.website,
        "industry": item.industry,
        "company_size": item.company_size,
        "linkedin_url": item.linkedin_url,
        "linkedin_profile_id": item.linkedin_profile_id,
        "city": item.city,
        "location": item.location,
        "segment": item.segment,
        "phone": item.phone,
        "email_corporate": item.email_corporate,
        "email_personal": item.email_personal,
    }
    for field_name, value in values.items():
        if value in (None, ""):
            continue
        current = getattr(lead, field_name, None)
        if overwrite_missing_only and current not in (None, ""):
            continue
        setattr(lead, field_name, value)

    if item.email_corporate:
        lead.email_corporate_source = _candidate_email_source(source)
    if item.email_personal:
        lead.email_personal_source = _candidate_email_source(source)

    if overwrite_missing_only:
        if lead.source == LeadSource.MANUAL:
            lead.source = candidate_to_lead_source(source)
    else:
        lead.source = candidate_to_lead_source(source)

    lead.notes = _merge_notes(
        lead.notes,
        _build_origin_note(source, item.notes),
    )


async def delete_lead_permanently(
    db: AsyncSession,
    *,
    lead: Lead,
) -> None:
    await db.delete(lead)
    await db.commit()


async def _merge_memberships(
    db: AsyncSession,
    primary_lead_id: uuid.UUID,
    secondary_leads: list[Lead],
) -> None:
    for secondary in secondary_leads:
        for lead_list in secondary.lists or []:
            await db.execute(
                pg_insert(lead_list_members)
                .values(lead_list_id=lead_list.id, lead_id=primary_lead_id)
                .on_conflict_do_nothing()
            )

    secondary_ids = [lead.id for lead in secondary_leads]
    if secondary_ids:
        await db.execute(
            delete(lead_list_members).where(lead_list_members.c.lead_id.in_(secondary_ids))
        )


async def _merge_tags(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    primary_lead_id: uuid.UUID,
    secondary_ids: list[uuid.UUID],
) -> None:
    if not secondary_ids:
        return

    primary_tags_result = await db.execute(
        select(LeadTag).where(LeadTag.tenant_id == tenant_id, LeadTag.lead_id == primary_lead_id)
    )
    existing_names = {tag.name.casefold() for tag in primary_tags_result.scalars().all()}
    secondary_tags_result = await db.execute(
        select(LeadTag).where(LeadTag.tenant_id == tenant_id, LeadTag.lead_id.in_(secondary_ids))
    )

    for tag in secondary_tags_result.scalars().all():
        tag_name = tag.name.casefold()
        if tag_name in existing_names:
            await db.delete(tag)
            continue
        tag.lead_id = primary_lead_id
        existing_names.add(tag_name)


def _merge_lead_fields(primary: Lead, secondary: Lead) -> None:
    fill_fields = [
        "first_name",
        "last_name",
        "job_title",
        "company",
        "company_domain",
        "website",
        "industry",
        "company_size",
        "linkedin_url",
        "linkedin_profile_id",
        "linkedin_connection_status",
        "linkedin_connected_at",
        "city",
        "location",
        "segment",
        "email_corporate",
        "email_corporate_source",
        "email_personal",
        "email_personal_source",
        "phone",
        "enriched_at",
        "timezone",
        "linkedin_recent_posts_json",
        "llm_icp_reasoning",
        "llm_personalization_notes",
        "llm_analyzed_at",
    ]
    for field_name in fill_fields:
        if getattr(primary, field_name) in (None, "") and getattr(secondary, field_name) not in (
            None,
            "",
        ):
            setattr(primary, field_name, getattr(secondary, field_name))

    if primary.score is None or (secondary.score is not None and secondary.score > primary.score):
        primary.score = secondary.score
    if secondary.llm_icp_score is not None and (
        primary.llm_icp_score is None or secondary.llm_icp_score > primary.llm_icp_score
    ):
        primary.llm_icp_score = secondary.llm_icp_score
    if secondary.email_corporate_verified:
        primary.email_corporate_verified = True
    if STATUS_RANK.get(secondary.status, 0) > STATUS_RANK.get(primary.status, 0):
        primary.status = secondary.status
    primary.notes = _merge_notes(primary.notes, secondary.notes)


def _candidate_email_source(source: str) -> str:
    if source == "b2b_database":
        return "apify_b2b_database"
    if source == "linkedin_enrichment":
        return "apify_linkedin_enrichment"
    return "apify_maps"


def _build_origin_note(source: str, notes: str | None) -> str:
    label = candidate_origin_label(source)
    parts = [f"Origem sistema: {label}"]
    if notes:
        parts.append(notes.strip())
    return "\n".join(part for part in parts if part)


def _merge_notes(current: str | None, incoming: str | None) -> str | None:
    current_text = (current or "").strip()
    incoming_text = (incoming or "").strip()
    if not incoming_text:
        return current_text or None
    if not current_text:
        return incoming_text
    if incoming_text in current_text:
        return current_text
    return f"{current_text}\n\n{incoming_text}"


def _extract_origin_note(notes: str | None) -> str | None:
    if not notes:
        return None
    for line in notes.splitlines():
        normalized = line.strip()
        if normalized.startswith("Origem inbound:"):
            return normalized.replace("Origem inbound:", "", 1).strip() or None
        if normalized.startswith("Origem sistema:"):
            return normalized.replace("Origem sistema:", "", 1).strip() or None
    return None


def _note_mentions(notes: str | None, text: str) -> bool:
    return bool(notes and text.lower() in notes.lower())
