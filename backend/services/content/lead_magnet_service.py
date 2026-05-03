"""
services/content/lead_magnet_service.py

Regras de negócio do subsistema inbound de lead magnets.
"""

from __future__ import annotations

import uuid
from typing import Any, TypedDict

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from models.content_landing_page import ContentLandingPage
from models.content_lead_magnet import ContentLeadMagnet
from models.content_lm_email_event import ContentLMEmailEvent
from models.content_lm_lead import ContentLMLead
from models.enums import LeadSource, LeadStatus
from models.lead import Lead
from models.lead_tag import LeadTag


def normalize_email(email: str) -> str:
    return email.strip().lower()


def build_public_landing_page_url(slug: str) -> str:
    return f"{settings.CONTENT_PUBLIC_BASE_URL.rstrip('/')}/lm/{slug}"


def recalculate_conversion_rate(total: int, base: int) -> float | None:
    if base <= 0:
        return None
    return round((total / base) * 100.0, 2)


class LeadMagnetMetrics(TypedDict):
    lead_magnet_id: uuid.UUID
    total_leads_captured: int
    total_synced_to_sendpulse: int
    total_sendpulse_pending: int
    total_sendpulse_failed: int
    total_sendpulse_skipped: int
    total_sequence_completed: int
    total_converted_via_email: int
    total_unsubscribed: int
    total_opens: int
    total_clicks: int
    landing_page_views: int
    landing_page_submissions: int
    landing_page_conversion_rate: float | None
    qualified_conversion_rate: float | None


async def get_lead_magnet_metrics(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    lead_magnet_id: uuid.UUID,
) -> LeadMagnetMetrics:
    total_leads_captured = await db.scalar(
        select(func.count(ContentLMLead.id)).where(
            ContentLMLead.tenant_id == tenant_id,
            ContentLMLead.lead_magnet_id == lead_magnet_id,
        )
    )
    total_synced = await db.scalar(
        select(func.count(ContentLMLead.id)).where(
            ContentLMLead.tenant_id == tenant_id,
            ContentLMLead.lead_magnet_id == lead_magnet_id,
            ContentLMLead.sendpulse_sync_status == "synced",
        )
    )
    total_sendpulse_pending = await db.scalar(
        select(func.count(ContentLMLead.id)).where(
            ContentLMLead.tenant_id == tenant_id,
            ContentLMLead.lead_magnet_id == lead_magnet_id,
            ContentLMLead.sendpulse_sync_status.in_(["pending", "processing"]),
        )
    )
    total_sendpulse_failed = await db.scalar(
        select(func.count(ContentLMLead.id)).where(
            ContentLMLead.tenant_id == tenant_id,
            ContentLMLead.lead_magnet_id == lead_magnet_id,
            ContentLMLead.sendpulse_sync_status == "failed",
        )
    )
    total_sendpulse_skipped = await db.scalar(
        select(func.count(ContentLMLead.id)).where(
            ContentLMLead.tenant_id == tenant_id,
            ContentLMLead.lead_magnet_id == lead_magnet_id,
            ContentLMLead.sendpulse_sync_status == "skipped",
        )
    )
    total_sequence_completed = await db.scalar(
        select(func.count(ContentLMLead.id)).where(
            ContentLMLead.tenant_id == tenant_id,
            ContentLMLead.lead_magnet_id == lead_magnet_id,
            ContentLMLead.sequence_completed.is_(True),
        )
    )
    total_converted_via_email = await db.scalar(
        select(func.count(ContentLMLead.id)).where(
            ContentLMLead.tenant_id == tenant_id,
            ContentLMLead.lead_magnet_id == lead_magnet_id,
            ContentLMLead.converted_via_email.is_(True),
        )
    )
    total_unsubscribed = await db.scalar(
        select(func.count(ContentLMLead.id)).where(
            ContentLMLead.tenant_id == tenant_id,
            ContentLMLead.lead_magnet_id == lead_magnet_id,
            ContentLMLead.sequence_status == "unsubscribed",
        )
    )
    total_opens = await db.scalar(
        select(func.count(ContentLMEmailEvent.id)).where(
            ContentLMEmailEvent.tenant_id == tenant_id,
            ContentLMEmailEvent.lead_magnet_id == lead_magnet_id,
            ContentLMEmailEvent.event_type == "open",
        )
    )
    total_clicks = await db.scalar(
        select(func.count(ContentLMEmailEvent.id)).where(
            ContentLMEmailEvent.tenant_id == tenant_id,
            ContentLMEmailEvent.lead_magnet_id == lead_magnet_id,
            ContentLMEmailEvent.event_type == "click",
        )
    )

    landing_page_result = await db.execute(
        select(ContentLandingPage).where(
            ContentLandingPage.tenant_id == tenant_id,
            ContentLandingPage.lead_magnet_id == lead_magnet_id,
        )
    )
    landing_page = landing_page_result.scalar_one_or_none()
    landing_page_views = landing_page.total_views if landing_page else 0
    landing_page_submissions = landing_page.total_submissions if landing_page else 0
    landing_page_conversion_rate = landing_page.conversion_rate if landing_page else None
    qualified_conversion_rate = recalculate_conversion_rate(
        int(total_converted_via_email or 0),
        int(total_leads_captured or 0),
    )

    return {
        "lead_magnet_id": lead_magnet_id,
        "total_leads_captured": int(total_leads_captured or 0),
        "total_synced_to_sendpulse": int(total_synced or 0),
        "total_sendpulse_pending": int(total_sendpulse_pending or 0),
        "total_sendpulse_failed": int(total_sendpulse_failed or 0),
        "total_sendpulse_skipped": int(total_sendpulse_skipped or 0),
        "total_sequence_completed": int(total_sequence_completed or 0),
        "total_converted_via_email": int(total_converted_via_email or 0),
        "total_unsubscribed": int(total_unsubscribed or 0),
        "total_opens": int(total_opens or 0),
        "total_clicks": int(total_clicks or 0),
        "landing_page_views": landing_page_views,
        "landing_page_submissions": landing_page_submissions,
        "landing_page_conversion_rate": landing_page_conversion_rate,
        "qualified_conversion_rate": qualified_conversion_rate,
    }


