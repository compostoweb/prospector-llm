"""
tests/test_workers/test_cadence.py

Testes unitários para workers/cadence._tick_async().

Estratégia:
  - Testa _tick_async diretamente (sem passar pelo Celery .delay)
  - Usa FakeAsyncSession em memória (sem dependência de DB real)
  - Redis e dispatch_step são mockados para isolar o worker
  - _tick_async usa engine próprio internamente — mockamos também para
    entregar a session fake

Cobre:
  - Steps pendentes vencidos são enfileirados para dispatch
  - Steps de leads não IN_CADENCE são SKIPPED
  - Step com scheduled_at futura não é processado (ainda não vencido)
  - Rate limit esgotado → step não enfileirado (sem marcar SKIPPED)
  - Retorno do dict {"dispatched": N, "skipped": M} está correto
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.sql import operators
from sqlalchemy.sql.elements import BinaryExpression, BooleanClauseList

from models.cadence import Cadence
from models.cadence_step import CadenceStep
from models.enums import Channel, LeadStatus, StepStatus
from models.lead import Lead
from models.tenant import Tenant

pytestmark = pytest.mark.asyncio


# ── FakeAsyncSession (sem dependência de DB) ──────────────────────────


class _FakeScalars:
    """Suporta tanto .all() quanto acesso direto ao valor escalar."""

    def __init__(self, items: list[Any], attr: str | None = None) -> None:
        self._items = items
        self._attr = attr

    def all(self) -> list[Any]:
        if self._attr:
            return [getattr(item, self._attr, item) for item in self._items]
        return list(self._items)


class _FakeResult:
    """Resultado fake que suporta scalar_one_or_none() e scalars()."""

    def __init__(self, items: list[Any], attr: str | None = None) -> None:
        self._items = items
        self._attr = attr

    def scalar_one_or_none(self) -> Any | None:
        if not self._items:
            return None
        val = self._items[0]
        return getattr(val, self._attr) if self._attr else val

    def scalars(self) -> _FakeScalars:
        return _FakeScalars(self._items, self._attr)


class FakeAsyncSession:
    """Session fake em memória que suporta os padrões de query do cadence worker."""

    def __init__(self) -> None:
        self._items: dict[type[Any], list[Any]] = {}

    def add(self, obj: object) -> None:
        bucket = self._items.setdefault(type(obj), [])
        if obj not in bucket:
            bucket.append(obj)

    def add_all(self, objects: list[object]) -> None:
        for obj in objects:
            self.add(obj)

    async def execute(self, statement: Any) -> _FakeResult:
        # Determina a entidade e possível atributo
        col_desc = (
            statement.column_descriptions[0] if hasattr(statement, "column_descriptions") else {}
        )
        entity = col_desc.get("entity")
        expr = col_desc.get("expr")

        # Detecta se é select de coluna específica (ex: select(Lead.status))
        attr: str | None = None
        if entity is not None and expr is not None and expr is not entity:
            attr = getattr(expr, "key", None)

        candidates = list(self._items.get(entity, [])) if entity is not None else []

        for criterion in getattr(statement, "_where_criteria", ()):
            candidates = [item for item in candidates if _matches_criterion(item, criterion)]

        return _FakeResult(candidates, attr)

    async def flush(self) -> None:
        pass

    async def commit(self) -> None:
        pass

    async def refresh(self, obj: object) -> None:
        pass

    async def close(self) -> None:
        pass


def _matches_criterion(obj: object, criterion: object) -> bool:
    """Avalia critérios WHERE contra objetos em memória."""
    if isinstance(criterion, BooleanClauseList):
        return all(_matches_criterion(obj, clause) for clause in criterion.clauses)

    if not isinstance(criterion, BinaryExpression):
        return True

    field_name = getattr(criterion.left, "key", None)
    if field_name is None:
        field_name = getattr(criterion.left, "name", None)
    if not isinstance(field_name, str):
        return True
    if not hasattr(obj, field_name):
        return True

    current_value = cast(object, getattr(obj, field_name, None))
    expected_value_raw = getattr(criterion.right, "value", criterion.right)
    expected_class_name = type(expected_value_raw).__name__
    if expected_class_name == "True_":
        expected_value = True
    elif expected_class_name == "False_":
        expected_value = False
    else:
        expected_value = cast(object, expected_value_raw)

    if criterion.operator is operators.eq:
        return current_value == expected_value  # type: ignore[return-value]
    if criterion.operator is operators.is_:
        return current_value is expected_value or current_value == expected_value  # type: ignore[return-value]
    if criterion.operator is operators.le:
        try:
            return cast(bool, current_value <= expected_value)  # type: ignore[return-value]
        except TypeError:
            return True
    if criterion.operator is operators.in_op:
        try:
            return current_value in expected_value
        except TypeError:
            return True

    return True


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def tenant_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def db() -> FakeAsyncSession:
    return FakeAsyncSession()


@pytest.fixture
def tenant(db: FakeAsyncSession, tenant_id: uuid.UUID) -> Tenant:
    t = Tenant(id=tenant_id, name="Tenant Teste", slug="tenant-teste")
    db.add(t)
    return t


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
        scheduled_at = datetime.now(tz=UTC) - timedelta(minutes=5)
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


def _mock_worker_session_local(db: FakeAsyncSession | None, tenants: list[Tenant]):
    """
    Retorna um mock para WorkerSessionLocal() que age como async context manager
    retornando uma session que lista os tenants fornecidos.
    """
    mock_root_session = AsyncMock()
    scalar_result = MagicMock()
    scalar_result.scalars.return_value.all.return_value = tenants
    mock_root_session.execute = AsyncMock(return_value=scalar_result)
    mock_root_session.__aenter__ = AsyncMock(return_value=mock_root_session)
    mock_root_session.__aexit__ = AsyncMock(return_value=False)

    return MagicMock(return_value=mock_root_session)


# ── Testes ────────────────────────────────────────────────────────────


async def test_tick_dispatches_pending_steps(
    db: FakeAsyncSession,
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

    mock_wsl = _mock_worker_session_local(db, [tenant])

    with (
        patch("workers.cadence.WorkerSessionLocal", mock_wsl),
        patch("workers.cadence.get_worker_session") as mock_get_session,
        patch("workers.cadence.redis_client") as mock_redis,
        patch("workers.dispatch.dispatch_step") as mock_dispatch,
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
    db: FakeAsyncSession,
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

    mock_wsl = _mock_worker_session_local(db, [tenant])

    with (
        patch("workers.cadence.WorkerSessionLocal", mock_wsl),
        patch("workers.cadence.get_worker_session") as mock_get_session,
        patch("workers.cadence.redis_client") as mock_redis,
        patch("workers.dispatch.dispatch_step") as mock_dispatch,
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
    db: FakeAsyncSession,
    tenant_id: uuid.UUID,
    tenant: Tenant,
) -> None:
    """Steps com scheduled_at no futuro não são processados."""
    from workers.cadence import _tick_async

    lead = _make_lead(tenant_id)
    cadence = _make_cadence(tenant_id)
    future_step = _make_step(
        tenant_id,
        lead.id,
        cadence.id,
        scheduled_at=datetime.now(tz=UTC) + timedelta(hours=2),
    )
    db.add_all([lead, cadence, future_step])
    await db.flush()

    mock_wsl = _mock_worker_session_local(db, [tenant])

    with (
        patch("workers.cadence.WorkerSessionLocal", mock_wsl),
        patch("workers.cadence.get_worker_session") as mock_get_session,
        patch("workers.cadence.redis_client") as mock_redis,
        patch("workers.dispatch.dispatch_step") as mock_dispatch,
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
    db: FakeAsyncSession,
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

    mock_wsl = _mock_worker_session_local(db, [tenant])

    with (
        patch("workers.cadence.WorkerSessionLocal", mock_wsl),
        patch("workers.cadence.get_worker_session") as mock_get_session,
        patch("workers.cadence.redis_client") as mock_redis,
        patch("workers.dispatch.dispatch_step") as mock_dispatch,
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


async def test_tick_uses_tenant_specific_rate_limit(
    db: FakeAsyncSession,
    tenant_id: uuid.UUID,
    tenant: Tenant,
) -> None:
    """Worker usa override de rate limit do tenant quando existir."""
    from models.tenant import TenantIntegration
    from workers.cadence import _tick_async

    lead = _make_lead(tenant_id)
    cadence = _make_cadence(tenant_id)
    step = _make_step(
        tenant_id,
        lead.id,
        cadence.id,
        channel=Channel.EMAIL,
    )
    integration = TenantIntegration(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        limit_linkedin_connect=11,
        limit_linkedin_dm=22,
        limit_email=77,
    )
    db.add_all([lead, cadence, step, integration])
    await db.flush()

    mock_wsl = _mock_worker_session_local(db, [tenant])

    with (
        patch("workers.cadence.WorkerSessionLocal", mock_wsl),
        patch("workers.cadence.get_worker_session") as mock_get_session,
        patch("workers.cadence.redis_client") as mock_redis,
        patch("workers.dispatch.dispatch_step") as mock_dispatch,
    ):

        async def _fake_session(_tid):
            yield db

        mock_get_session.side_effect = _fake_session
        mock_redis.check_and_increment = AsyncMock(return_value=True)
        mock_dispatch.delay = MagicMock()

        await _tick_async()

    mock_redis.check_and_increment.assert_called_once_with(
        channel=Channel.EMAIL.value,
        tenant_id=tenant_id,
        limit=77,
    )


async def test_tick_returns_correct_counts(
    db: FakeAsyncSession,
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

    mock_wsl = _mock_worker_session_local(db, [tenant])

    with (
        patch("workers.cadence.WorkerSessionLocal", mock_wsl),
        patch("workers.cadence.get_worker_session") as mock_get_session,
        patch("workers.cadence.redis_client") as mock_redis,
        patch("workers.dispatch.dispatch_step") as mock_dispatch,
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

    mock_wsl = _mock_worker_session_local(None, [])

    with patch("workers.cadence.WorkerSessionLocal", mock_wsl):
        result = await _tick_async()

    assert result["dispatched"] == 0
    assert result["skipped"] == 0
