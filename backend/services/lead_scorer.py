from __future__ import annotations

from models.enums import ContactPointKind, ContactQualityBucket, EmailType
from models.lead import Lead


class LeadScorer:
    def score(self, lead: Lead) -> int:
        points = 0
        contact_points = list(lead.__dict__.get("contact_points") or [])
        emails = list(lead.__dict__.get("emails") or [])

        best_email_bucket = self._best_email_bucket(lead, contact_points, emails)
        best_phone_bucket = self._best_phone_bucket(lead, contact_points)

        if lead.linkedin_url:
            points += 15

        if lead.linkedin_mismatch is True:
            points -= 20
        elif lead.linkedin_checked_at is not None:
            points += 5

        if best_email_bucket == ContactQualityBucket.GREEN:
            points += 35
        elif best_email_bucket == ContactQualityBucket.ORANGE:
            points += 18
        elif best_email_bucket == ContactQualityBucket.RED:
            points -= 8
        elif lead.email_corporate:
            points += 22
        elif lead.email_personal:
            points += 8

        if lead.email_corporate_verified:
            points += 8

        if lead.company:
            points += 10

        if lead.website:
            points += 10

        if best_phone_bucket == ContactQualityBucket.GREEN:
            points += 10
        elif best_phone_bucket == ContactQualityBucket.ORANGE:
            points += 6
        elif lead.phone:
            points += 4

        if lead.segment:
            points += 10

        if lead.city:
            points += 5

        return max(0, min(100, points))

    def _best_email_bucket(self, lead: Lead, contact_points: list[object], emails: list[object]):
        buckets: list[ContactQualityBucket] = []

        for point in contact_points:
            if getattr(point, "kind", None) == ContactPointKind.EMAIL:
                bucket = getattr(point, "quality_bucket", None)
                if isinstance(bucket, ContactQualityBucket):
                    buckets.append(bucket)

        for email in emails:
            bucket = getattr(email, "quality_bucket", None)
            if isinstance(bucket, ContactQualityBucket):
                buckets.append(bucket)

        if buckets:
            return self._best_bucket(buckets)

        if lead.email_corporate_verified:
            return ContactQualityBucket.GREEN
        if lead.email_corporate:
            return ContactQualityBucket.ORANGE
        if lead.email_personal:
            primary_email_types = [
                getattr(email, "email_type", None)
                for email in emails
                if getattr(email, "is_primary", False)
            ]
            if EmailType.PERSONAL in primary_email_types or not primary_email_types:
                return ContactQualityBucket.RED

        return None

    def _best_phone_bucket(self, lead: Lead, contact_points: list[object]):
        buckets: list[ContactQualityBucket] = []
        for point in contact_points:
            if getattr(point, "kind", None) != ContactPointKind.PHONE:
                continue
            bucket = getattr(point, "quality_bucket", None)
            if isinstance(bucket, ContactQualityBucket):
                buckets.append(bucket)
        if buckets:
            return self._best_bucket(buckets)
        return ContactQualityBucket.ORANGE if lead.phone else None

    @staticmethod
    def _best_bucket(buckets: list[ContactQualityBucket]) -> ContactQualityBucket:
        if ContactQualityBucket.GREEN in buckets:
            return ContactQualityBucket.GREEN
        if ContactQualityBucket.ORANGE in buckets:
            return ContactQualityBucket.ORANGE
        return ContactQualityBucket.RED


lead_scorer = LeadScorer()
