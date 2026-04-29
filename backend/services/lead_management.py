from __future__ import annotations

import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, NotRequired, TypedDict

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.cadence import Cadence
from models.cadence_step import CadenceStep
from models.content_calculator_result import ContentCalculatorResult
from models.content_lm_lead import ContentLMLead
from models.enums import (
    ContactPointKind,
    ContactQualityBucket,
    EmailType,
    EmailVerificationStatus,
    LeadSource,
    LeadStatus,
    StepStatus,
)
from models.interaction import Interaction
from models.lead import Lead
from models.lead_contact_point import LeadContactPoint
from models.lead_email import LeadEmail
from models.lead_list import LeadList, lead_list_members
from models.lead_tag import LeadTag
from models.manual_task import ManualTask
from models.sandbox import SandboxStep
from schemas.lead import (
    LeadActiveCadenceSummary,
    LeadContactPointResponse,
    LeadEmailInput,
    LeadEmailResponse,
    LeadGeneratedPreviewItem,
    LeadListSummary,
    LeadResponse,
)

STATUS_RANK: dict[LeadStatus, int] = {
    LeadStatus.ARCHIVED: 0,
    LeadStatus.RAW: 1,
    LeadStatus.ENRICHED: 2,
    LeadStatus.IN_CADENCE: 3,
    LeadStatus.CONVERTED: 4,
}

_ACTIVE_CADENCE_STEP_STATUSES = (
    StepStatus.PENDING,
    StepStatus.DISPATCHING,
    StepStatus.SENT,
)


@dataclass(frozen=True, slots=True)
class ActiveCadenceInfo:
    id: uuid.UUID
    name: str


class LeadEmailSpec(TypedDict):
    email: str
    email_type: EmailType
    source: str | None
    verified: bool
    verification_status: NotRequired[EmailVerificationStatus | None]
    quality_score: NotRequired[float | None]
    quality_bucket: NotRequired[ContactQualityBucket | None]
    is_primary: bool


class LeadContactPointSpec(TypedDict):
    kind: ContactPointKind
    value: str
    normalized_value: str
    source: str | None
    verified: bool
    verification_status: NotRequired[str | None]
    quality_score: NotRequired[float | None]
    quality_bucket: NotRequired[ContactQualityBucket | None]
    evidence_json: NotRequired[dict[str, object] | None]
    metadata_json: NotRequired[dict[str, object] | None]
    is_primary: bool


def infer_lead_origin(lead: Lead) -> tuple[str, str, str | None]:
    note_detail = _extract_origin_note(lead.notes)
    sources = {
        lead.email_corporate_source,
        lead.email_personal_source,
        *(email.source for email in lead.emails or []),
        *(point.source for point in lead.contact_points or []),
    }

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


def serialize_lead(
    lead: Lead,
    *,
    active_cadences_by_lead: dict[uuid.UUID, list[ActiveCadenceInfo]] | None = None,
) -> LeadResponse:
    base = LeadResponse.model_validate(lead).model_dump()
    origin_key, origin_label, origin_detail = infer_lead_origin(lead)
    lead_lists = lead.lists or []
    lead_emails = sorted(
        lead.emails or [],
        key=lambda item: (not item.is_primary, item.email_type.value, item.email),
    )
    lead_contact_points = sorted(
        lead.contact_points or [],
        key=lambda item: (not item.is_primary, item.kind.value, item.value.casefold()),
    )
    active_cadences = (active_cadences_by_lead or {}).get(lead.id, [])
    base["lead_lists"] = [LeadListSummary(id=ll.id, name=ll.name) for ll in lead_lists]
    base["emails"] = [LeadEmailResponse.model_validate(email) for email in lead_emails]
    base["contact_points"] = [
        LeadContactPointResponse.model_validate(point) for point in lead_contact_points
    ]
    base["origin_key"] = origin_key
    base["origin_label"] = origin_label
    base["origin_detail"] = origin_detail
    base["active_cadence_count"] = len(active_cadences)
    base["active_cadences"] = [
        LeadActiveCadenceSummary(id=item.id, name=item.name) for item in active_cadences
    ]
    base["has_multiple_active_cadences"] = len(active_cadences) > 1
    return LeadResponse(**base)


