"""
models/content_lm_post.py

Posts do calendário editorial vinculados a lead magnets.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TenantMixin, TimestampMixin


class ContentLMPost(Base, TenantMixin, TimestampMixin):
    __tablename__ = "content_lm_posts"

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
    content_post_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("content_posts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    post_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="launch",
        server_default="launch",
        comment="launch | relaunch | reminder",
    )
    distribution_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="comment",
        server_default="comment",
        comment="comment | dm | link_bio",
    )
    trigger_word: Mapped[str | None] = mapped_column(String(50), nullable=True)
    linkedin_post_urn: Mapped[str | None] = mapped_column(String(100), nullable=True)
    comments_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    dms_sent: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    clicks_lp: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    leads_from_post: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)