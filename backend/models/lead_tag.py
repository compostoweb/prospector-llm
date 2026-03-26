"""
models/lead_tag.py

Model LeadTag — tags associadas a leads para categorização na sidebar do inbox.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TenantMixin


class LeadTag(Base, TenantMixin):
    """
    Tag associada a um lead.
    Permite categorização rápida direto da sidebar do inbox.
    """

    __tablename__ = "lead_tags"
    __table_args__ = (
        UniqueConstraint("lead_id", "name", name="uq_lead_tags_lead_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    lead_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(50), nullable=False)
    color: Mapped[str] = mapped_column(String(7), nullable=False, default="#6366f1")