async def load_active_cadences_for_leads(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    lead_ids: Iterable[uuid.UUID],
) -> dict[uuid.UUID, list[ActiveCadenceInfo]]:
    ordered_lead_ids = list(dict.fromkeys(lead_ids))
    if not ordered_lead_ids:
        return {}

    result = await db.execute(
        select(CadenceStep.lead_id, Cadence.id, Cadence.name)
        .join(Cadence, Cadence.id == CadenceStep.cadence_id)
        .where(
            CadenceStep.tenant_id == tenant_id,
            CadenceStep.lead_id.in_(ordered_lead_ids),
            CadenceStep.status.in_(_ACTIVE_CADENCE_STEP_STATUSES),
            Cadence.is_active.is_(True),
        )
        .distinct()
        .order_by(CadenceStep.lead_id, Cadence.name)
    )

    mapped: dict[uuid.UUID, list[ActiveCadenceInfo]] = {lead_id: [] for lead_id in ordered_lead_ids}
    for lead_id, cadence_id, cadence_name in result.all():
        mapped.setdefault(lead_id, []).append(ActiveCadenceInfo(id=cadence_id, name=cadence_name))

    return mapped


async def get_lead_with_lists(
    lead_id: uuid.UUID,
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> Lead | None:
    result = await db.execute(
        select(Lead)
        .where(Lead.id == lead_id, Lead.tenant_id == tenant_id)
        .execution_options(populate_existing=True)
        .options(
            selectinload(Lead.lists),
            selectinload(Lead.emails),
            selectinload(Lead.contact_points),
        )  # type: ignore[arg-type]
    )
    return result.scalar_one_or_none()


async def reload_lead_for_output(db: AsyncSession, *, lead: Lead) -> Lead:
    refreshed = await get_lead_with_lists(lead.id, lead.tenant_id, db)
    if refreshed is None:
        raise RuntimeError(f"Lead {lead.id} não encontrado após recarga para output.")
    return refreshed


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
            .execution_options(populate_existing=True)
            .options(
                selectinload(Lead.lists),
                selectinload(Lead.emails),
                selectinload(Lead.contact_points),
            )  # type: ignore[arg-type]
            .limit(1)
        )
        lead = result.scalar_one_or_none()
        if lead is not None:
            return lead

    email_values = [value.strip().lower() for _, value in lookups if value and "@" in value]
    for email in dict.fromkeys(email_values):
        result = await db.execute(
            select(Lead)
            .join(LeadEmail, LeadEmail.lead_id == Lead.id)
            .where(
                Lead.tenant_id == tenant_id,
                LeadEmail.email == email,
            )
            .execution_options(populate_existing=True)
            .options(
                selectinload(Lead.lists),
                selectinload(Lead.emails),
                selectinload(Lead.contact_points),
            )  # type: ignore[arg-type]
            .limit(1)
        )
        lead = result.scalar_one_or_none()
        if lead is not None:
            return lead
    return None


def lead_email_specs_from_lead(lead: Lead) -> list[LeadEmailSpec]:
    if lead.emails:
        return [
            {
                "email": email.email,
                "email_type": email.email_type,
                "source": email.source,
                "verified": email.verified,
                "verification_status": email.verification_status,
                "quality_score": email.quality_score,
                "quality_bucket": email.quality_bucket,
                "is_primary": email.is_primary,
            }
            for email in lead.emails
        ]

    return build_lead_email_specs(
        email_corporate=lead.email_corporate,
        email_corporate_source=lead.email_corporate_source,
        email_corporate_verified=lead.email_corporate_verified,
        email_personal=lead.email_personal,
        email_personal_source=lead.email_personal_source,
    )


def additional_lead_email_specs(lead: Lead) -> list[LeadEmailSpec]:
    return [spec for spec in lead_email_specs_from_lead(lead) if not spec["is_primary"]]


