"""
tests/test_api/test_analytics.py

Testes unitários das rotas de analytics adicionadas recentemente.
O foco aqui é validar a transformação dos resultados e o uso do filtro `days`
sem depender do ambiente asyncpg atual, que segue instável para esse tipo de setup.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from api.routes import analytics as analytics_routes
from models.cadence import Cadence
from models.enums import Channel

pytestmark = pytest.mark.asyncio


class FakeResult:
    def __init__(
        self,
        *,
        scalar_value: object | None = None,
        scalar_one_or_none_value: object | None = None,
        one_value: object | None = None,
        all_values: list[object] | None = None,
    ) -> None:
        self._scalar_value = scalar_value
        self._scalar_one_or_none_value = scalar_one_or_none_value
        self._one_value = one_value
        self._all_values = all_values or []

    def scalar(self) -> object | None:
        return self._scalar_value

    def scalar_one_or_none(self) -> object | None:
        if self._scalar_one_or_none_value is not None:
            return self._scalar_one_or_none_value
        return self._scalar_value

    def one(self) -> object:
        if self._one_value is None:
            raise AssertionError("Expected one() value for fake result")
        return self._one_value

    def all(self) -> list[object]:
        return self._all_values


class RecordingAsyncSession:
    def __init__(self, *results: FakeResult) -> None:
        self._results = list(results)
        self.statements: list[object] = []

    async def execute(self, statement):  # type: ignore[no-untyped-def]
        self.statements.append(statement)
        if not self._results:
            raise AssertionError("Unexpected execute() call without fake result")
        return self._results.pop(0)


def _make_cadence(tenant_id: uuid.UUID, cadence_id: uuid.UUID | None = None) -> Cadence:
    return Cadence(
        id=cadence_id or uuid.uuid4(),
        tenant_id=tenant_id,
        name="Cadência Teste",
        description="Cadência para analytics",
        is_active=True,
        cadence_type="mixed",
        mode="automatic",
        llm_provider="openai",
        llm_model="gpt-4o-mini",
        llm_temperature=0.7,
        llm_max_tokens=512,
    )


def _statement_contains_param(statement: object, expected: object) -> bool:
    compiled = statement.compile()
    return expected in compiled.params.values()


async def test_get_cadences_overview_returns_real_metrics() -> None:
    tenant_id = uuid.uuid4()
    cadence_id = uuid.uuid4()
    empty_cadence_id = uuid.uuid4()
    session = RecordingAsyncSession(
        FakeResult(
            all_values=[
                SimpleNamespace(id=cadence_id),
                SimpleNamespace(id=empty_cadence_id),
            ]
        ),
        FakeResult(
            all_values=[
                SimpleNamespace(
                    cadence_id=cadence_id,
                    total_leads=2,
                    leads_active=1,
                    leads_converted=1,
                )
            ]
        ),
    )

    result = await analytics_routes.get_cadences_overview(
        db=session,
        tenant_id=tenant_id,
    )

    by_id = {item.cadence_id: item for item in result}
    assert by_id[str(cadence_id)].total_leads == 2
    assert by_id[str(cadence_id)].leads_active == 1
    assert by_id[str(cadence_id)].leads_converted == 1
    assert by_id[str(empty_cadence_id)].total_leads == 0
    assert by_id[str(empty_cadence_id)].leads_active == 0
    assert by_id[str(empty_cadence_id)].leads_converted == 0


async def test_get_cadence_analytics_maps_counts_and_uses_days_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    cadence = _make_cadence(tenant_id)
    marker_since = datetime(2026, 3, 28, tzinfo=UTC)

    monkeypatch.setattr(analytics_routes, "_utc_days_ago", lambda days: marker_since)

    session = RecordingAsyncSession(
        FakeResult(scalar_one_or_none_value=cadence),
        FakeResult(scalar_value=5),
        FakeResult(scalar_value=4),
        FakeResult(one_value=SimpleNamespace(sent=2, replied=1, pending=1, skipped=0, failed=1)),
        FakeResult(
            all_values=[
                SimpleNamespace(
                    channel=Channel.EMAIL,
                    sent=1,
                    replied=0,
                    pending=1,
                    skipped=0,
                    failed=1,
                ),
                SimpleNamespace(
                    channel=Channel.LINKEDIN_DM,
                    sent=1,
                    replied=1,
                    pending=0,
                    skipped=0,
                    failed=0,
                ),
            ]
        ),
        FakeResult(
            all_values=[
                SimpleNamespace(
                    step_number=1,
                    channel=Channel.EMAIL,
                    sent=1,
                    replied=0,
                    pending=0,
                    skipped=0,
                    failed=0,
                ),
                SimpleNamespace(
                    step_number=2,
                    channel=Channel.LINKEDIN_DM,
                    sent=1,
                    replied=1,
                    pending=0,
                    skipped=0,
                    failed=0,
                ),
                SimpleNamespace(
                    step_number=3,
                    channel=Channel.EMAIL,
                    sent=0,
                    replied=0,
                    pending=1,
                    skipped=0,
                    failed=0,
                ),
                SimpleNamespace(
                    step_number=4,
                    channel=Channel.EMAIL,
                    sent=0,
                    replied=0,
                    pending=0,
                    skipped=0,
                    failed=1,
                ),
            ]
        ),
    )

    result = await analytics_routes.get_cadence_analytics(
        cadence_id=cadence.id,
        days=7,
        db=session,
        tenant_id=tenant_id,
    )

    assert result.cadence_id == str(cadence.id)
    assert result.total_leads == 5
    assert result.leads_active == 4
    assert result.steps_sent == 2
    assert result.replies == 1
    assert result.pending_steps == 1
    assert result.failed_steps == 1
    assert result.skipped_steps == 0
    assert result.reply_rate == 50.0

    channel_map = {item.channel: item for item in result.channel_breakdown}
    assert channel_map["email"].sent == 1
    assert channel_map["email"].pending == 1
    assert channel_map["email"].failed == 1
    assert channel_map["linkedin_dm"].replied == 1

    step_map = {(item.step_number, item.channel): item for item in result.step_breakdown}
    assert step_map[(1, "email")].sent == 1
    assert step_map[(2, "linkedin_dm")].reply_rate == 100.0
    assert step_map[(3, "email")].pending == 1
    assert step_map[(4, "email")].failed == 1

    assert _statement_contains_param(session.statements[3], marker_since)
    assert _statement_contains_param(session.statements[4], marker_since)
    assert _statement_contains_param(session.statements[5], marker_since)


async def test_get_cadence_analytics_raises_404_when_missing() -> None:
    tenant_id = uuid.uuid4()
    session = RecordingAsyncSession(FakeResult(scalar_one_or_none_value=None))

    with pytest.raises(HTTPException) as excinfo:
        await analytics_routes.get_cadence_analytics(
            cadence_id=uuid.uuid4(),
            db=session,
            tenant_id=tenant_id,
        )

    assert excinfo.value.status_code == 404


async def test_get_email_ab_results_maps_open_rates_and_uses_days_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker_since = datetime(2026, 3, 25, tzinfo=UTC)
    monkeypatch.setattr(analytics_routes, "_utc_days_ago", lambda days: marker_since)

    session = RecordingAsyncSession(
        FakeResult(
            all_values=[
                SimpleNamespace(subject_used="Variante A", sent=1),
                SimpleNamespace(subject_used="Variante B", sent=1),
            ]
        ),
        FakeResult(
            all_values=[
                SimpleNamespace(subject_used="Variante A", opened=1),
            ]
        ),
    )

    result = await analytics_routes.get_email_ab_results(
        cadence_id=uuid.uuid4(),
        step_number=1,
        days=7,
        db=session,
        tenant_id=uuid.uuid4(),
    )

    by_subject = {item.subject: item for item in result}
    assert by_subject["Variante A"].sent == 1
    assert by_subject["Variante A"].opened == 1
    assert by_subject["Variante A"].open_rate == 100.0
    assert by_subject["Variante B"].sent == 1
    assert by_subject["Variante B"].opened == 0
    assert by_subject["Variante B"].open_rate == 0.0

    assert _statement_contains_param(session.statements[0], marker_since)
    assert _statement_contains_param(session.statements[1], marker_since)
