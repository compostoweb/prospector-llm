from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.cadence import Cadence
from models.cadence_step import CadenceStep
from models.enums import Channel, StepStatus
from models.lead import Lead
from models.linkedin_account import LinkedInAccount
from models.tenant import TenantIntegration
from workers.connection_check import _resolve_unipile_account_id_for_lead

pytestmark = pytest.mark.asyncio


def _make_pending_lead(tenant_id: uuid.UUID) -> Lead:
    suffix = uuid.uuid4().hex[:10]
    return Lead(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="Lead Pending",
        company="Acme",
        linkedin_url=f"https://linkedin.com/in/{suffix}",
        linkedin_profile_id=f"li_{suffix}",
        linkedin_connection_status="pending",
        status="in_cadence",
        source="manual",
    )


async def test_resolve_unipile_account_id_for_lead_prefers_cadence_account(
    db: AsyncSession,
    tenant,
) -> None:
    lead = _make_pending_lead(tenant.id)
    linkedin_account = LinkedInAccount(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        display_name="Conta Unipile",
        provider_type="unipile",
        unipile_account_id="li_cadence_123",
    )
    cadence = Cadence(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Cadência LinkedIn",
        llm_provider="openai",
        llm_model="gpt-4o-mini",
        llm_temperature=0.7,
        llm_max_tokens=256,
        linkedin_account_id=linkedin_account.id,
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
        sent_at=datetime.now(tz=UTC) - timedelta(hours=3),
        status=StepStatus.SENT,
    )
    db.add_all([lead, linkedin_account])
    await db.flush()
    db.add_all([cadence, step])
    await db.flush()

    account_id = await _resolve_unipile_account_id_for_lead(lead, db)

    assert account_id == "li_cadence_123"


async def test_resolve_unipile_account_id_for_lead_skips_native_account(
    db: AsyncSession,
    tenant,
) -> None:
    lead = _make_pending_lead(tenant.id)
    linkedin_account = LinkedInAccount(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        display_name="Conta Nativa",
        provider_type="native",
        li_at_cookie="encrypted-cookie",
    )
    cadence = Cadence(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Cadência Native",
        llm_provider="openai",
        llm_model="gpt-4o-mini",
        llm_temperature=0.7,
        llm_max_tokens=256,
        linkedin_account_id=linkedin_account.id,
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
        sent_at=datetime.now(tz=UTC) - timedelta(hours=3),
        status=StepStatus.SENT,
    )
    result = await db.execute(
        select(TenantIntegration).where(TenantIntegration.tenant_id == tenant.id)
    )
    integration = result.scalar_one()
    integration.unipile_linkedin_account_id = "fallback_should_not_be_used"

    db.add_all([lead, linkedin_account])
    await db.flush()
    db.add_all([cadence, step])
    await db.flush()

    account_id = await _resolve_unipile_account_id_for_lead(lead, db)

    assert account_id is None
