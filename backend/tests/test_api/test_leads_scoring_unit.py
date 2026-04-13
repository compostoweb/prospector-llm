from __future__ import annotations

import inspect
import uuid
from typing import Any, get_args, get_type_hints

import pytest

from api.routes import leads as leads_route
from models.enums import LeadSource, LeadStatus
from models.lead import Lead
from schemas.lead import LeadCreateRequest, LeadUpdateRequest


class _FakeScalars:
    def __init__(self, items: list[Any]) -> None:
        self._items = items

    def all(self) -> list[Any]:
        return list(self._items)


class _FakeResult:
    def __init__(self, items: list[Any]) -> None:
        self._items = items

    def scalar_one_or_none(self) -> Any | None:
        if not self._items:
            return None
        return self._items[0]

    def scalars(self) -> _FakeScalars:
        return _FakeScalars(self._items)


class FakeAsyncSession:
    def __init__(self) -> None:
        self.items: list[Any] = []

    async def execute(self, statement: Any) -> _FakeResult:
        return _FakeResult([])

    def add(self, obj: Any) -> None:
        self.items.append(obj)

    async def commit(self) -> None:
        pass

    async def refresh(self, obj: Any) -> None:
        pass


def _make_lead(tenant_id: uuid.UUID) -> Lead:
    lead = Lead(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="João Silva",
        company="Acme Corp",
        linkedin_url="https://linkedin.com/in/score-unit-test",
        source=LeadSource.MANUAL,
        status=LeadStatus.RAW,
    )
    lead.lists = []
    return lead


@pytest.mark.asyncio
async def test_create_lead_sets_initial_score(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.uuid4()
    db = FakeAsyncSession()

    async def _fake_get_lead_with_lists(
        lead_id: uuid.UUID,
        tenant_id_arg: uuid.UUID,
        session: FakeAsyncSession,
    ) -> Lead | None:
        assert tenant_id_arg == tenant_id
        assert session is db
        return next((item for item in db.items if isinstance(item, Lead) and item.id == lead_id), None)

    monkeypatch.setattr(leads_route, "get_lead_with_lists", _fake_get_lead_with_lists)
    monkeypatch.setattr(leads_route, "serialize_lead", lambda lead: lead)

    result = await leads_route.create_lead(
        body=LeadCreateRequest(
            name="João Silva",
            company="Acme Corp",
            website="https://acme.com",
            linkedin_url="https://linkedin.com/in/score-create-test",
            source=LeadSource.MANUAL,
        ),
        enrich=False,
        tenant_id=tenant_id,
        db=db,
    )

    assert isinstance(result, Lead)
    assert result.score == 40.0


@pytest.mark.asyncio
async def test_update_lead_recalculates_score_for_score_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    db = FakeAsyncSession()
    lead = _make_lead(tenant_id)
    lead.website = None
    lead.segment = None
    lead.city = None
    lead.email_corporate = None
    lead.score = 30.0

    async def _fake_get_lead_or_404(
        lead_id: uuid.UUID,
        tenant_id_arg: uuid.UUID,
        session: FakeAsyncSession,
    ) -> Lead:
        assert lead_id == lead.id
        assert tenant_id_arg == tenant_id
        assert session is db
        return lead

    monkeypatch.setattr(leads_route, "_get_lead_or_404", _fake_get_lead_or_404)
    monkeypatch.setattr(leads_route, "serialize_lead", lambda current: current)

    result = await leads_route.update_lead(
        lead_id=lead.id,
        body=LeadUpdateRequest(
            email_corporate="joao@acme.com",
            website="https://acme.com",
            city="São Paulo",
            segment="SaaS",
        ),
        tenant_id=tenant_id,
        db=db,
    )

    assert isinstance(result, Lead)
    assert result.score == 80.0


def test_list_leads_accepts_min_score_up_to_100() -> None:
    signature = inspect.signature(leads_route.list_leads)
    annotation = get_type_hints(leads_route.list_leads, include_extras=True)["min_score"]
    query_info = get_args(annotation)[1]
    assert signature.parameters["min_score"].name == "min_score"
    le_constraint = next(item for item in query_info.metadata if hasattr(item, "le"))
    assert le_constraint.le == 100.0