def build_lead_contact_point_specs(
    *,
    email_specs: Iterable[LeadEmailSpec] | None = None,
    email_evidence_by_value: dict[str, dict[str, object] | None] | None = None,
    phone: str | None = None,
    phone_source: str | None = None,
    phone_verified: bool = False,
    phone_verification_status: str | None = None,
    phone_quality_score: float | None = None,
    phone_quality_bucket: ContactQualityBucket | None = None,
    phone_evidence_json: dict[str, object] | None = None,
    phone_metadata_json: dict[str, object] | None = None,
) -> list[LeadContactPointSpec]:
    specs: list[LeadContactPointSpec] = []
    evidence_lookup = {
        _normalize_email(key): value
        for key, value in (email_evidence_by_value or {}).items()
        if key
    }

    for email_spec in email_specs or []:
        normalized_email = _normalize_email(email_spec.get("email"))
        if not normalized_email:
            continue
        specs.append(
            {
                "kind": ContactPointKind.EMAIL,
                "value": normalized_email,
                "normalized_value": normalized_email,
                "source": email_spec.get("source"),
                "verified": bool(email_spec.get("verified", False)),
                "verification_status": _string_or_none(email_spec.get("verification_status")),
                "quality_score": email_spec.get("quality_score"),
                "quality_bucket": email_spec.get("quality_bucket"),
                "evidence_json": evidence_lookup.get(normalized_email),
                "metadata_json": {
                    "email_type": _email_type_attr(email_spec).value,
                },
                "is_primary": bool(email_spec.get("is_primary", False)),
            }
        )

    normalized_phone = _normalize_phone(phone)
    if normalized_phone and phone:
        specs.append(
            {
                "kind": ContactPointKind.PHONE,
                "value": phone.strip(),
                "normalized_value": normalized_phone,
                "source": phone_source,
                "verified": phone_verified,
                "verification_status": phone_verification_status,
                "quality_score": phone_quality_score,
                "quality_bucket": phone_quality_bucket,
                "evidence_json": phone_evidence_json,
                "metadata_json": phone_metadata_json,
                "is_primary": True,
            }
        )

    return _dedupe_contact_point_specs(specs)


def build_lead_email_specs(
    *,
    email_corporate: str | None = None,
    email_corporate_source: str | None = None,
    email_corporate_verified: bool = False,
    email_corporate_verification_status: EmailVerificationStatus | None = None,
    email_corporate_quality_score: float | None = None,
    email_corporate_quality_bucket: ContactQualityBucket | None = None,
    email_personal: str | None = None,
    email_personal_source: str | None = None,
    email_personal_verification_status: EmailVerificationStatus | None = None,
    email_personal_quality_score: float | None = None,
    email_personal_quality_bucket: ContactQualityBucket | None = None,
    extra_emails: Iterable[LeadEmailInput | LeadEmailSpec | LeadEmail] | None = None,
) -> list[LeadEmailSpec]:
    specs: list[LeadEmailSpec] = []

    corporate_email = _normalize_email(email_corporate)
    if corporate_email:
        specs.append(
            {
                "email": corporate_email,
                "email_type": EmailType.CORPORATE,
                "source": email_corporate_source,
                "verified": email_corporate_verified,
                "verification_status": email_corporate_verification_status,
                "quality_score": email_corporate_quality_score,
                "quality_bucket": email_corporate_quality_bucket,
                "is_primary": True,
            }
        )

    personal_email = _normalize_email(email_personal)
    if personal_email:
        specs.append(
            {
                "email": personal_email,
                "email_type": EmailType.PERSONAL,
                "source": email_personal_source,
                "verified": False,
                "verification_status": email_personal_verification_status,
                "quality_score": email_personal_quality_score,
                "quality_bucket": email_personal_quality_bucket,
                "is_primary": True,
            }
        )

    for item in extra_emails or []:
        email = _normalize_email(_email_attr(item, "email"))
        if not email:
            continue
        specs.append(
            {
                "email": email,
                "email_type": _email_type_attr(item),
                "source": _email_attr(item, "source"),
                "verified": bool(_email_attr(item, "verified", False)),
                "verification_status": _email_verification_status_attr(item),
                "quality_score": _quality_score_attr(item),
                "quality_bucket": _quality_bucket_attr(item),
                "is_primary": bool(_email_attr(item, "is_primary", False)),
            }
        )

    return _dedupe_email_specs(specs)


