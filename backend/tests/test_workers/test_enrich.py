# pyright: reportPrivateUsage=false

from __future__ import annotations

import os
from types import SimpleNamespace
from typing import Any, cast

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/testdb")
os.environ.setdefault("SECRET_KEY", "test-secret")

from models.enums import ContactQualityBucket, LeadStatus
from workers.enrich import (
    _assess_phone_quality,
    _companies_match,
    _resolve_linkedin_crosscheck,
    _status_after_enrichment,
)


def test_status_after_enrichment_preserves_in_cadence() -> None:
    assert _status_after_enrichment(LeadStatus.IN_CADENCE) == LeadStatus.IN_CADENCE


def test_status_after_enrichment_promotes_raw_to_enriched() -> None:
    assert _status_after_enrichment(LeadStatus.RAW) == LeadStatus.ENRICHED


def test_status_after_enrichment_preserves_terminal_statuses() -> None:
    assert _status_after_enrichment(LeadStatus.CONVERTED) == LeadStatus.CONVERTED
    assert _status_after_enrichment(LeadStatus.ARCHIVED) == LeadStatus.ARCHIVED


def test_companies_match_handles_contains_logic() -> None:
    assert _companies_match("Acme", "Acme Ltda") is True
    assert _companies_match("Acme Labs", "Beta Labs") is False
    assert _companies_match(None, "Acme") is None


async def test_resolve_linkedin_crosscheck_updates_profile_and_company(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from core.config import settings as app_settings

    monkeypatch.setattr(app_settings, "UNIPILE_ACCOUNT_ID_LINKEDIN", "acc_123")

    lead = SimpleNamespace(
        id="lead-1",
        linkedin_url="https://www.linkedin.com/in/jane-doe/",
        linkedin_profile_id=None,
        company="Acme",
    )

    async def _fake_get_linkedin_profile(account_id: str, linkedin_url: str):
        assert account_id == "acc_123"
        assert linkedin_url.endswith("/jane-doe/")
        return SimpleNamespace(profile_id="provider_123", company="Acme Ltda")

    async def _fake_fetch_profile_company(account_id: str, provider_id: str):
        raise AssertionError("fetch_profile_company não deveria ser chamado")

    monkeypatch.setattr(
        "workers.enrich.unipile_client",
        SimpleNamespace(
            get_linkedin_profile=_fake_get_linkedin_profile,
            fetch_profile_company=_fake_fetch_profile_company,
        ),
    )

    result = await _resolve_linkedin_crosscheck(cast(Any, lead))

    assert result is not None
    assert result.profile_id == "provider_123"
    assert result.current_company == "Acme Ltda"
    assert result.company_match is True
    assert lead.linkedin_profile_id == "provider_123"


def test_assess_phone_quality_marks_verified_as_green() -> None:
    score, bucket, verified = _assess_phone_quality("VERIFIED")

    assert score == 0.95
    assert bucket == ContactQualityBucket.GREEN
    assert verified is True


def test_assess_phone_quality_marks_unknown_as_orange() -> None:
    score, bucket, verified = _assess_phone_quality("UNKNOWN")

    assert score == 0.55
    assert bucket == ContactQualityBucket.ORANGE
    assert verified is False