async def upsert_lm_capture(
    db: AsyncSession,
    *,
    lead_magnet: ContentLeadMagnet,
    name: str,
    email: str,
    origin: str,
    lm_post_id: uuid.UUID | None = None,
    linkedin_profile_url: str | None = None,
    company: str | None = None,
    role: str | None = None,
    phone: str | None = None,
    capture_metadata: dict[str, Any] | None = None,
) -> tuple[ContentLMLead, bool, bool]:
    normalized_email = normalize_email(email)
    result = await db.execute(
        select(ContentLMLead).where(
            ContentLMLead.tenant_id == lead_magnet.tenant_id,
            ContentLMLead.lead_magnet_id == lead_magnet.id,
            ContentLMLead.email == normalized_email,
        )
    )
    lm_lead = result.scalar_one_or_none()
    created = lm_lead is None

    if lm_lead is None:
        lm_lead = ContentLMLead(
            tenant_id=lead_magnet.tenant_id,
            lead_magnet_id=lead_magnet.id,
            lm_post_id=lm_post_id,
            name=name,
            email=normalized_email,
            linkedin_profile_url=linkedin_profile_url,
            company=company,
            role=role,
            phone=phone,
            origin=origin,
            capture_metadata=capture_metadata,
            sendpulse_list_id=lead_magnet.sendpulse_list_id,
            sendpulse_sync_status="pending" if lead_magnet.sendpulse_list_id else "skipped",
        )
        db.add(lm_lead)
        lead_magnet.total_leads_captured += 1
    else:
        lm_lead.name = name or lm_lead.name
        lm_lead.linkedin_profile_url = linkedin_profile_url or lm_lead.linkedin_profile_url
        lm_lead.company = company or lm_lead.company
        lm_lead.role = role or lm_lead.role
        lm_lead.phone = phone or lm_lead.phone
        lm_lead.origin = origin or lm_lead.origin
        if lm_post_id is not None:
            lm_lead.lm_post_id = lm_post_id
        if capture_metadata:
            merged = dict(lm_lead.capture_metadata or {})
            merged.update(capture_metadata)
            lm_lead.capture_metadata = merged

    list_changed = lm_lead.sendpulse_list_id != lead_magnet.sendpulse_list_id
    lm_lead.sendpulse_list_id = lead_magnet.sendpulse_list_id

    should_sync = bool(lead_magnet.sendpulse_list_id) and (
        created
        or list_changed
        or lm_lead.sendpulse_sync_status in {"pending", "failed", "skipped"}
        or not lm_lead.sendpulse_subscriber_id
    )
    if should_sync:
        lm_lead.sendpulse_sync_status = "pending"
        lm_lead.sendpulse_last_error = None

    return lm_lead, created, should_sync