async def replace_lead_email_records(
    db: AsyncSession,
    *,
    lead: Lead,
    specs: Iterable[LeadEmailSpec],
) -> None:
    normalized_specs = _dedupe_email_specs(list(specs))
    _sync_primary_email_fields(lead, normalized_specs)

    existing_result = await db.execute(
        select(LeadEmail)
        .where(LeadEmail.lead_id == lead.id)
        .execution_options(populate_existing=True)
    )
    existing_records = existing_result.scalars().all()
    existing_by_email = {record.email.casefold(): record for record in existing_records}

    for spec in normalized_specs:
        email_key = spec["email"].casefold()
        record = existing_by_email.pop(email_key, None)
        if record is None:
            db.add(
                LeadEmail(
                    tenant_id=lead.tenant_id,
                    lead_id=lead.id,
                    email=spec["email"],
                    email_type=spec["email_type"],
                    source=spec["source"],
                    verified=spec["verified"],
                    verification_status=spec.get("verification_status"),
                    quality_score=spec.get("quality_score"),
                    quality_bucket=spec.get("quality_bucket"),
                    is_primary=spec["is_primary"],
                )
            )
            continue

        record.tenant_id = lead.tenant_id
        record.lead_id = lead.id
        record.email_type = spec["email_type"]
        record.source = spec["source"]
        record.verified = spec["verified"]
        record.verification_status = spec.get("verification_status")
        record.quality_score = spec.get("quality_score")
        record.quality_bucket = spec.get("quality_bucket")
        record.is_primary = spec["is_primary"]

    for stale_record in existing_by_email.values():
        await db.delete(stale_record)


async def replace_lead_contact_points(
    db: AsyncSession,
    *,
    lead: Lead,
    specs: Iterable[LeadContactPointSpec],
) -> None:
    normalized_specs = _dedupe_contact_point_specs(list(specs))

    existing_result = await db.execute(
        select(LeadContactPoint)
        .where(LeadContactPoint.lead_id == lead.id)
        .execution_options(populate_existing=True)
    )
    existing_records = existing_result.scalars().all()
    existing_by_key = {
        (record.kind.value, record.normalized_value.casefold()): record
        for record in existing_records
    }

    for spec in normalized_specs:
        point_key = (spec["kind"].value, spec["normalized_value"].casefold())
        record = existing_by_key.pop(point_key, None)
        if record is None:
            db.add(
                LeadContactPoint(
                    tenant_id=lead.tenant_id,
                    lead_id=lead.id,
                    kind=spec["kind"],
                    value=spec["value"],
                    normalized_value=spec["normalized_value"],
                    source=spec["source"],
                    verified=spec["verified"],
                    verification_status=spec.get("verification_status"),
                    quality_score=spec.get("quality_score"),
                    quality_bucket=spec.get("quality_bucket"),
                    evidence_json=spec.get("evidence_json"),
                    metadata_json=spec.get("metadata_json"),
                    is_primary=spec["is_primary"],
                )
            )
            continue

        record.tenant_id = lead.tenant_id
        record.lead_id = lead.id
        record.kind = spec["kind"]
        record.value = spec["value"]
        record.normalized_value = spec["normalized_value"]
        record.source = spec["source"]
        record.verified = spec["verified"]
        record.verification_status = spec.get("verification_status")
        record.quality_score = spec.get("quality_score")
        record.quality_bucket = spec.get("quality_bucket")
        record.evidence_json = spec.get("evidence_json")
        record.metadata_json = spec.get("metadata_json")
        record.is_primary = spec["is_primary"]

    for stale_record in existing_by_key.values():
        await db.delete(stale_record)


