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
from typing import Any, Protocol, cast

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

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

    def scalars(self) -> FakeResult:
        return self


class CompilableStatement(Protocol):
    def compile(self, *args: Any, **kwargs: Any) -> Any: ...


class FakeAsyncSession:
    def __init__(self, *results: FakeResult) -> None:
        self._results = list(results)
        self.statements: list[CompilableStatement] = []

    async def execute(  # pyright: ignore[reportIncompatibleMethodOverride]
        self, statement: CompilableStatement, *args: Any, **kwargs: Any
    ) -> FakeResult:
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
        llm_model="gpt-5.4-mini",
        llm_temperature=0.7,
        llm_max_tokens=512,
    )


def _statement_contains_param(statement: CompilableStatement, expected: object) -> bool:
    compiled = statement.compile()
    return expected in compiled.params.values()


def _statement_param_count(statement: CompilableStatement, expected: object) -> int:
    compiled = statement.compile()
    return sum(1 for value in compiled.params.values() if value == expected)


def _compiled_sql(statement: CompilableStatement) -> str:
    return str(statement.compile())


async def test_get_cadences_overview_returns_real_metrics() -> None:
    tenant_id = uuid.uuid4()
    cadence_id = uuid.uuid4()
    empty_cadence_id = uuid.uuid4()
    cadence = _make_cadence(tenant_id, cadence_id)
    empty_cadence = _make_cadence(tenant_id, empty_cadence_id)
    session = FakeAsyncSession(
        FakeResult(
            all_values=[
                cadence,
                empty_cadence,
            ]
        ),
        FakeResult(
            all_values=[
                SimpleNamespace(
                    cadence_id=cadence_id,
                    total_leads=2,
                    leads_active=1,
                    leads_converted=1,
                    leads_finished=1,
                    replies=3,
                    leads_paused=1,
                )
            ]
        ),
    )

    original_sync = analytics_routes._sync_cadence_list_members
    analytics_routes._sync_cadence_list_members = _fake_sync_cadence_list_members
    try:
        result = await analytics_routes.get_cadences_overview(
            db=cast(AsyncSession, session),
            tenant_id=tenant_id,
        )
    finally:
        analytics_routes._sync_cadence_list_members = original_sync

    by_id = {item.cadence_id: item for item in result}
    assert by_id[str(cadence_id)].total_leads == 2
    assert by_id[str(cadence_id)].leads_active == 1
    assert by_id[str(cadence_id)].leads_converted == 1
    assert by_id[str(cadence_id)].leads_finished == 1
    assert by_id[str(cadence_id)].replies == 3
    assert by_id[str(cadence_id)].leads_paused == 1
    assert by_id[str(empty_cadence_id)].total_leads == 0
    assert by_id[str(empty_cadence_id)].leads_active == 0
    assert by_id[str(empty_cadence_id)].leads_converted == 0
    assert by_id[str(empty_cadence_id)].leads_finished == 0
    assert by_id[str(empty_cadence_id)].replies == 0
    assert by_id[str(empty_cadence_id)].leads_paused == 0


