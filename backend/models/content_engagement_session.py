"""
models/content_engagement_session.py

ContentEngagementSession — sessao de garimpagem de posts para engajamento estrategico.

Uma sessao agrupa uma rodada completa de scan:
  - posts de referencia (alto engajamento do nicho)
  - posts de ICP (decisores recentes)
  - comentarios gerados por LLM
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TenantMixin, TimestampMixin


class ContentEngagementSession(Base, TenantMixin, TimestampMixin):
    """
    Sessao de scan de engajamento.

    status: running | completed | partial | failed
    scan_source: linkedin_api | apify | manual
    """

    __tablename__ = "content_engagement_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    linked_post_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        comment="post que sera publicado em seguida (opcional)",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="running",
        comment="running | completed | partial | failed",
    )
    references_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    icp_posts_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    comments_generated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    comments_posted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    scan_source: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="apify",
        comment="linkedin_api | apify | manual",
    )
    current_step: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="etapa atual do scan: 1-4",
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    posts: Mapped[list[ContentEngagementPost]] = relationship(  # noqa: F821
        "ContentEngagementPost",
        back_populates="session",
        lazy="select",
        cascade="all, delete-orphan",
    )
    comments: Mapped[list[ContentEngagementComment]] = relationship(  # noqa: F821
        "ContentEngagementComment",
        back_populates="session",
        lazy="select",
        cascade="all, delete-orphan",
    )
