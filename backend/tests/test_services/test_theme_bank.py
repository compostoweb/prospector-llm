"""
tests/test_services/test_theme_bank.py

Cobertura do seed versionado do banco de temas do Content Hub.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.content.theme_bank import (
    ALL_CONTENT_THEME_SEEDS,
    PUBLISHED_CONTENT_THEME_HISTORY,
    seed_theme_bank_for_tenant,
)

pytestmark = pytest.mark.asyncio


class _FakeScalarResult:
    def __init__(self, values: list[str]) -> None:
        self._values = values

    def all(self) -> list[str]:
        return self._values


class _FakeResult:
    def __init__(self, values: list[str]) -> None:
        self._values = values

    def scalars(self) -> _FakeScalarResult:
        return _FakeScalarResult(self._values)


def _make_db(existing_titles: list[str]) -> MagicMock:
    db = MagicMock()
    db.execute = AsyncMock(return_value=_FakeResult(existing_titles))
    db.add_all = MagicMock()
    return db


async def test_seed_theme_bank_for_tenant_creates_all_default_themes() -> None:
    tenant_id = uuid.uuid4()
    db = _make_db([])

    inserted = await seed_theme_bank_for_tenant(db, tenant_id)
    seeded_themes = db.add_all.call_args.args[0]

    assert inserted == len(ALL_CONTENT_THEME_SEEDS)
    assert len(seeded_themes) == len(ALL_CONTENT_THEME_SEEDS)
    assert sum(1 for theme in seeded_themes if theme.used) == len(PUBLISHED_CONTENT_THEME_HISTORY)
    assert all(theme.is_custom is False for theme in seeded_themes)
    assert all(theme.tenant_id == tenant_id for theme in seeded_themes)


async def test_seed_theme_bank_for_tenant_is_idempotent() -> None:
    db = _make_db([seed["title"] for seed in ALL_CONTENT_THEME_SEEDS])

    inserted = await seed_theme_bank_for_tenant(db, uuid.uuid4())

    assert inserted == 0
    db.add_all.assert_not_called()


async def test_seed_theme_bank_for_tenant_preserves_existing_titles() -> None:
    existing_title = ALL_CONTENT_THEME_SEEDS[0]["title"]
    db = _make_db([existing_title])

    inserted = await seed_theme_bank_for_tenant(db, uuid.uuid4())
    seeded_themes = db.add_all.call_args.args[0]
    seeded_titles = {theme.title for theme in seeded_themes}

    assert inserted == len(ALL_CONTENT_THEME_SEEDS) - 1
    assert len(seeded_themes) == len(ALL_CONTENT_THEME_SEEDS) - 1
    assert existing_title not in seeded_titles