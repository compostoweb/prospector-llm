"""
models/content_lead_magnet.py

Lead magnets do subsistema inbound do Content Hub.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TenantMixin, TimestampMixin


class ContentLeadMagnet(Base, TenantMixin, TimestampMixin):
    __tablename__ = "content_lead_magnets"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="pdf | calculator | email_sequence",
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="draft",
        server_default="draft",
        comment="draft | active | paused | archived",
    )
    file_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    cta_text: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sendpulse_list_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="ID da mailing list no SendPulse vinculada ao lead magnet",
    )
    linked_calculator_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("content_lead_magnets.id", ondelete="SET NULL"),
        nullable=True,
    )
    total_leads_captured: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    total_downloads: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    conversion_rate: Mapped[float | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )