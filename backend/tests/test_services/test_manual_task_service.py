from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any

import pytest
from sqlalchemy.sql import operators
from sqlalchemy.sql.elements import BinaryExpression, BooleanClauseList

from models.cadence import Cadence
from models.enums import Channel, ManualTaskStatus
from models.lead import Lead
from models.manual_task import ManualTask
from services.manual_task_service import ManualTaskService

pytestmark = pytest.mark.asyncio


class _FakeScalars:
    def __init__(self, items: list[Any]) -> None:
        self._items = items

    def all(self) -> list[Any]:
        return list(self._items)


class _FakeResult:
    def __init__(self, items: list[Any]) -> None:
        self._items = items

    def scalar(self) -> Any | None:
        if not self._items:
            return None
        return self._items[0]

    def scalar_one_or_none(self) -> Any | None:
        if not self._items:
            return None
        return self._items[0]

    def scalars(self) -> _FakeScalars:
        return _FakeScalars(self._items)


class FakeAsyncSession:
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
        col_desc = (
            statement.column_descriptions[0] if hasattr(statement, "column_descriptions") else {}
        )
        entity = col_desc.get("entity")
        candidates = (
            list(self._items.get(entity, [])) if entity else list(self._items.get(ManualTask, []))
        )

        for criterion in getattr(statement, "_where_criteria", ()):
            candidates = [item for item in candidates if _matches_criterion(item, criterion)]

        selected_columns = getattr(statement, "selected_columns", None)
        if selected_columns is not None and any(
            getattr(column, "name", None) == "count" for column in selected_columns
        ):
            return _FakeResult([len(candidates)])

        return _FakeResult(candidates)

    async def commit(self) -> None:
        pass

    async def refresh(self, obj: object) -> None:
        pass


def _matches_criterion(obj: object, criterion: object) -> bool:
    if isinstance(criterion, BooleanClauseList):
        return all(_matches_criterion(obj, clause) for clause in criterion.clauses)

    if not isinstance(criterion, BinaryExpression):
        return True

    field_name = getattr(criterion.left, "key", None) or getattr(criterion.left, "name", None)
    if not isinstance(field_name, str):
        return True

    current_value = getattr(obj, field_name, None)
    expected_value = getattr(criterion.right, "value", criterion.right)

    if criterion.operator is operators.eq:
        return current_value == expected_value
    if criterion.operator is operators.is_:
        return current_value is expected_value or current_value == expected_value
    if criterion.operator is operators.ge:
        return current_value >= expected_value
    if criterion.operator is operators.gt:
        return current_value > expected_value
    if criterion.operator is operators.le:
        return current_value <= expected_value
    if criterion.operator is operators.lt:
        return current_value < expected_value

    return True


def _make_lead(tenant_id: uuid.UUID) -> Lead:
    return Lead(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="Lead Manual",
        company="Acme",
        linkedin_url="https://linkedin.com/in/manual-task",
        source="manual",
    )


def _make_cadence(tenant_id: uuid.UUID) -> Cadence:
    return Cadence(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="Cadência Manual",
        is_active=True,
        llm_provider="openai",
        llm_model="gpt-5.4-mini",
        steps_template=[
            {"channel": "linkedin_connect", "step_number": 1},
            {"channel": "linkedin_dm", "step_number": 2},
            {"channel": "email", "step_number": 3},
            {"channel": "linkedin_dm", "step_number": 2},
        ],
    )


async def test_create_tasks_for_lead_deduplicates_existing_steps() -> None:
    service = ManualTaskService()
    db = FakeAsyncSession()
    tenant_id = uuid.uuid4()
    lead = _make_lead(tenant_id)
    cadence = _make_cadence(tenant_id)

    existing_task = ManualTask(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        cadence_id=cadence.id,
        lead_id=lead.id,
        channel=Channel.LINKEDIN_DM,
        step_number=2,
        status=ManualTaskStatus.PENDING,
    )
    db.add(existing_task)

    created = await service.create_tasks_for_lead(lead, cadence, db)

    assert len(created) == 1
    assert created[0].channel == Channel.EMAIL
    assert created[0].step_number == 3


async def test_get_task_rejects_task_from_other_tenant() -> None:
    service = ManualTaskService()
    db = FakeAsyncSession()
    tenant_id = uuid.uuid4()
    other_tenant_id = uuid.uuid4()
    lead = _make_lead(tenant_id)
    cadence = _make_cadence(tenant_id)
    task = ManualTask(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        cadence_id=cadence.id,
        lead_id=lead.id,
        channel=Channel.EMAIL,
        step_number=1,
        status=ManualTaskStatus.PENDING,
    )
    task.lead = lead
    task.cadence = cadence
    db.add(task)

    with pytest.raises(ValueError, match="não encontrada"):
        await service._get_task(task.id, db, tenant_id=other_tenant_id)


