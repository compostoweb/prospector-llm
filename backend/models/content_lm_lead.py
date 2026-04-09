"""
models/content_lm_lead.py

Leads capturados via lead magnets e LPs públicas.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TenantMixin, TimestampMixin


class ContentLMLead(Base, TenantMixin, TimestampMixin):
    __tablename__ = "content_lm_leads"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "lead_magnet_id",
            "email",
            name="uq_content_lm_leads_tenant_lm_email",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    lead_magnet_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("content_lead_magnets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lm_post_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("content_lm_posts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    linkedin_profile_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    company: Mapped[str | None] = mapped_column(String(150), nullable=True)
    role: Mapped[str | None] = mapped_column(String(150), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    origin: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="landing_page",
        server_default="landing_page",
        comment="linkedin_comment | linkedin_dm | landing_page | cold_outreach | direct | calculator",
    )
    capture_metadata: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    sendpulse_list_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sendpulse_subscriber_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sendpulse_sync_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
        comment="pending | processing | synced | failed | skipped",
    )
    sendpulse_last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    sendpulse_last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    sequence_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
        comment="pending | active | completed | unsubscribed",
    )
    sequence_completed: Mapped[bool] = mapped_column(default=False, nullable=False, server_default="false")
    converted_via_email: Mapped[bool] = mapped_column(default=False, nullable=False, server_default="false")
    converted_to_lead: Mapped[bool] = mapped_column(default=False, nullable=False, server_default="false")
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    downloaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)