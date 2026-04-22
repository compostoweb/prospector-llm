from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import Channel, EmailProviderType, InteractionDirection, LeadStatus
from models.interaction import Interaction
from models.lead import Lead
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
    assert (
        event.matched_email
        == "bounce-test-1776892293@prospector-bounce-1776892293.invalid"
    )


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