async def test_get_cadence_analytics_maps_counts_and_uses_days_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    cadence = _make_cadence(tenant_id)
    marker_since = datetime(2026, 3, 28, tzinfo=UTC)

    monkeypatch.setattr(analytics_routes, "_utc_days_ago", lambda days: marker_since)
    monkeypatch.setattr(
        analytics_routes, "_sync_cadence_list_members", _fake_sync_cadence_list_members
    )

    session = FakeAsyncSession(
        FakeResult(scalar_one_or_none_value=cadence),
        FakeResult(scalar_value=5),
        FakeResult(scalar_value=4),
        FakeResult(one_value=SimpleNamespace(sent=3, pending=1, skipped=0, failed=1)),
        FakeResult(one_value=SimpleNamespace(replied=1)),
        FakeResult(
            all_values=[
                SimpleNamespace(
                    channel=Channel.EMAIL,
                    sent=1,
                    pending=1,
                    skipped=0,
                    failed=1,
                ),
                SimpleNamespace(
                    channel=Channel.LINKEDIN_DM,
                    sent=1,
                    pending=0,
                    skipped=0,
                    failed=0,
                ),
                SimpleNamespace(
                    channel=Channel.LINKEDIN_CONNECT,
                    sent=1,
                    pending=0,
                    skipped=0,
                    failed=0,
                ),
            ]
        ),
        FakeResult(
            all_values=[
                SimpleNamespace(channel=Channel.LINKEDIN_DM, replied=1),
            ]
        ),
        FakeResult(
            all_values=[
                SimpleNamespace(channel=Channel.EMAIL, opened=1),
            ]
        ),
        FakeResult(
            all_values=[
                SimpleNamespace(channel=Channel.LINKEDIN_CONNECT, accepted=1),
            ]
        ),
        FakeResult(
            all_values=[
                SimpleNamespace(
                    step_number=1,
                    channel=Channel.EMAIL,
                    sent=1,
                    pending=0,
                    skipped=0,
                    failed=0,
                ),
                SimpleNamespace(
                    step_number=2,
                    channel=Channel.LINKEDIN_DM,
                    sent=1,
                    pending=0,
                    skipped=0,
                    failed=0,
                ),
                SimpleNamespace(
                    step_number=3,
                    channel=Channel.EMAIL,
                    sent=0,
                    pending=1,
                    skipped=0,
                    failed=0,
                ),
                SimpleNamespace(
                    step_number=4,
                    channel=Channel.EMAIL,
                    sent=0,
                    pending=0,
                    skipped=0,
                    failed=1,
                ),
                SimpleNamespace(
                    step_number=5,
                    channel=Channel.LINKEDIN_CONNECT,
                    sent=1,
                    pending=0,
                    skipped=0,
                    failed=0,
                ),
            ]
        ),
        FakeResult(
            all_values=[
                SimpleNamespace(step_number=2, channel=Channel.LINKEDIN_DM, replied=1),
            ]
        ),
        FakeResult(
            all_values=[
                SimpleNamespace(step_number=1, channel=Channel.EMAIL, opened=1),
            ]
        ),
        FakeResult(
            all_values=[
                SimpleNamespace(step_number=1, channel=Channel.EMAIL, bounced=1),
            ]
        ),
        FakeResult(
            all_values=[
                SimpleNamespace(step_number=5, channel=Channel.LINKEDIN_CONNECT, accepted=1),
            ]
        ),
    )

    result = await analytics_routes.get_cadence_analytics(
        cadence_id=cadence.id,
        days=7,
        db=cast(AsyncSession, session),
        tenant_id=tenant_id,
    )

    assert result.cadence_id == str(cadence.id)
    assert result.total_leads == 5
    assert result.leads_active == 4
    assert result.steps_sent == 3
    assert result.replies == 1
    assert result.pending_steps == 1
    assert result.failed_steps == 1
    assert result.skipped_steps == 0
    assert result.reply_rate == 33.3

    channel_map = {item.channel: item for item in result.channel_breakdown}
    assert channel_map["email"].sent == 1
    assert channel_map["email"].pending == 1
    assert channel_map["email"].failed == 1
    assert channel_map["email"].open_rate == 100.0
    assert channel_map["linkedin_dm"].replied == 1
    assert channel_map["linkedin_connect"].accepted == 1
    assert channel_map["linkedin_connect"].acceptance_rate == 100.0

    step_map = {(item.step_number, item.channel): item for item in result.step_breakdown}
    assert step_map[(1, "email")].sent == 1
    assert step_map[(1, "email")].lead_count == 1
    assert step_map[(1, "email")].open_rate == 100.0
    assert step_map[(1, "email")].bounced == 1
    assert step_map[(2, "linkedin_dm")].reply_rate == 100.0
    assert step_map[(3, "email")].pending == 1
    assert step_map[(4, "email")].failed == 1
    assert step_map[(5, "linkedin_connect")].accepted == 1
    assert step_map[(5, "linkedin_connect")].acceptance_rate == 100.0

    for index in range(3, 14):
        assert _statement_contains_param(session.statements[index], marker_since)
    assert _statement_contains_param(session.statements[4], "fallback_single_cadence")
    assert _statement_contains_param(session.statements[6], "fallback_single_cadence")
    assert _statement_contains_param(session.statements[10], "fallback_single_cadence")


async def test_get_cadence_analytics_raises_404_when_missing() -> None:
    tenant_id = uuid.uuid4()
    session = FakeAsyncSession(FakeResult(scalar_one_or_none_value=None))

    with pytest.raises(HTTPException) as excinfo:
        await analytics_routes.get_cadence_analytics(
            cadence_id=uuid.uuid4(),
            db=cast(AsyncSession, session),
            tenant_id=tenant_id,
        )

    assert excinfo.value.status_code == 404


