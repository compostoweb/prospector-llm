"""
models/content_article.py

ContentArticle — post de tipo "link share" no LinkedIn (card rico apontando
para URL externa). Usado para divulgar Newsletter publicada no Pulse, blog
posts, ou qualquer URL externa.

Publicado via Posts API oficial: POST /rest/posts com content.article.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TenantMixin, TimestampMixin


class ContentArticle(Base, TenantMixin, TimestampMixin):
    """
    Post de link share via Posts API.

    status: draft | approved | scheduled | published | failed | deleted
    """

    __tablename__ = "content_articles"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ── Conteudo do card ──────────────────────────────────────────────
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumbnail_s3_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    linkedin_image_urn: Mapped[str | None] = mapped_column(Text, nullable=True)
    commentary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Status ────────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="draft",
        server_default="draft",
    )
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    linkedin_post_urn: Mapped[str | None] = mapped_column(String(200), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── First comment ─────────────────────────────────────────────────
    first_comment_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    first_comment_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
    )
    first_comment_pin_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
    )
    first_comment_urn: Mapped[str | None] = mapped_column(Text, nullable=True)
    first_comment_posted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    first_comment_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Idempotency lock ──────────────────────────────────────────────
    processing_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_lock_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )

    # ── Metricas ──────────────────────────────────────────────────────
    impressions: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    likes: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    comments: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    shares: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    engagement_rate: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    metrics_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Origem ────────────────────────────────────────────────────────
    source_newsletter_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("content_newsletters.id", ondelete="SET NULL"),
        nullable=True,
    )
    auto_scraped: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    scraped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