async def test_create_tasks_for_lead_ignores_manual_task_and_non_post_connect_channels() -> None:
    service = ManualTaskService()
    db = FakeAsyncSession()
    tenant_id = uuid.uuid4()
    lead = _make_lead(tenant_id)
    cadence = Cadence(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="Cadência Semi-manual",
        is_active=True,
        llm_provider="openai",
        llm_model="gpt-5.4-mini",
        steps_template=[
            {"channel": "linkedin_connect", "step_number": 1},
            {"channel": "manual_task", "step_number": 2},
            {"channel": "linkedin_post_comment", "step_number": 3},
            {"channel": "linkedin_dm", "step_number": 4},
            {"channel": "email", "step_number": 5},
        ],
    )

    created = await service.create_tasks_for_lead(lead, cadence, db)

    assert [(task.channel, task.step_number) for task in created] == [
        (Channel.LINKEDIN_DM, 4),
        (Channel.EMAIL, 5),
    ]


async def test_mark_done_external_updates_status_notes_and_sent_at() -> None:
    service = ManualTaskService()
    db = FakeAsyncSession()
    tenant_id = uuid.uuid4()
    lead = _make_lead(tenant_id)
    cadence = _make_cadence(tenant_id)
    task = ManualTask(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        cadence_id=cadence.id,
        lead_id=lead.id,
        channel=Channel.EMAIL,
        step_number=3,
        status=ManualTaskStatus.PENDING,
    )
    task.lead = lead
    task.cadence = cadence
    db.add(task)

    updated = await service.mark_done_external(
        task.id,
        tenant_id=tenant_id,
        notes="Feito manualmente pelo SDR após ligação.",
        db=db,
    )

    assert updated.status == ManualTaskStatus.DONE_EXTERNAL
    assert updated.notes == "Feito manualmente pelo SDR após ligação."
    assert updated.sent_at is not None


async def test_skip_updates_status_without_touching_notes() -> None:
    service = ManualTaskService()
    db = FakeAsyncSession()
    tenant_id = uuid.uuid4()
    lead = _make_lead(tenant_id)
    cadence = _make_cadence(tenant_id)
    task = ManualTask(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        cadence_id=cadence.id,
        lead_id=lead.id,
        channel=Channel.LINKEDIN_DM,
        step_number=2,
        status=ManualTaskStatus.CONTENT_GENERATED,
        notes="Gerado, mas não enviar nesta cadência.",
    )
    task.lead = lead
    task.cadence = cadence
    db.add(task)

    updated = await service.skip(task.id, tenant_id=tenant_id, db=db)

    assert updated.status == ManualTaskStatus.SKIPPED
    assert updated.notes == "Gerado, mas não enviar nesta cadência."
    assert updated.sent_at is None


async def test_reopen_done_external_restores_actionable_status_and_clears_execution_markers() -> (
    None
):
    service = ManualTaskService()
    db = FakeAsyncSession()
    tenant_id = uuid.uuid4()
    lead = _make_lead(tenant_id)
    cadence = _make_cadence(tenant_id)
    task = ManualTask(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        cadence_id=cadence.id,
        lead_id=lead.id,
        channel=Channel.EMAIL,
        step_number=3,
        status=ManualTaskStatus.DONE_EXTERNAL,
        edited_text="Texto final aprovado.",
        notes="Marcada como feita por engano.",
        sent_at=datetime.now(tz=UTC),
    )
    task.lead = lead
    task.cadence = cadence
    db.add(task)

    updated = await service.reopen(task.id, tenant_id=tenant_id, db=db)

    assert updated.status == ManualTaskStatus.CONTENT_GENERATED
    assert updated.sent_at is None
    assert updated.notes is None


async def test_reopen_without_text_returns_task_to_pending() -> None:
    service = ManualTaskService()
    db = FakeAsyncSession()
    tenant_id = uuid.uuid4()
    lead = _make_lead(tenant_id)
    cadence = _make_cadence(tenant_id)
    task = ManualTask(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        cadence_id=cadence.id,
        lead_id=lead.id,
        channel=Channel.LINKEDIN_DM,
        step_number=2,
        status=ManualTaskStatus.SKIPPED,
    )
    task.lead = lead
    task.cadence = cadence
    db.add(task)

    updated = await service.reopen(task.id, tenant_id=tenant_id, db=db)

    assert updated.status == ManualTaskStatus.PENDING
    assert updated.sent_at is None


async def test_get_stats_counts_skipped_with_date_range() -> None:
    service = ManualTaskService()
    db = FakeAsyncSession()
    tenant_id = uuid.uuid4()
    lead = _make_lead(tenant_id)
    cadence = _make_cadence(tenant_id)

    first_task = ManualTask(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        cadence_id=cadence.id,
        lead_id=lead.id,
        channel=Channel.EMAIL,
        step_number=2,
        status=ManualTaskStatus.SKIPPED,
        created_at=datetime(2026, 4, 8, tzinfo=UTC),
    )
    second_task = ManualTask(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        cadence_id=cadence.id,
        lead_id=lead.id,
        channel=Channel.EMAIL,
        step_number=3,
        status=ManualTaskStatus.SKIPPED,
        created_at=datetime(2026, 4, 22, tzinfo=UTC),
    )
    first_task.lead = lead
    first_task.cadence = cadence
    second_task.lead = lead
    second_task.cadence = cadence
    db.add(first_task)
    db.add(second_task)

    stats = await service.get_stats(
        tenant_id=tenant_id,
        db=db,
        start_date=date(2026, 4, 20),
        end_date=date(2026, 4, 23),
    )

    assert stats["skipped"] == 1
