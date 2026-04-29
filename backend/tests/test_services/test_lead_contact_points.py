from __future__ import annotations

from models.enums import ContactPointKind, ContactQualityBucket, EmailType, EmailVerificationStatus
from services.lead_management import build_lead_contact_point_specs


def test_build_lead_contact_point_specs_maps_email_and_phone() -> None:
    specs = build_lead_contact_point_specs(
        email_specs=[
            {
                "email": "Lead@Example.com",
                "email_type": EmailType.CORPORATE,
                "source": "prospeo",
                "verified": True,
                "verification_status": EmailVerificationStatus.VALID,
                "quality_score": 0.96,
                "quality_bucket": ContactQualityBucket.GREEN,
                "is_primary": True,
            }
        ],
        email_evidence_by_value={
            "lead@example.com": {
                "provider": "prospeo",
                "finder_confidence": 1.0,
            }
        },
        phone="+55 (11) 99999-1111",
        phone_source="prospeo",
        phone_verified=True,
        phone_verification_status="VERIFIED",
        phone_quality_score=0.95,
        phone_quality_bucket=ContactQualityBucket.GREEN,
        phone_evidence_json={"provider": "prospeo", "mobile_status": "VERIFIED"},
    )

    assert specs[0]["kind"] == ContactPointKind.EMAIL
    assert specs[0]["normalized_value"] == "lead@example.com"
    assert specs[0]["evidence_json"] == {"provider": "prospeo", "finder_confidence": 1.0}
    assert specs[1]["kind"] == ContactPointKind.PHONE
    assert specs[1]["normalized_value"] == "5511999991111"
    assert specs[1]["verified"] is True
