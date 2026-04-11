"""
models/content_engagement_event.py

Eventos operacionais do módulo de engajamento.
Servem para auditoria, debug e trilha de execução da sessão.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TenantMixin, TimestampMixin


class ContentEngagementEvent(Base, TenantMixin, TimestampMixin):
    __tablename__ = "content_engagement_events"

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
    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    payload: Mapped[dict[str, object] | None] = mapped_column(
        JSONB(astext_type=Text()),
        nullable=True,
    )
