from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.cadence import Cadence
from models.cadence_step import CadenceStep
from models.email_account import EmailAccount
from models.enums import Channel, Intent, StepStatus
from models.interaction import Interaction
from models.lead import Lead
from models.lead_email import LeadEmail
from models.linkedin_account import LinkedInAccount
from models.tenant import TenantIntegration
from services.inbound_message_service import (
    find_lead_by_email,
    process_inbound_reply,
    resolve_unipile_account_context,
)

pytestmark = pytest.mark.asyncio


def _make_lead(tenant_id: uuid.UUID) -> Lead:
    suffix = uuid.uuid4().hex[:10]
    return Lead(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="João Silva",
        company="Acme Corp",
        linkedin_url=f"https://linkedin.com/in/{suffix}",
        linkedin_profile_id=f"li_{suffix}",
        email_corporate="joao@acme.com",
        status="in_cadence",
        source="manual",
    )


async def test_resolve_unipile_account_context_uses_provider_accounts(
    db: AsyncSession,
    tenant,
) -> None:
    linkedin_account = LinkedInAccount(
        tenant_id=tenant.id,
        display_name="LinkedIn Unipile",
        provider_type="unipile",
        unipile_account_id="li_acc_123",
    )
    email_account = EmailAccount(
        tenant_id=tenant.id,
        display_name="Gmail Unipile",
        email_address="owner@acme.com",
        provider_type="unipile_gmail",
        unipile_account_id="gm_acc_456",
    )
    db.add_all([linkedin_account, email_account])
    await db.flush()

    linkedin_context = await resolve_unipile_account_context("li_acc_123", db)
    email_context = await resolve_unipile_account_context("gm_acc_456", db)

    assert linkedin_context is not None
    assert linkedin_context.tenant_id == tenant.id
    assert linkedin_context.channel == Channel.LINKEDIN_DM

    assert email_context is not None
    assert email_context.tenant_id == tenant.id
    assert email_context.channel == Channel.EMAIL


async def test_resolve_unipile_account_context_filters_by_account_type(
    db: AsyncSession,
    tenant,
) -> None:
    result = await db.execute(
        select(TenantIntegration).where(TenantIntegration.tenant_id == tenant.id)
    )
    integration = result.scalar_one()
    integration.unipile_linkedin_account_id = "shared_acc"
    integration.unipile_gmail_account_id = "shared_acc"
    await db.flush()

    linkedin_context = await resolve_unipile_account_context(
        "shared_acc",
        db,
        account_type="LINKEDIN",
    )
    email_context = await resolve_unipile_account_context(
        "shared_acc",
        db,
        account_type="GMAIL",
    )

    assert linkedin_context is not None
    assert linkedin_context.channel == Channel.LINKEDIN_DM
    assert email_context is not None
    assert email_context.channel == Channel.EMAIL


async def test_find_lead_by_email_matches_lead_email_case_insensitive(
    db: AsyncSession,
    tenant,
) -> None:
    lead = _make_lead(tenant.id)
    db.add(lead)
    await db.flush()

    db.add(
        LeadEmail(
            tenant_id=tenant.id,
            lead_id=lead.id,
            email="Joao+Extra@Acme.com",
            source="import",
        )
    )
    await db.flush()

    found = await find_lead_by_email("joao+extra@acme.com", tenant.id, db)

    assert found is not None
    assert found.id == lead.id


async def test_process_inbound_reply_marks_connect_step_replied_for_linkedin_dm(
    db: AsyncSession,
    tenant,
) -> None:
    lead = _make_lead(tenant.id)
    cadence = Cadence(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Cadência Teste",
        llm_provider="openai",
        llm_model="gpt-4o-mini",
        llm_temperature=0.7,
        llm_max_tokens=256,
    )
    step = CadenceStep(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        lead_id=lead.id,
        cadence_id=cadence.id,
        channel=Channel.LINKEDIN_CONNECT,
        step_number=1,
        day_offset=0,
        scheduled_at=datetime.now(tz=UTC) - timedelta(days=1),
        sent_at=datetime.now(tz=UTC) - timedelta(hours=2),
        status=StepStatus.SENT,
    )
    db.add_all([lead, cadence, step])
    await db.flush()

    parser_instance = MagicMock()
    parser_instance.classify = AsyncMock(
        return_value={
            "intent": "INTEREST",
            "confidence": 0.96,
            "summary": "Aceitou continuar a conversa",
        }
    )

    with (
        patch(
            "services.inbound_message_service.resolve_tenant_llm_config",
            new=AsyncMock(return_value=SimpleNamespace(provider="openai", model="gpt-4o-mini")),
        ),
        patch("services.inbound_message_service.ReplyParser", return_value=parser_instance),
        patch("services.notification.send_reply_notification", new=AsyncMock()),
        patch("api.routes.ws.broadcast_event", new=AsyncMock()),
    ):
        result = await process_inbound_reply(
            db=db,
            registry=MagicMock(),
            tenant_id=tenant.id,
            lead=lead,
            channel=Channel.LINKEDIN_DM,
            reply_text="Aceitei, pode me mandar mais detalhes.",
            external_message_id="msg_li_123",
        )

    await db.refresh(step)
    await db.refresh(lead)
    interaction_result = await db.execute(
        select(Interaction).where(Interaction.unipile_message_id == "msg_li_123")
    )
    interaction = interaction_result.scalar_one_or_none()

    assert result.intent == Intent.INTEREST
    assert step.status == StepStatus.REPLIED
    assert lead.status == "converted"
    assert interaction is not None
    assert interaction.channel == Channel.LINKEDIN_DM
