from __future__ import annotations

from types import SimpleNamespace

import pytest

from integrations.zerobounce import ZeroBounceClient
from models.enums import ContactQualityBucket, EmailType, EmailVerificationStatus
from services.contact_quality import contact_quality_classifier
from services.lead_management import build_lead_email_specs


def test_classifier_marks_valid_corporate_as_green() -> None:
    result = contact_quality_classifier.assess_email(
        finder_confidence=0.72,
        verification_status=EmailVerificationStatus.VALID,
        email_type=EmailType.CORPORATE,
    )

    assert result.verified is True
    assert result.bucket == ContactQualityBucket.GREEN
    assert result.score >= 0.90


def test_classifier_marks_accept_all_as_orange() -> None:
    result = contact_quality_classifier.assess_email(
        finder_confidence=0.81,
        verification_status=EmailVerificationStatus.ACCEPT_ALL,
        email_type=EmailType.CORPORATE,
    )

    assert result.verified is False
    assert result.bucket == ContactQualityBucket.ORANGE
    assert 0.50 <= result.score < 0.90


def test_classifier_penalizes_personal_email() -> None:
    result = contact_quality_classifier.assess_email(
        finder_confidence=0.98,
        verification_status=EmailVerificationStatus.VALID,
        email_type=EmailType.PERSONAL,
    )

    assert result.verified is True
    assert result.bucket == ContactQualityBucket.RED
    assert result.score < 0.50


@pytest.mark.asyncio
async def test_zerobounce_maps_catch_all_to_accept_all(monkeypatch: pytest.MonkeyPatch) -> None:
    client = ZeroBounceClient()

    class _Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "status": "catch-all",
                "sub_status": "accept_all",
                "mx_found": True,
                "smtp_provider": "google",
            }

    async def _fake_get(*args: object, **kwargs: object) -> _Response:
        return _Response()

    monkeypatch.setattr(client, "_client", SimpleNamespace(get=_fake_get))

    result = await client.validate_with_details("lead@example.com")

    assert result.status == EmailVerificationStatus.ACCEPT_ALL
    assert result.is_verified is False
    assert result.is_usable is True
    assert result.mx_found is True


@pytest.mark.asyncio
async def test_zerobounce_validate_returns_false_on_transport_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = ZeroBounceClient()

    async def _fake_get(*args: object, **kwargs: object) -> object:
        raise RuntimeError("network down")

    monkeypatch.setattr(client, "_client", SimpleNamespace(get=_fake_get))

    assert await client.validate("lead@example.com") is False


def test_build_lead_email_specs_keeps_quality_metadata() -> None:
    specs = build_lead_email_specs(
        email_corporate="Lead@Example.com",
        email_corporate_source="prospeo",
        email_corporate_verified=True,
        email_corporate_verification_status=EmailVerificationStatus.VALID,
        email_corporate_quality_score=0.97,
        email_corporate_quality_bucket=ContactQualityBucket.GREEN,
    )

    assert specs == [
        {
            "email": "lead@example.com",
            "email_type": EmailType.CORPORATE,
            "source": "prospeo",
            "verified": True,
            "verification_status": EmailVerificationStatus.VALID,
            "quality_score": 0.97,
            "quality_bucket": ContactQualityBucket.GREEN,
            "is_primary": True,
        }
    ]


def test_classifier_applies_linkedin_match_signal() -> None:
    assessment = contact_quality_classifier.assess_email(
        finder_confidence=0.74,
        verification_status=EmailVerificationStatus.ACCEPT_ALL,
        email_type=EmailType.CORPORATE,
    )

    upgraded = contact_quality_classifier.apply_linkedin_signal(
        assessment,
        company_match=True,
    )
    downgraded = contact_quality_classifier.apply_linkedin_signal(
        assessment,
        company_match=False,
    )

    assert upgraded.score > assessment.score
    assert downgraded.score < assessment.score
    assert downgraded.bucket == ContactQualityBucket.RED
