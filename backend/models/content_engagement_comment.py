"""
models/content_engagement_comment.py

ContentEngagementComment — sugestao de comentario gerada por LLM para um post de ICP.

REGRA ABSOLUTA: nenhum comentario e postado automaticamente.
Tudo passa pela revisao e acao manual do usuario.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TenantMixin, TimestampMixin


class ContentEngagementComment(Base, TenantMixin, TimestampMixin):
    """
    Sugestao de comentario LLM para post de ICP.

    variation: 1 ou 2 (duas opcoes por post)
    status: pending | selected | posted | discarded
    """

    __tablename__ = "content_engagement_comments"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    engagement_post_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("content_engagement_posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("content_engagement_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    comment_text: Mapped[str] = mapped_column(Text, nullable=False)
    variation: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="1 ou 2 (duas opcoes por post)",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        comment="pending | selected | posted | discarded",
    )
    posted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    post: Mapped[ContentEngagementPost] = relationship(  # noqa: F821
        "ContentEngagementPost",
        back_populates="suggested_comments",
    )
    session: Mapped[ContentEngagementSession] = relationship(  # noqa: F821
        "ContentEngagementSession",
        back_populates="comments",
    )
