from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TenantMixin, TimestampMixin
from models.enums import EmailType

if TYPE_CHECKING:
    from models.lead import Lead


class LeadEmail(Base, TenantMixin, TimestampMixin):
    """Endereco de email normalizado de um lead."""

    __tablename__ = "lead_emails"
    __table_args__ = (UniqueConstraint("lead_id", "email", name="uq_lead_emails_lead_id_email"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(254), nullable=False, index=True)
    email_type: Mapped[EmailType] = mapped_column(
        SAEnum(EmailType, name="email_type"),
        nullable=False,
        default=EmailType.UNKNOWN,
    )
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    lead: Mapped[Lead] = relationship("Lead", back_populates="emails")
