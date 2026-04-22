from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/testdb")
os.environ.setdefault("SECRET_KEY", "test-secret")

from models.enums import LeadStatus
from workers.enrich import _status_after_enrichment


def test_status_after_enrichment_preserves_in_cadence() -> None:
    assert _status_after_enrichment(LeadStatus.IN_CADENCE) == LeadStatus.IN_CADENCE


def test_status_after_enrichment_promotes_raw_to_enriched() -> None:
    assert _status_after_enrichment(LeadStatus.RAW) == LeadStatus.ENRICHED


def test_status_after_enrichment_preserves_terminal_statuses() -> None:
    assert _status_after_enrichment(LeadStatus.CONVERTED) == LeadStatus.CONVERTED
    assert _status_after_enrichment(LeadStatus.ARCHIVED) == LeadStatus.ARCHIVED
