from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TenantMixin, TimestampMixin
from models.enums import ContactPointKind, ContactQualityBucket

if TYPE_CHECKING:
    from models.lead import Lead


class LeadContactPoint(Base, TenantMixin, TimestampMixin):
    """Ponto de contato canônico de um lead com qualidade e evidências."""

    __tablename__ = "lead_contact_points"
    __table_args__ = (
        UniqueConstraint(
            "lead_id",
            "kind",
            "normalized_value",
            name="uq_lead_contact_points_lead_kind_value",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[ContactPointKind] = mapped_column(
        SAEnum(ContactPointKind, name="contact_point_kind"),
        nullable=False,
    )
    value: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_value: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verification_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_bucket: Mapped[ContactQualityBucket | None] = mapped_column(
        SAEnum(
            ContactQualityBucket,
            name="contact_quality_bucket",
            native_enum=False,
        ),
        nullable=True,
    )
    evidence_json: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    metadata_json: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    lead: Mapped[Lead] = relationship("Lead", back_populates="contact_points")
