from __future__ import annotations

from models.enums import ContactQualityBucket, LeadSource
from schemas.lead import LeadGeneratedPreviewItem
from services.lead_generation import _apply_preview_quality


def _make_preview_item(**overrides: object) -> LeadGeneratedPreviewItem:
    payload: dict[str, object] = {
        "preview_id": "b2b_database:1",
        "name": "Joao Silva",
        "source": LeadSource.API,
        "origin_key": "b2b_database",
        "origin_label": "Base B2B",
    }
    payload.update(overrides)
    return LeadGeneratedPreviewItem(**payload)


def test_apply_preview_quality_marks_verified_corporate_email_as_green() -> None:
    item = _make_preview_item(email_corporate="joao@acme.com", li_verified=True)

    enriched = _apply_preview_quality(item)

    assert enriched.quality_bucket == ContactQualityBucket.GREEN
    assert enriched.quality_score == 0.85


def test_apply_preview_quality_marks_linkedin_mismatch_as_red() -> None:
    item = _make_preview_item(email_corporate="joao@acme.com", li_outdated=True)

    enriched = _apply_preview_quality(item)

    assert enriched.quality_bucket == ContactQualityBucket.RED
    assert enriched.quality_score == 0.20