async def sync_lead_contact_points_from_state(
    db: AsyncSession,
    *,
    lead: Lead,
) -> None:
    await db.flush()
    existing_emails_result = await db.execute(
        select(LeadEmail)
        .where(LeadEmail.lead_id == lead.id)
        .execution_options(populate_existing=True)
    )
    email_records = existing_emails_result.scalars().all()
    email_specs = (
        [
            {
                "email": email.email,
                "email_type": email.email_type,
                "source": email.source,
                "verified": email.verified,
                "verification_status": email.verification_status,
                "quality_score": email.quality_score,
                "quality_bucket": email.quality_bucket,
                "is_primary": email.is_primary,
            }
            for email in email_records
        ]
        if email_records
        else build_lead_email_specs(
            email_corporate=lead.email_corporate,
            email_corporate_source=lead.email_corporate_source,
            email_corporate_verified=lead.email_corporate_verified,
            email_personal=lead.email_personal,
            email_personal_source=lead.email_personal_source,
        )
    )

    await replace_lead_contact_points(
        db,
        lead=lead,
        specs=build_lead_contact_point_specs(
            email_specs=email_specs,
            phone=lead.phone,
        ),
    )


def preferred_lead_email(lead: Lead | None) -> str | None:
    if lead is None:
        return None
    if lead.email_corporate:
        return lead.email_corporate
    if lead.email_personal:
        return lead.email_personal
    for email in lead.emails or []:
        if email.email:
            return email.email
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

    from services.cadence_manager import auto_enroll_linked_cadences_for_list

    await auto_enroll_linked_cadences_for_list(
        db,
        list_id=list_id,
        lead_ids=[lead_id],
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
        .options(
            selectinload(Lead.lists),
            selectinload(Lead.emails),
            selectinload(Lead.contact_points),
        )  # type: ignore[arg-type]
    )
    leads = result.scalars().all()
    lead_map = {lead.id: lead for lead in leads}
    primary = lead_map[primary_lead_id]
    secondary_leads = [lead_map[lead_id] for lead_id in secondary_ids if lead_id in lead_map]

    for secondary in secondary_leads:
        _merge_lead_fields(primary, secondary)

    _merge_lead_email_records(primary, secondary_leads)
    await sync_lead_contact_points_from_state(db, lead=primary)

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
    return await reload_lead_for_output(db, lead=primary)


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


_FIELD_MAX_LEN: dict[str, int] = {
    "name": 300,
    "first_name": 150,
    "last_name": 150,
    "job_title": 200,
    "company": 300,
    "company_domain": 500,
    "website": 500,
    "industry": 200,
    "company_size": 50,
    "linkedin_url": 500,
    "linkedin_profile_id": 200,
    "city": 200,
    "location": 500,
    "segment": 200,
    "phone": 50,
    "email_corporate": 255,
    "email_personal": 255,
}


def _trunc(field_name: str, value: str | None) -> str | None:
    if value is None:
        return None
    limit = _FIELD_MAX_LEN.get(field_name)
    if limit and len(value) > limit:
        return value[:limit]
    return value


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
        setattr(lead, field_name, _trunc(field_name, value))

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


def _merge_lead_email_records(primary: Lead, secondary_leads: list[Lead]) -> None:
    existing = {email.email.casefold(): email for email in primary.emails or []}

    for secondary in secondary_leads:
        for email in secondary.emails or []:
            key = email.email.casefold()
            current = existing.get(key)
            if current is None:
                email.lead_id = primary.id
                email.tenant_id = primary.tenant_id
                existing[key] = email
                continue

            current.verified = current.verified or email.verified
            if current.source in (None, "") and email.source:
                current.source = email.source
            if current.email_type == EmailType.UNKNOWN and email.email_type != EmailType.UNKNOWN:
                current.email_type = email.email_type
            if email.is_primary and email.email_type == current.email_type:
                current.is_primary = True

    _sync_primary_email_fields(primary, lead_email_specs_from_lead(primary))


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


def _normalize_email(value: str | None) -> str | None:
    normalized = (value or "").strip().lower()
    return normalized or None


def _email_attr(
    item: LeadEmailInput | LeadEmailSpec | LeadEmail, field: str, default: Any = None
) -> Any:
    if isinstance(item, dict):
        return item.get(field, default)
    return getattr(item, field, default)


