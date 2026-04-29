from __future__ import annotations

from dataclasses import dataclass

from models.enums import ContactQualityBucket, EmailType, EmailVerificationStatus


@dataclass(frozen=True)
class ContactQualityAssessment:
    """Resultado normalizado da avaliação de qualidade de um contato."""

    score: float
    bucket: ContactQualityBucket
    verification_status: EmailVerificationStatus
    verified: bool


class ContactQualityClassifier:
    """Classifica a qualidade do contato a partir da confiança e verificação."""

    def assess_email(
        self,
        *,
        finder_confidence: float,
        verification_status: EmailVerificationStatus,
        email_type: EmailType,
    ) -> ContactQualityAssessment:
        score = _clamp(finder_confidence)

        if verification_status == EmailVerificationStatus.VALID:
            score = max(score, 0.95)
        elif verification_status == EmailVerificationStatus.ACCEPT_ALL:
            score = min(max(score, 0.55), 0.75)
        elif verification_status in {
            EmailVerificationStatus.UNKNOWN,
            EmailVerificationStatus.WEBMAIL,
        }:
            score = min(max(score, 0.50), 0.65)
        else:
            score = 0.0

        if email_type == EmailType.PERSONAL and score > 0.0:
            score = min(score, 0.45)

        bucket = _bucket_for_score(score)
        return ContactQualityAssessment(
            score=score,
            bucket=bucket,
            verification_status=verification_status,
            verified=verification_status == EmailVerificationStatus.VALID,
        )

    def apply_linkedin_signal(
        self,
        assessment: ContactQualityAssessment,
        *,
        company_match: bool | None,
    ) -> ContactQualityAssessment:
        if company_match is None:
            return assessment

        if company_match:
            score = min(1.0, assessment.score + 0.10)
        else:
            score = max(0.0, assessment.score - 0.30)

        return ContactQualityAssessment(
            score=score,
            bucket=_bucket_for_score(score),
            verification_status=assessment.verification_status,
            verified=assessment.verified,
        )


contact_quality_classifier = ContactQualityClassifier()


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _bucket_for_score(score: float) -> ContactQualityBucket:
    if score >= 0.90:
        return ContactQualityBucket.GREEN
    if score >= 0.50:
        return ContactQualityBucket.ORANGE
    return ContactQualityBucket.RED
