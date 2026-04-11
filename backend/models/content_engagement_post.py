"""
models/content_engagement_post.py

ContentEngagementPost — post garimpado no LinkedIn para analise de engajamento.

post_type='reference': post de alto engajamento do nicho (para aprender)
post_type='icp': post recente de decisor do ICP (para comentar)
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TenantMixin, TimestampMixin


class ContentEngagementPost(Base, TenantMixin, TimestampMixin):
    """
    Post garimpado no LinkedIn.

    post_type: 'reference' (alto engajamento do nicho) | 'icp' (post de decisor)
    engagement_score = comentarios*3 + likes + shares*2
    """

    __tablename__ = "content_engagement_posts"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("content_engagement_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    post_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="reference | icp",
    )

    # Author info
    author_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    author_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    author_company: Mapped[str | None] = mapped_column(String(300), nullable=True)
    author_linkedin_urn: Mapped[str | None] = mapped_column(String(100), nullable=True)
    author_profile_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Post content
    source: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="apify",
        comment="apify | linkedin_api | manual | google",
    )
    merged_sources: Mapped[list[str] | None] = mapped_column(
        JSONB(astext_type=Text()),
        nullable=True,
        comment="Lista de fontes mescladas para este post deduplicado",
    )
    merge_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Quantidade de capturas fundidas neste post",
    )
    post_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    canonical_post_url: Mapped[str | None] = mapped_column(String(500), nullable=True, index=True)
    dedup_key: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    post_text: Mapped[str] = mapped_column(Text, nullable=False)
    post_published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Engagement metrics
    likes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    comments: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    shares: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    engagement_score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="comentarios*3 + likes + shares*2",
    )

    # LLM analysis (preenchido apos scan)
    hook_type: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
        comment="loop_open | contrarian | identification | shortcut | benefit | data",
    )
    pillar: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="authority | case | vision",
    )
    why_it_performed: Mapped[str | None] = mapped_column(Text, nullable=True)
    what_to_replicate: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Control
    is_saved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    session: Mapped[ContentEngagementSession] = relationship(  # noqa: F821
        "ContentEngagementSession",
        back_populates="posts",
    )
    suggested_comments: Mapped[list[ContentEngagementComment]] = relationship(  # noqa: F821
        "ContentEngagementComment",
        back_populates="post",
        lazy="select",
        cascade="all, delete-orphan",
    )