async def test_get_cadence_analytics_syncs_legacy_list_members_before_counting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    cadence = _make_cadence(tenant_id)
    cadence.lead_list_id = uuid.uuid4()
    synced: list[uuid.UUID] = []

    async def _fake_sync(current_cadence: Cadence, db: AsyncSession) -> int:
        synced.append(current_cadence.id)
        return 1

    monkeypatch.setattr(analytics_routes, "_sync_cadence_list_members", _fake_sync)

    session = FakeAsyncSession(
        FakeResult(scalar_one_or_none_value=cadence),
        FakeResult(scalar_value=1),
        FakeResult(scalar_value=1),
        FakeResult(one_value=SimpleNamespace(sent=0, pending=1, skipped=0, failed=0)),
        FakeResult(one_value=SimpleNamespace(replied=0)),
        FakeResult(all_values=[]),
        FakeResult(all_values=[]),
        FakeResult(all_values=[]),
        FakeResult(all_values=[]),
        FakeResult(all_values=[]),
        FakeResult(all_values=[]),
        FakeResult(all_values=[]),
        FakeResult(all_values=[]),
        FakeResult(all_values=[]),
    )

    result = await analytics_routes.get_cadence_analytics(
        cadence_id=cadence.id,
        days=30,
        db=cast(AsyncSession, session),
        tenant_id=tenant_id,
    )

    assert synced == [cadence.id]
    assert result.total_leads == 1
    assert result.leads_active == 1


async def _fake_sync_cadence_list_members(cadence: Cadence, db: AsyncSession) -> int:
    return 0


