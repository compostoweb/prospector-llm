from __future__ import annotations

import uuid
from typing import Any, Protocol, cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from services import cadence_step_eligibility

pytestmark = pytest.mark.asyncio


class FakeResult:
    def __init__(self, scalar_one_or_none_value: object | None) -> None:
        self._scalar_one_or_none_value = scalar_one_or_none_value

    def scalar_one_or_none(self) -> object | None:
        return self._scalar_one_or_none_value


class CompilableStatement(Protocol):
    def compile(self, *args: Any, **kwargs: Any) -> Any: ...


class FakeAsyncSession:
    def __init__(self, result: FakeResult) -> None:
        self.result = result
        self.statements: list[CompilableStatement] = []

    async def execute(  # pyright: ignore[reportIncompatibleMethodOverride]
        self, statement: CompilableStatement, *args: Any, **kwargs: Any
    ) -> FakeResult:
        self.statements.append(statement)
        return self.result


def _statement_contains_param(statement: CompilableStatement, expected: object) -> bool:
    compiled = statement.compile()
    return expected in compiled.params.values()


async def test_lead_has_replied_in_cadence_only_considers_reliable_replies() -> None:
    session = FakeAsyncSession(FakeResult(None))

    result = await cadence_step_eligibility._lead_has_replied_in_cadence(
        db=cast(AsyncSession, session),
        lead_id=uuid.uuid4(),
        cadence_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
    )

    assert result is False
    assert _statement_contains_param(session.statements[0], "fallback_single_cadence")
