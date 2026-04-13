from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest

from api.webhooks import unipile as unipile_webhook
from models.cadence import Cadence
from models.cadence_step import CadenceStep
from models.enums import Channel, LeadSource, LeadStatus, StepStatus
from models.lead import Lead

pytestmark = pytest.mark.asyncio


class _FakeScalarSequence:
    def __init__(self, values: list[object]) -> None:
        self._values = values

    def all(self) -> list[object]:
        return self._values


class _FakeResult:
    def __init__(self, value: object | None = None, values: list[object] | None = None) -> None:
        self._value = value
        self._values = values or []

    def scalar_one_or_none(self) -> object | None:
        return self._value

    def scalars(self) -> _FakeScalarSequence:
        return _FakeScalarSequence(self._values)


class _FakeAsyncSession:
    def __init__(self, *results: _FakeResult) -> None:
        self._results = list(results)
        self.statements: list[Any] = []

    async def execute(self, statement: Any) -> _FakeResult:
        self.statements.append(statement)
        if not self._results:
            raise AssertionError("Unexpected execute() call without fake result")
        return self._results.pop(0)


def _make_cadence(tenant_id: uuid.UUID) -> Cadence:
    return Cadence(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="Cadência Teste",
        llm_provider="openai",
        llm_model="gpt-4o-mini",
        llm_temperature=0.7,
        llm_max_tokens=512,
    )


def _make_lead(
    tenant_id: uuid.UUID,
    *,
    email_corporate: str | None = None,
    linkedin_profile_id: str | None = None,
) -> Lead:
    return Lead(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="Lead Teste",
        company="Acme",
        linkedin_url=f"https://linkedin.com/in/{uuid.uuid4().hex[:10]}",
        linkedin_profile_id=linkedin_profile_id,
        email_corporate=email_corporate,
        source=LeadSource.MANUAL,
        status=LeadStatus.IN_CADENCE,
    )


def _make_step(
    tenant_id: uuid.UUID,
    lead_id: uuid.UUID,
    cadence_id: uuid.UUID,
    *,
    channel: Channel,
    status: StepStatus,
    sent_at: datetime | None,
) -> CadenceStep:
    return CadenceStep(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        lead_id=lead_id,
        cadence_id=cadence_id,
        channel=channel,
        step_number=1,
        day_offset=0,
        scheduled_at=datetime.now(tz=UTC),
        status=status,
        sent_at=sent_at,
    )


def _compiled_params(statement: Any) -> dict[str, object]:
    return statement.compile().params


async def test_resolve_tenant_id_for_account_uses_tenant_integration() -> None:
    tenant_id = uuid.uuid4()
    db = _FakeAsyncSession(_FakeResult(values=[tenant_id]))
    session = cast(Any, db)

    resolved = await unipile_webhook._resolve_tenant_id_for_unipile_account(
        "linkedin-account-123",
        session,
    )

    assert resolved == tenant_id
    params = _compiled_params(db.statements[0])
    assert "linkedin-account-123" in params.values()


async def test_find_lead_by_sender_is_scoped_by_tenant() -> None:
    tenant_id = uuid.uuid4()
    lead = _make_lead(tenant_id, email_corporate="contato@empresa.com")
    db = _FakeAsyncSession(
        _FakeResult(None),
        _FakeResult(lead),
    )
    session = cast(Any, db)

    found = await unipile_webhook._find_lead_by_sender(
        "contato@empresa.com",
        tenant_id,
        session,
    )

    assert found is lead
    assert len(db.statements) == 2
    for statement in db.statements:
        assert tenant_id in _compiled_params(statement).values()


async def test_mark_latest_step_replied_updates_most_recent_matching_step() -> None:
    tenant_id = uuid.uuid4()
    cadence = _make_cadence(tenant_id)
    lead = _make_lead(tenant_id, email_corporate="lead@empresa.com")

    older_step = _make_step(
        tenant_id,
        lead.id,
        cadence.id,
        channel=Channel.EMAIL,
        status=StepStatus.SENT,
        sent_at=datetime.now(tz=UTC) - timedelta(days=1),
    )
    newer_step = _make_step(
        tenant_id,
        lead.id,
        cadence.id,
        channel=Channel.EMAIL,
        status=StepStatus.SENT,
        sent_at=datetime.now(tz=UTC),
    )
    db = _FakeAsyncSession(_FakeResult(newer_step))
    session = cast(Any, db)

    await unipile_webhook._mark_latest_step_replied(
        lead_id=lead.id,
        tenant_id=tenant_id,
        channel=Channel.EMAIL,
        db=session,
    )

    assert older_step.status == StepStatus.SENT
    assert newer_step.status == StepStatus.REPLIED
    params = _compiled_params(db.statements[0])
    assert tenant_id in params.values()
    assert lead.id in params.values()
    assert Channel.EMAIL in params.values()
    assert StepStatus.SENT in params.values()


async def test_verify_signature_accepts_custom_auth_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(unipile_webhook.settings, "UNIPILE_WEBHOOK_SECRET", "secret-123")
    monkeypatch.setattr(unipile_webhook.settings, "ENV", "prod")

    assert unipile_webhook._verify_signature(
        b"{}",
        signature_header="",
        custom_auth_header="secret-123",
    )