async def test_get_cadences_overview_syncs_legacy_list_members_before_aggregating(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    cadence_id = uuid.uuid4()
    cadence = _make_cadence(tenant_id, cadence_id)
    cadence.lead_list_id = uuid.uuid4()
    synced: list[uuid.UUID] = []

    async def _fake_sync(current_cadence: Cadence, db: AsyncSession) -> int:
        synced.append(current_cadence.id)
        return 1

    monkeypatch.setattr(analytics_routes, "_sync_cadence_list_members", _fake_sync)

    session = FakeAsyncSession(
        FakeResult(all_values=[cadence]),
        FakeResult(
            all_values=[
                SimpleNamespace(
                    cadence_id=cadence_id,
                    total_leads=1,
                    leads_active=1,
                    leads_converted=0,
                    leads_finished=0,
                    replies=0,
                    leads_paused=0,
                )
            ]
        ),
    )

    result = await analytics_routes.get_cadences_overview(
        db=cast(AsyncSession, session),
        tenant_id=tenant_id,
    )

    assert synced == [cadence_id]
    assert result[0].cadence_id == str(cadence_id)
    assert result[0].total_leads == 1


async def test_get_email_ab_results_maps_open_rates_and_uses_days_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker_since = datetime(2026, 3, 25, tzinfo=UTC)
    monkeypatch.setattr(analytics_routes, "_utc_days_ago", lambda days: marker_since)

    session = FakeAsyncSession(
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
        db=cast(AsyncSession, session),
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
    assert _statement_contains_param(session.statements[0], "email_only")
    assert _statement_contains_param(session.statements[1], "email_only")


async def test_get_email_stats_filters_to_email_only_cadences(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker_since = datetime(2026, 3, 25, tzinfo=UTC)
    monkeypatch.setattr(analytics_routes, "_utc_days_ago", lambda days: marker_since)

    session = FakeAsyncSession(
        FakeResult(scalar_value=5),
        FakeResult(scalar_value=2),
        FakeResult(scalar_value=3),
        FakeResult(scalar_value=1),
        FakeResult(scalar_value=1),
    )

    result = await analytics_routes.get_email_stats(
        days=7,
        db=cast(AsyncSession, session),
        tenant_id=uuid.uuid4(),
    )

    assert result.sent == 5
    assert result.opened == 2
    assert result.replied == 3
    assert result.unsubscribed == 1
    assert result.bounced == 1
    assert result.open_rate == 40.0
    assert result.reply_rate == 60.0

    for statement in session.statements:
        assert _statement_contains_param(statement, marker_since)
        assert _statement_contains_param(statement, "email_only")

    assert "cadence_steps.id = interactions.cadence_step_id" in _compiled_sql(session.statements[0])
    assert "cadence_steps.id = interactions.cadence_step_id" in _compiled_sql(session.statements[1])
    assert "cadence_steps.id = interactions.cadence_step_id" in _compiled_sql(session.statements[2])
    assert _statement_contains_param(session.statements[2], "fallback_single_cadence")


async def test_get_email_cadences_stats_filters_to_email_only_cadences(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker_since = datetime(2026, 3, 25, tzinfo=UTC)
    monkeypatch.setattr(analytics_routes, "_utc_days_ago", lambda days: marker_since)

    cadence_id = uuid.uuid4()
    session = FakeAsyncSession(
        FakeResult(all_values=[SimpleNamespace(cadence_id=cadence_id, sent=5)]),
        FakeResult(all_values=[SimpleNamespace(id=cadence_id, name="Cold Email Puro")]),
        FakeResult(all_values=[SimpleNamespace(cadence_id=cadence_id, opened=2)]),
        FakeResult(all_values=[SimpleNamespace(cadence_id=cadence_id, replied=3)]),
        FakeResult(all_values=[SimpleNamespace(cadence_id=cadence_id, bounced=1)]),
    )

    result = await analytics_routes.get_email_cadences_stats(
        days=7,
        db=cast(AsyncSession, session),
        tenant_id=uuid.uuid4(),
    )

    assert result == [
        analytics_routes.EmailCadenceItem(
            cadence_id=str(cadence_id),
            cadence_name="Cold Email Puro",
            sent=5,
            opened=2,
            replied=3,
            bounced=1,
            open_rate=40.0,
            reply_rate=60.0,
        )
    ]

    assert _statement_contains_param(session.statements[0], marker_since)
    assert _statement_contains_param(session.statements[0], "email_only")
    assert _statement_contains_param(session.statements[2], "email_only")
    assert _statement_contains_param(session.statements[3], "email_only")
    assert _statement_contains_param(session.statements[4], "email_only")
    assert _statement_contains_param(session.statements[3], "fallback_single_cadence")
    assert "interactions" in _compiled_sql(session.statements[2]).lower()
    assert "cadence_steps" in _compiled_sql(session.statements[2]).lower()
    assert "interactions" in _compiled_sql(session.statements[3]).lower()
    assert "cadence_steps" in _compiled_sql(session.statements[3]).lower()


async def test_get_email_over_time_maps_daily_series_and_inlines_day_bucket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker_since = datetime(2026, 3, 20, tzinfo=UTC)
    monkeypatch.setattr(analytics_routes, "_utc_days_ago", lambda days: marker_since)

    session = FakeAsyncSession(
        FakeResult(
            all_values=[
                SimpleNamespace(day=datetime(2026, 3, 25, tzinfo=UTC), cnt=3),
                SimpleNamespace(day=datetime(2026, 3, 26, tzinfo=UTC), cnt=1),
            ]
        ),
        FakeResult(
            all_values=[
                SimpleNamespace(day=datetime(2026, 3, 25, tzinfo=UTC), cnt=2),
            ]
        ),
        FakeResult(
            all_values=[
                SimpleNamespace(day=datetime(2026, 3, 26, tzinfo=UTC), cnt=1),
            ]
        ),
    )

    result = await analytics_routes.get_email_over_time(
        days=7,
        db=cast(AsyncSession, session),
        tenant_id=uuid.uuid4(),
    )

    assert result == [
        analytics_routes.EmailOverTimeItem(date="2026-03-25", sent=3, opened=2, replied=0),
        analytics_routes.EmailOverTimeItem(date="2026-03-26", sent=1, opened=0, replied=1),
    ]

    assert _statement_contains_param(session.statements[0], marker_since)
    assert _statement_contains_param(session.statements[1], marker_since)
    assert _statement_contains_param(session.statements[2], marker_since)
    assert _statement_contains_param(session.statements[0], "email_only")
    assert _statement_contains_param(session.statements[1], "email_only")
    assert _statement_contains_param(session.statements[2], "email_only")
    assert _statement_contains_param(session.statements[2], "fallback_single_cadence")
    assert _statement_param_count(session.statements[0], "day") == 0
    assert _statement_param_count(session.statements[1], "day") == 0
    assert _statement_param_count(session.statements[2], "day") == 0
    assert "cadence_steps.id = interactions.cadence_step_id" in _compiled_sql(session.statements[0])
    assert "cadence_steps.id = interactions.cadence_step_id" in _compiled_sql(session.statements[1])
    assert "cadence_steps.id = interactions.cadence_step_id" in _compiled_sql(session.statements[2])


async def test_dashboard_channel_recent_and_intent_queries_ignore_low_confidence_email_replies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker_today = datetime(2026, 4, 22, tzinfo=UTC)
    marker_week = datetime(2026, 4, 15, tzinfo=UTC)
    marker_period = datetime(2026, 4, 1, tzinfo=UTC)

    def _fake_days_ago(days: int) -> datetime:
        if days == 7:
            return marker_week
        if days == 30:
            return marker_period
        if days == 60:
            return datetime(2026, 3, 1, tzinfo=UTC)
        raise AssertionError(f"Unexpected days value: {days}")

    monkeypatch.setattr(analytics_routes, "_utc_start_of_today", lambda: marker_today)
    monkeypatch.setattr(analytics_routes, "_utc_days_ago", _fake_days_ago)

    tenant_id = uuid.uuid4()

    dashboard_session = FakeAsyncSession(
        FakeResult(one_value=SimpleNamespace(total=10, in_cadence=4, converted=1, archived=0)),
        FakeResult(one_value=SimpleNamespace(current=3, previous=2)),
        FakeResult(one_value=SimpleNamespace(today=2, week=5, period=9, prev_period=7)),
        FakeResult(one_value=SimpleNamespace(today=1, week=2, period=3, prev_period=1)),
        FakeResult(one_value=SimpleNamespace(current=2, previous=1)),
    )
    dashboard = await analytics_routes.get_dashboard_stats(
        days=30,
        db=cast(AsyncSession, dashboard_session),
        tenant_id=tenant_id,
    )
    assert dashboard.replies_period == 3
    assert _statement_contains_param(dashboard_session.statements[3], "fallback_single_cadence")

    channel_session = FakeAsyncSession(
        FakeResult(all_values=[SimpleNamespace(channel=Channel.EMAIL, sent=5)]),
        FakeResult(all_values=[SimpleNamespace(channel=Channel.EMAIL, replies=1)]),
    )
    channels = await analytics_routes.get_channel_breakdown(
        days=30,
        db=cast(AsyncSession, channel_session),
        tenant_id=tenant_id,
    )
    assert channels[0].replies == 1
    assert _statement_contains_param(channel_session.statements[1], "fallback_single_cadence")

    recent_session = FakeAsyncSession(
        FakeResult(
            all_values=[
                SimpleNamespace(
                    id=uuid.uuid4(),
                    channel=Channel.EMAIL,
                    intent=None,
                    created_at=marker_today,
                    lead_id=uuid.uuid4(),
                    lead_name="Adriano",
                    company_name="Composto Web",
                )
            ]
        )
    )
    recent = await analytics_routes.get_recent_replies(
        limit=5,
        db=cast(AsyncSession, recent_session),
        tenant_id=tenant_id,
    )
    assert recent[0].lead_name == "Adriano"
    assert _statement_contains_param(recent_session.statements[0], "fallback_single_cadence")

    intent_session = FakeAsyncSession(
        FakeResult(all_values=[SimpleNamespace(intent=SimpleNamespace(value="neutral"), cnt=2)])
    )
    intents = await analytics_routes.get_intent_breakdown(
        days=30,
        db=cast(AsyncSession, intent_session),
        tenant_id=tenant_id,
    )
    assert intents[0].count == 2
    assert _statement_contains_param(intent_session.statements[0], "fallback_single_cadence")


async def test_get_email_ab_results_joins_outbound_opened_by_cadence_step_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker_since = datetime(2026, 3, 25, tzinfo=UTC)
    monkeypatch.setattr(analytics_routes, "_utc_days_ago", lambda days: marker_since)

    session = FakeAsyncSession(
        FakeResult(all_values=[SimpleNamespace(subject_used="Variante A", sent=1)]),
        FakeResult(all_values=[SimpleNamespace(subject_used="Variante A", opened=1)]),
    )

    await analytics_routes.get_email_ab_results(
        cadence_id=uuid.uuid4(),
        step_number=1,
        days=7,
        db=cast(AsyncSession, session),
        tenant_id=uuid.uuid4(),
    )

    assert "interactions.cadence_step_id = cadence_steps.id" in _compiled_sql(session.statements[1])