def _email_type_attr(item: LeadEmailInput | LeadEmailSpec | LeadEmail) -> EmailType:
    raw = _email_attr(item, "email_type", EmailType.UNKNOWN)
    if isinstance(raw, EmailType):
        return raw
    try:
        return EmailType(str(raw))
    except ValueError:
        return EmailType.UNKNOWN


def _email_verification_status_attr(
    item: LeadEmailInput | LeadEmailSpec | LeadEmail,
) -> EmailVerificationStatus | None:
    raw = _email_attr(item, "verification_status")
    if raw is None:
        return None
    if isinstance(raw, EmailVerificationStatus):
        return raw
    try:
        return EmailVerificationStatus(str(raw))
    except ValueError:
        return None


def _quality_bucket_attr(
    item: LeadEmailInput | LeadEmailSpec | LeadEmail,
) -> ContactQualityBucket | None:
    raw = _email_attr(item, "quality_bucket")
    if raw is None:
        return None
    if isinstance(raw, ContactQualityBucket):
        return raw
    try:
        return ContactQualityBucket(str(raw))
    except ValueError:
        return None


def _quality_score_attr(item: LeadEmailInput | LeadEmailSpec | LeadEmail) -> float | None:
    raw = _email_attr(item, "quality_score")
    if raw is None:
        return None
    try:
        return max(0.0, min(1.0, float(raw)))
    except (TypeError, ValueError):
        return None


def _string_or_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _dedupe_email_specs(specs: list[LeadEmailSpec]) -> list[LeadEmailSpec]:
    merged: dict[str, LeadEmailSpec] = {}

    for spec in specs:
        email = _normalize_email(spec.get("email"))
        if not email:
            continue
        normalized_spec: LeadEmailSpec = {
            "email": email,
            "email_type": spec.get("email_type", EmailType.UNKNOWN),
            "source": spec.get("source"),
            "verified": bool(spec.get("verified", False)),
            "verification_status": spec.get("verification_status"),
            "quality_score": spec.get("quality_score"),
            "quality_bucket": spec.get("quality_bucket"),
            "is_primary": bool(spec.get("is_primary", False)),
        }

        current = merged.get(email)
        if current is None:
            merged[email] = normalized_spec
            continue

        current["verified"] = current["verified"] or normalized_spec["verified"]
        current["is_primary"] = current["is_primary"] or normalized_spec["is_primary"]
        if current["source"] in (None, "") and normalized_spec["source"]:
            current["source"] = normalized_spec["source"]
        if _verification_status_rank(
            normalized_spec.get("verification_status")
        ) > _verification_status_rank(current.get("verification_status")):
            current["verification_status"] = normalized_spec.get("verification_status")
        current_score = current.get("quality_score")
        normalized_score = normalized_spec.get("quality_score")
        if normalized_score is not None and (
            current_score is None or normalized_score >= current_score
        ):
            current["quality_score"] = normalized_score
            current["quality_bucket"] = normalized_spec.get("quality_bucket")
        if (
            current["email_type"] == EmailType.UNKNOWN
            and normalized_spec["email_type"] != EmailType.UNKNOWN
        ):
            current["email_type"] = normalized_spec["email_type"]
        if normalized_spec["is_primary"] and normalized_spec["email_type"] != EmailType.UNKNOWN:
            current["email_type"] = normalized_spec["email_type"]

    deduped = list(merged.values())
    for email_type in (EmailType.CORPORATE, EmailType.PERSONAL):
        typed_specs = [spec for spec in deduped if spec["email_type"] == email_type]
        primary_seen = False
        for spec in typed_specs:
            if spec["is_primary"] and not primary_seen:
                primary_seen = True
                continue
            if spec["is_primary"] and primary_seen:
                spec["is_primary"] = False
        if not primary_seen and typed_specs:
            typed_specs[0]["is_primary"] = True

    return sorted(
        deduped,
        key=lambda spec: (not spec["is_primary"], spec["email_type"].value, spec["email"]),
    )


