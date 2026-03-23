"""
tests/test_services/test_cadence_manager.py

Testes unitários para services/cadence_manager.py.
Foco: lógica de enrollment — filtragem de canais, criação de steps.
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from models.cadence import Cadence
from models.enums import Channel, LeadStatus, StepStatus
from models.lead import Lead
from services.cadence_manager import CadenceManager, _DEFAULT_TEMPLATE


pytestmark = pytest.mark.asyncio


# ── Fixtures ──────────────────────────────────────────────────────────

def _make_lead(
    tenant_id: uuid.UUID,
    linkedin_url: str | None = "https://linkedin.com/in/test",
    email_corporate: str | None = "test@empresa.com",
) -> Lead:
    return Lead(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="Teste Lead",
        company="ACME",
        linkedin_url=linkedin_url,
        email_corporate=email_corporate,
        status=LeadStatus.ENRICHED,
    )


def _make_cadence(tenant_id: uuid.UUID, allow_personal_email: bool = False) -> Cadence:
    return Cadence(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="Cadência Teste",
        allow_personal_email=allow_personal_email,
    )


# ── Testes de enrollment ──────────────────────────────────────────────

async def test_enroll_all_channels_creates_all_steps(
    db: AsyncSession, tenant_id: uuid.UUID, tenant
):
    """Lead com LinkedIn + email corporativo → todos os steps do template."""
    lead = _make_lead(tenant_id)
    cadence = _make_cadence(tenant_id)
    db.add(lead)
    db.add(cadence)
    await db.flush()

    manager = CadenceManager()
    steps = await manager.enroll(lead, cadence, db)

    assert len(steps) == len(_DEFAULT_TEMPLATE)
    assert lead.status == LeadStatus.IN_CADENCE

    channels = [s.channel for s in steps]
    assert Channel.LINKEDIN_CONNECT in channels
    assert Channel.LINKEDIN_DM in channels
    assert Channel.EMAIL in channels


async def test_enroll_without_linkedin_skips_linkedin_steps(
    db: AsyncSession, tenant_id: uuid.UUID, tenant
):
    """Lead sem LinkedIn → steps LINKEDIN_CONNECT e LINKEDIN_DM ignorados."""
    lead = _make_lead(tenant_id, linkedin_url=None)
    cadence = _make_cadence(tenant_id)
    db.add(lead)
    db.add(cadence)
    await db.flush()

    manager = CadenceManager()
    steps = await manager.enroll(lead, cadence, db)

    channels = [s.channel for s in steps]
    assert Channel.LINKEDIN_CONNECT not in channels
    assert Channel.LINKEDIN_DM not in channels
    assert Channel.EMAIL in channels


async def test_enroll_without_email_skips_email_steps(
    db: AsyncSession, tenant_id: uuid.UUID, tenant
):
    """Lead sem email e cadência não permite pessoal → steps EMAIL ignorados."""
    lead = _make_lead(tenant_id, email_corporate=None)
    cadence = _make_cadence(tenant_id, allow_personal_email=False)
    db.add(lead)
    db.add(cadence)
    await db.flush()

    manager = CadenceManager()
    steps = await manager.enroll(lead, cadence, db)

    channels = [s.channel for s in steps]
    assert Channel.EMAIL not in channels
    assert Channel.LINKEDIN_CONNECT in channels


async def test_enroll_personal_email_allowed(
    db: AsyncSession, tenant_id: uuid.UUID, tenant
):
    """Lead com email pessoal + cadência permite pessoal → EMAIL incluído."""
    lead = _make_lead(tenant_id, email_corporate=None)
    lead.email_personal = "teste@gmail.com"
    cadence = _make_cadence(tenant_id, allow_personal_email=True)
    db.add(lead)
    db.add(cadence)
    await db.flush()

    manager = CadenceManager()
    steps = await manager.enroll(lead, cadence, db)

    channels = [s.channel for s in steps]
    assert Channel.EMAIL in channels


async def test_enroll_no_channel_raises(
    db: AsyncSession, tenant_id: uuid.UUID, tenant
):
    """Lead sem LinkedIn e sem email → ValueError."""
    lead = _make_lead(tenant_id, linkedin_url=None, email_corporate=None)
    cadence = _make_cadence(tenant_id, allow_personal_email=False)
    db.add(lead)
    db.add(cadence)
    await db.flush()

    manager = CadenceManager()
    with pytest.raises(ValueError, match="nenhum canal disponível"):
        await manager.enroll(lead, cadence, db)


async def test_enroll_steps_have_correct_status(
    db: AsyncSession, tenant_id: uuid.UUID, tenant
):
    """Todos os steps criados devem ter status PENDING."""
    lead = _make_lead(tenant_id)
    cadence = _make_cadence(tenant_id)
    db.add(lead)
    db.add(cadence)
    await db.flush()

    manager = CadenceManager()
    steps = await manager.enroll(lead, cadence, db)

    assert all(s.status == StepStatus.PENDING for s in steps)


async def test_enroll_steps_have_ascending_day_offsets(
    db: AsyncSession, tenant_id: uuid.UUID, tenant
):
    """Os steps devem ser ordenados por day_offset crescente."""
    lead = _make_lead(tenant_id)
    cadence = _make_cadence(tenant_id)
    db.add(lead)
    db.add(cadence)
    await db.flush()

    manager = CadenceManager()
    steps = await manager.enroll(lead, cadence, db)

    offsets = [s.day_offset for s in steps]
    assert offsets == sorted(offsets)