async def update_landing_page_submission_stats(
    landing_page: ContentLandingPage,
    *,
    increment_views: int = 0,
    increment_submissions: int = 0,
) -> None:
    landing_page.total_views += increment_views
    landing_page.total_submissions += increment_submissions
    landing_page.conversion_rate = recalculate_conversion_rate(
        landing_page.total_submissions,
        landing_page.total_views,
    )


async def queue_sendpulse_sync(lm_lead: ContentLMLead) -> None:
    from workers.content_lm_sync import sync_lm_lead_to_sendpulse

    sync_lm_lead_to_sendpulse.apply_async(
        args=[str(lm_lead.id), str(lm_lead.tenant_id)],
        queue="content",
    )


async def queue_lm_delivery_email(lm_lead: ContentLMLead) -> None:
    from workers.content_lm_sync import send_lm_delivery_email

    send_lm_delivery_email.apply_async(
        args=[str(lm_lead.id), str(lm_lead.tenant_id)],
        queue="content",
    )


async def _ensure_lead_tag(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    lead_id: uuid.UUID,
    name: str,
    color: str,
) -> None:
    tag_result = await db.execute(
        select(LeadTag).where(
            LeadTag.tenant_id == tenant_id,
            LeadTag.lead_id == lead_id,
            LeadTag.name == name,
        )
    )
    if tag_result.scalar_one_or_none() is None:
        db.add(
            LeadTag(
                tenant_id=tenant_id,
                lead_id=lead_id,
                name=name,
                color=color,
            )
        )


def _append_note(existing: str | None, new_line: str) -> str:
    if not existing:
        return new_line
    if new_line in existing:
        return existing
    return f"{existing}\n\n{new_line}".strip()


async def convert_inbound_contact_to_prospect(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    name: str,
    email: str,
    company: str | None,
    role: str | None,
    phone: str | None,
    note: str,
    extra_tags: list[str] | None = None,
) -> Lead:
    result = await db.execute(
        select(Lead).where(
            Lead.tenant_id == tenant_id,
            or_(Lead.email_corporate == email, Lead.email_personal == email),
        )
    )
    lead = result.scalar_one_or_none()

    if lead is None:
        lead = Lead(
            tenant_id=tenant_id,
            name=name,
            job_title=role,
            company=company,
            phone=phone,
            email_corporate=email,
            email_corporate_source="lead_magnet",
            source=LeadSource.API,
            status=LeadStatus.RAW,
            notes=note,
        )
        db.add(lead)
        await db.flush()
    else:
        if not lead.name and name:
            lead.name = name
        if not lead.job_title and role:
            lead.job_title = role
        if not lead.company and company:
            lead.company = company
        if not lead.phone and phone:
            lead.phone = phone
        if not lead.email_corporate:
            lead.email_corporate = email
            lead.email_corporate_source = "lead_magnet"
        lead.notes = _append_note(lead.notes, note)

    await _ensure_lead_tag(
        db,
        tenant_id=tenant_id,
        lead_id=lead.id,
        name="lead_magnet",
        color="#2563eb",
    )
    for tag_name in extra_tags or []:
        await _ensure_lead_tag(
            db,
            tenant_id=tenant_id,
            lead_id=lead.id,
            name=tag_name,
            color="#0f766e",
        )
    return lead


async def convert_lm_lead_to_prospect(
    db: AsyncSession,
    *,
    lm_lead: ContentLMLead,
    lead_magnet_title: str,
    note_suffix: str | None = None,
    extra_tags: list[str] | None = None,
) -> Lead:
    note = f"Origem inbound: {lead_magnet_title}"
    if note_suffix:
        note = f"{note} | {note_suffix}"

    lead = await convert_inbound_contact_to_prospect(
        db,
        tenant_id=lm_lead.tenant_id,
        name=lm_lead.name,
        email=lm_lead.email,
        company=lm_lead.company,
        role=lm_lead.role,
        phone=lm_lead.phone,
        note=note,
        extra_tags=extra_tags,
    )

    lm_lead.converted_to_lead = True
    lm_lead.lead_id = lead.id
    return lead