def _dedupe_contact_point_specs(specs: list[LeadContactPointSpec]) -> list[LeadContactPointSpec]:
    merged: dict[tuple[str, str], LeadContactPointSpec] = {}

    for spec in specs:
        normalized_value = _normalize_contact_point_value(spec["kind"], spec.get("value"))
        if not normalized_value:
            continue
        normalized_spec: LeadContactPointSpec = {
            "kind": spec["kind"],
            "value": str(spec["value"]).strip(),
            "normalized_value": normalized_value,
            "source": spec.get("source"),
            "verified": bool(spec.get("verified", False)),
            "verification_status": _string_or_none(spec.get("verification_status")),
            "quality_score": spec.get("quality_score"),
            "quality_bucket": spec.get("quality_bucket"),
            "evidence_json": spec.get("evidence_json"),
            "metadata_json": spec.get("metadata_json"),
            "is_primary": bool(spec.get("is_primary", False)),
        }
        key = (normalized_spec["kind"].value, normalized_value.casefold())
        current = merged.get(key)
        if current is None:
            merged[key] = normalized_spec
            continue

        current["verified"] = current["verified"] or normalized_spec["verified"]
        current["is_primary"] = current["is_primary"] or normalized_spec["is_primary"]
        if current.get("source") in (None, "") and normalized_spec.get("source"):
            current["source"] = normalized_spec.get("source")
        current_score = current.get("quality_score")
        normalized_score = normalized_spec.get("quality_score")
        if normalized_score is not None and (
            current_score is None or normalized_score >= current_score
        ):
            current["quality_score"] = normalized_score
            current["quality_bucket"] = normalized_spec.get("quality_bucket")
        if current.get("verification_status") in (None, "") and normalized_spec.get(
            "verification_status"
        ):
            current["verification_status"] = normalized_spec.get("verification_status")
        if (
            current.get("evidence_json") is None
            and normalized_spec.get("evidence_json") is not None
        ):
            current["evidence_json"] = normalized_spec.get("evidence_json")
        if (
            current.get("metadata_json") is None
            and normalized_spec.get("metadata_json") is not None
        ):
            current["metadata_json"] = normalized_spec.get("metadata_json")

    deduped = list(merged.values())
    for kind in ContactPointKind:
        typed_specs = [spec for spec in deduped if spec["kind"] == kind]
        primary_seen = False
        for spec in typed_specs:
            if spec["is_primary"] and not primary_seen:
                primary_seen = True
                continue
            if spec["is_primary"] and primary_seen:
                spec["is_primary"] = False
        if not primary_seen and typed_specs:
            typed_specs[0]["is_primary"] = True

    return sorted(
        deduped,
        key=lambda spec: (spec["kind"].value, not spec["is_primary"], spec["normalized_value"]),
    )


def _normalize_contact_point_value(kind: ContactPointKind, value: object) -> str | None:
    if kind == ContactPointKind.EMAIL:
        return _normalize_email(_string_or_none(value))
    return _normalize_phone(_string_or_none(value))


def _normalize_phone(value: str | None) -> str | None:
    digits = "".join(ch for ch in (value or "") if ch.isdigit())
    return digits or None


def _sync_primary_email_fields(lead: Lead, specs: list[LeadEmailSpec]) -> None:
    corporate_primary = next(
        (
            spec
            for spec in specs
            if spec["email_type"] == EmailType.CORPORATE and spec["is_primary"]
        ),
        None,
    )
    personal_primary = next(
        (spec for spec in specs if spec["email_type"] == EmailType.PERSONAL and spec["is_primary"]),
        None,
    )

    lead.email_corporate = corporate_primary["email"] if corporate_primary else None
    lead.email_corporate_source = corporate_primary["source"] if corporate_primary else None
    lead.email_corporate_verified = corporate_primary["verified"] if corporate_primary else False
    lead.email_personal = personal_primary["email"] if personal_primary else None
    lead.email_personal_source = personal_primary["source"] if personal_primary else None


def _verification_status_rank(status: EmailVerificationStatus | None) -> int:
    if status == EmailVerificationStatus.VALID:
        return 4
    if status == EmailVerificationStatus.ACCEPT_ALL:
        return 3
    if status == EmailVerificationStatus.UNKNOWN:
        return 2
    if status is None:
        return 1
    return 0
