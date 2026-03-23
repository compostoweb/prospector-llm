"""
tests/test_workers/test_cadence.py

Testes unitários para workers/cadence._tick_async().

Estratégia:
  - Testa _tick_async diretamente (sem passar pelo Celery .delay)
  - Banco de dados real via fixture db do conftest para criar fixtures
  - Redis e dispatch_step são mockados para isolar o worker
  - _tick_async usa engine próprio internamente — mockamos também para
    entregar o db de teste

Cobre:
  - Steps pendentes vencidos são enfileirados para dispatch
  - Steps de leads não IN_CADENCE são SKIPPED
  - Step com scheduled_at futura não é processado (ainda não vencido)
  - Rate limit esgotado → step não enfileirado (sem marcar SKIPPED)
  - Retorno do dict {"dispatched": N, "skipped": M} está correto
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.cadence import Cadence
from models.cadence_step import CadenceStep
from models.enums import Channel, LeadStatus, StepStatus
from models.lead import Lead
from models.tenant import Tenant

pytestmark = pytest.mark.asyncio


# ── Factories ─────────────────────────────────────────────────────────

def _make_lead(tenant_id: uuid.UUID, status: LeadStatus = LeadStatus.IN_CADENCE) -> Lead:
    return Lead(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="Lead Tick",
        company="Tick Corp",
        linkedin_url="https://linkedin.com/in/tick",
        status=status,
        source="manual",
    )


def _make_cadence(tenant_id: uuid.UUID) -> Cadence:
    return Cadence(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="Cadência Tick",
        llm_provider="openai",
        llm_model="gpt-4o-mini",
    )


def _make_step(
    tenant_id: uuid.UUID,
    lead_id: uuid.UUID,
    cadence_id: uuid.UUID,
    *,
    channel: Channel = Channel.LINKEDIN_CONNECT,
    scheduled_at: datetime | None = None,
    status: StepStatus = StepStatus.PENDING,
) -> CadenceStep:
    if scheduled_at is None:
        # Vencido por padrão (5 minutos atrás)
        scheduled_at = datetime.now(tz=timezone.utc) - timedelta(minutes=5)
    return CadenceStep(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        lead_id=lead_id,
        cadence_id=cadence_id,
        channel=channel,
        step_number=1,
        day_offset=0,
        use_voice=False,
        scheduled_at=scheduled_at,
        status=status,
    )


# ── Helper: substitui o engine interno do _tick_async ─────────────────

def _mock_engine_factory(db: AsyncSession, tenants: list[Tenant]):
    """
    Retorna um context manager que simula o engine + session_factory
    usados dentro de _tick_async para listar os tenants.
    """
    from unittest.mock import AsyncMock, MagicMock

    mock_engine = MagicMock()
    mock_engine.dispose = AsyncMock()

    mock_root_session = AsyncMock()
    scalar_result = MagicMock()
    scalar_result.scalars.return_value.all.return_value = tenants
    mock_root_session.execute = AsyncMock(return_value=scalar_result)
    mock_root_session.__aenter__ = AsyncMock(return_value=mock_root_session)
    mock_root_session.__aexit__ = AsyncMock(return_value=False)

    mock_session_factory = MagicMock(return_value=mock_root_session)

    return mock_engine, mock_session_factory


# ── Testes ────────────────────────────────────────────────────────────

async def test_tick_dispatches_pending_steps(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    tenant: Tenant,
) -> None:
    """Steps pendentes vencidos são enfileirados com dispatch_step.delay."""
    from workers.cadence import _tick_async

    lead = _make_lead(tenant_id)
    cadence = _make_cadence(tenant_id)
    step = _make_step(tenant_id, lead.id, cadence.id)
    db.add_all([lead, cadence, step])
    await db.flush()

    mock_engine, mock_session_factory = _mock_engine_factory(db, [tenant])

    with (
        patch("workers.cadence.create_async_engine", return_value=mock_engine),
        patch("workers.cadence.async_sessionmaker", return_value=mock_session_factory),
        patch("workers.cadence.get_session") as mock_get_session,
        patch("workers.cadence.redis_client") as mock_redis,
        patch("workers.cadence.dispatch_step") as mock_dispatch,
    ):
        async def _fake_session(_tid):
            yield db

        mock_get_session.side_effect = _fake_session
        mock_redis.check_and_increment = AsyncMock(return_value=True)
        mock_dispatch.delay = MagicMock()

        result = await _tick_async()

    assert result["dispatched"] >= 1
    assert result["skipped"] == 0
    mock_dispatch.delay.assert_called_once_with(str(step.id), str(tenant_id))


async def test_tick_skips_lead_not_in_cadence(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    tenant: Tenant,
) -> None:
    """Lead com status diferente de IN_CADENCE → step marcado como SKIPPED."""
    from workers.cadence import _tick_async

    lead = _make_lead(tenant_id, status=LeadStatus.CONVERTED)
    cadence = _make_cadence(tenant_id)
    step = _make_step(tenant_id, lead.id, cadence.id)
    db.add_all([lead, cadence, step])
    await db.flush()

    mock_engine, mock_session_factory = _mock_engine_factory(db, [tenant])

    with (
        patch("workers.cadence.create_async_engine", return_value=mock_engine),
        patch("workers.cadence.async_sessionmaker", return_value=mock_session_factory),
        patch("workers.cadence.get_session") as mock_get_session,
        patch("workers.cadence.redis_client") as mock_redis,
        patch("workers.cadence.dispatch_step") as mock_dispatch,
    ):
        async def _fake_session(_tid):
            yield db

        mock_get_session.side_effect = _fake_session
        mock_redis.check_and_increment = AsyncMock(return_value=True)
        mock_dispatch.delay = MagicMock()

        result = await _tick_async()

    assert result["skipped"] >= 1
    mock_dispatch.delay.assert_not_called()

    await db.refresh(step)
    assert step.status == StepStatus.SKIPPED


async def test_tick_does_not_dispatch_future_steps(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    tenant: Tenant,
) -> None:
    """Steps com scheduled_at no futuro não são processados."""
    from workers.cadence import _tick_async

    lead = _make_lead(tenant_id)
    cadence = _make_cadence(tenant_id)
    future_step = _make_step(
        tenant_id, lead.id, cadence.id,
        scheduled_at=datetime.now(tz=timezone.utc) + timedelta(hours=2),
    )
    db.add_all([lead, cadence, future_step])
    await db.flush()

    mock_engine, mock_session_factory = _mock_engine_factory(db, [tenant])

    with (
        patch("workers.cadence.create_async_engine", return_value=mock_engine),
        patch("workers.cadence.async_sessionmaker", return_value=mock_session_factory),
        patch("workers.cadence.get_session") as mock_get_session,
        patch("workers.cadence.redis_client") as mock_redis,
        patch("workers.cadence.dispatch_step") as mock_dispatch,
    ):
        async def _fake_session(_tid):
            yield db

        mock_get_session.side_effect = _fake_session
        mock_redis.check_and_increment = AsyncMock(return_value=True)
        mock_dispatch.delay = MagicMock()

        result = await _tick_async()

    assert result["dispatched"] == 0
    mock_dispatch.delay.assert_not_called()


async def test_tick_rate_limited_step_not_dispatched(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    tenant: Tenant,
) -> None:
    """Rate limit esgotado → step não é enfileirado (permanece PENDING)."""
    from workers.cadence import _tick_async

    lead = _make_lead(tenant_id)
    cadence = _make_cadence(tenant_id)
    step = _make_step(tenant_id, lead.id, cadence.id)
    db.add_all([lead, cadence, step])
    await db.flush()

    mock_engine, mock_session_factory = _mock_engine_factory(db, [tenant])

    with (
        patch("workers.cadence.create_async_engine", return_value=mock_engine),
        patch("workers.cadence.async_sessionmaker", return_value=mock_session_factory),
        patch("workers.cadence.get_session") as mock_get_session,
        patch("workers.cadence.redis_client") as mock_redis,
        patch("workers.cadence.dispatch_step") as mock_dispatch,
    ):
        async def _fake_session(_tid):
            yield db

        mock_get_session.side_effect = _fake_session
        # Rate limit esgotado para este canal
        mock_redis.check_and_increment = AsyncMock(return_value=False)
        mock_dispatch.delay = MagicMock()

        result = await _tick_async()

    assert result["dispatched"] == 0
    mock_dispatch.delay.assert_not_called()

    # Step deve continuar PENDING (não marcado SKIPPED por rate limit)
    await db.refresh(step)
    assert step.status == StepStatus.PENDING


async def test_tick_returns_correct_counts(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    tenant: Tenant,
) -> None:
    """Contadores dispatched/skipped refletem o que aconteceu."""
    from workers.cadence import _tick_async

    lead_active = _make_lead(tenant_id, status=LeadStatus.IN_CADENCE)
    lead_archived = _make_lead(tenant_id, status=LeadStatus.ARCHIVED)
    cadence = _make_cadence(tenant_id)

    step_ok = _make_step(tenant_id, lead_active.id, cadence.id)
    step_skip = _make_step(tenant_id, lead_archived.id, cadence.id)

    db.add_all([lead_active, lead_archived, cadence, step_ok, step_skip])
    await db.flush()

    mock_engine, mock_session_factory = _mock_engine_factory(db, [tenant])

    with (
        patch("workers.cadence.create_async_engine", return_value=mock_engine),
        patch("workers.cadence.async_sessionmaker", return_value=mock_session_factory),
        patch("workers.cadence.get_session") as mock_get_session,
        patch("workers.cadence.redis_client") as mock_redis,
        patch("workers.cadence.dispatch_step") as mock_dispatch,
    ):
        async def _fake_session(_tid):
            yield db

        mock_get_session.side_effect = _fake_session
        mock_redis.check_and_increment = AsyncMock(return_value=True)
        mock_dispatch.delay = MagicMock()

        result = await _tick_async()

    assert result["dispatched"] == 1
    assert result["skipped"] == 1


async def test_tick_no_tenants_returns_zero_counts() -> None:
    """Sem tenants ativos, retorna zeros sem erros."""
    from workers.cadence import _tick_async

    mock_engine = MagicMock()
    mock_engine.dispose = AsyncMock()

    mock_root_session = AsyncMock()
    scalar_result = MagicMock()
    scalar_result.scalars.return_value.all.return_value = []
    mock_root_session.execute = AsyncMock(return_value=scalar_result)
    mock_root_session.__aenter__ = AsyncMock(return_value=mock_root_session)
    mock_root_session.__aexit__ = AsyncMock(return_value=False)

    mock_session_factory = MagicMock(return_value=mock_root_session)

    with (
        patch("workers.cadence.create_async_engine", return_value=mock_engine),
        patch("workers.cadence.async_sessionmaker", return_value=mock_session_factory),
    ):
        result = await _tick_async()

    assert result["dispatched"] == 0
    assert result["skipped"] == 0
