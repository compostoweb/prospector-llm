from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import (
    Channel,
    ContactPointKind,
    ContactQualityBucket,
    EmailProviderType,
    EmailType,
    EmailVerificationStatus,
    InteractionDirection,
    LeadStatus,
)
from models.interaction import Interaction
from models.lead import Lead
from models.lead_contact_point import LeadContactPoint
from models.lead_email import LeadEmail
from services.email_event_service import (
    build_outbound_email_delivery_observation,
    classify_inbound_email_event,
    get_email_provider_capabilities,
    mark_email_opened,
    record_email_bounce,
    record_email_unsubscribe,
)


@pytest.mark.asyncio
async def test_mark_email_opened_updates_interaction(
    db: AsyncSession,
    tenant,
) -> None:
    lead = Lead(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Lead Track",
        email_corporate="track@empresa.com",
        status=LeadStatus.IN_CADENCE,
        source="manual",
    )
    interaction = Interaction(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        lead_id=lead.id,
        channel=Channel.EMAIL,
        direction=InteractionDirection.OUTBOUND,
        content_text="Hello",
    )
    db.add_all([lead, interaction])
    await db.flush()

    await mark_email_opened(db, interaction.id)

    await db.refresh(interaction)
    assert interaction.opened is True
    assert interaction.opened_at is not None


@pytest.mark.asyncio
async def test_record_email_unsubscribe_is_idempotent(
    db: AsyncSession,
    tenant,
) -> None:
    created = await record_email_unsubscribe(db, tenant.id, "OptOut@Empresa.com")
    duplicated = await record_email_unsubscribe(db, tenant.id, "optout@empresa.com")

    assert created is True
    assert duplicated is False


@pytest.mark.asyncio
async def test_record_email_bounce_marks_matching_lead(
    db: AsyncSession,
    tenant,
) -> None:
    lead = Lead(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Lead Bounce",
        email_corporate="bounce@empresa.com",
        status=LeadStatus.IN_CADENCE,
        source="manual",
    )
    db.add(lead)
    await db.flush()

    updated_lead = await record_email_bounce(
        db,
        tenant.id,
        "bounce@empresa.com",
        source="test",
    )

    assert updated_lead is not None
    await db.refresh(lead)
    assert lead.email_bounced_at is not None
    assert lead.email_bounce_type == "hard"


@pytest.mark.asyncio
async def test_record_email_bounce_marks_only_bounced_contact_point_red(
    db: AsyncSession,
    tenant,
) -> None:
    lead = Lead(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Lead Bounce Contact",
        email_corporate="bounce@empresa.com",
        status=LeadStatus.IN_CADENCE,
        source="manual",
    )
    bounced_email = LeadEmail(
        tenant_id=tenant.id,
        lead_id=lead.id,
        email="bounce@empresa.com",
        email_type=EmailType.CORPORATE,
        verified=True,
        verification_status=EmailVerificationStatus.VALID,
        quality_bucket=ContactQualityBucket.GREEN,
        quality_score=0.95,
        is_primary=True,
    )
    bounced_contact = LeadContactPoint(
        tenant_id=tenant.id,
        lead_id=lead.id,
        kind=ContactPointKind.EMAIL,
        value="bounce@empresa.com",
        normalized_value="bounce@empresa.com",
        verified=True,
        verification_status=EmailVerificationStatus.VALID.value,
        quality_bucket=ContactQualityBucket.GREEN,
        quality_score=0.95,
        is_primary=True,
    )
    healthy_contact = LeadContactPoint(
        tenant_id=tenant.id,
        lead_id=lead.id,
        kind=ContactPointKind.EMAIL,
        value="alt@empresa.com",
        normalized_value="alt@empresa.com",
        verified=True,
        verification_status=EmailVerificationStatus.VALID.value,
        quality_bucket=ContactQualityBucket.GREEN,
        quality_score=0.90,
        is_primary=False,
    )
    db.add_all([lead, bounced_email, bounced_contact, healthy_contact])
    await db.flush()

    updated_lead = await record_email_bounce(
        db,
        tenant.id,
        "bounce@empresa.com",
        source="test",
    )

    assert updated_lead is not None
    await db.refresh(bounced_email)
    await db.refresh(bounced_contact)
    await db.refresh(healthy_contact)

    assert bounced_email.verified is False
    assert bounced_email.verification_status == EmailVerificationStatus.INVALID
    assert bounced_email.quality_bucket == ContactQualityBucket.RED
    assert bounced_contact.verified is False
    assert bounced_contact.verification_status == EmailVerificationStatus.INVALID.value
    assert bounced_contact.quality_bucket == ContactQualityBucket.RED
    assert bounced_contact.metadata_json is not None
    assert bounced_contact.metadata_json["last_bounce_source"] == "test"
    assert healthy_contact.quality_bucket == ContactQualityBucket.GREEN


@pytest.mark.asyncio
async def test_record_email_bounce_creates_red_contact_point_when_missing(
    db: AsyncSession,
    tenant,
) -> None:
    lead = Lead(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Lead Bounce Missing Contact",
        email_corporate="missing@empresa.com",
        status=LeadStatus.IN_CADENCE,
        source="manual",
    )
    db.add(lead)
    await db.flush()

    updated_lead = await record_email_bounce(
        db,
        tenant.id,
        "missing@empresa.com",
        source="test",
    )

    assert updated_lead is not None
    contact_result = await db.execute(
        select(LeadContactPoint).where(
            LeadContactPoint.lead_id == lead.id,
            LeadContactPoint.normalized_value == "missing@empresa.com",
        )
    )
    contact = contact_result.scalar_one()

    assert contact.quality_bucket == ContactQualityBucket.RED
    assert contact.verification_status == EmailVerificationStatus.INVALID.value
    assert contact.is_primary is True


def test_classify_inbound_email_event_detects_bounce() -> None:
    event = classify_inbound_email_event(
        from_email="mailer-daemon@googlemail.com",
        subject="Delivery Status Notification",
        body="Final-Recipient: rfc822; pessoa@empresa.com",
    )

    assert event.kind == "bounce"
    assert event.matched_email == "pessoa@empresa.com"


def test_classify_inbound_email_event_extracts_gmail_friendly_bounce_body() -> None:
    event = classify_inbound_email_event(
        from_email="mailer-daemon@googlemail.com",
        subject="Delivery Status Notification (Failure)",
        body=(
            "Endereço não encontrado\n"
            "A mensagem não foi entregue para "
            "bounce-test-1776892293@prospector-bounce-1776892293.invalid "
            "porque o domínio prospector-bounce-1776892293.invalid não foi encontrado.\n"
            "A resposta foi:\n"
            "DNS Error: DNS type 'mx' lookup of prospector-bounce-1776892293.invalid "
            "responded with code NXDOMAIN Domain name not found."
        ),
    )

    assert event.kind == "bounce"
    assert event.matched_email == "bounce-test-1776892293@prospector-bounce-1776892293.invalid"


def test_email_provider_capabilities_do_not_fake_delivered() -> None:
    capabilities = get_email_provider_capabilities(EmailProviderType.GOOGLE_OAUTH)
    delivery = build_outbound_email_delivery_observation(
        EmailProviderType.GOOGLE_OAUTH,
        success=True,
    )

    assert capabilities.supports_delivery_confirmation is False
    assert capabilities.observable_events == ("reply", "bounce", "opened", "unsubscribe")
    assert delivery.state == "accepted"
    assert delivery.confirmed is False
