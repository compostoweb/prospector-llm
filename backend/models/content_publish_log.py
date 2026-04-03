"""
models/content_publish_log.py

ContentPublishLog — log imutavel de todas as acoes de publicacao no LinkedIn.

Registra cada tentativa de schedule, publish, cancel ou fail
junto com a resposta bruta da LinkedIn API.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TenantMixin, _utcnow


class ContentPublishLog(Base, TenantMixin):
    """
    Log imutavel de publicacoes.

    action: schedule | publish | cancel | fail
    Sem updated_at — registro nao e alterado apos criacao.
    """

    __tablename__ = "content_publish_log"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    post_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("content_posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="schedule | publish | cancel | fail",
    )
    linkedin_response: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Resposta bruta da LinkedIn API",
    )
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )
