"""
models/content_engagement_discovery_query.py

Histórico do query composer de discovery externo para engajamento.
Primeira fonte suportada: operadores de busca do Google.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TenantMixin, TimestampMixin


class ContentEngagementDiscoveryQuery(Base, TenantMixin, TimestampMixin):
    __tablename__ = "content_engagement_discovery_queries"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    provider: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="google_operators",
        index=True,
    )
    query_text: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    criteria: Mapped[dict[str, object] | None] = mapped_column(
        JSONB(astext_type=Text()),
        nullable=True,
    )
    imported_session_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("content_engagement_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
