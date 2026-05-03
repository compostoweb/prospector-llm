"""
models/content_newsletter.py

ContentNewsletter — edicoes da newsletter editorial publicada no LinkedIn Pulse.
Como o LinkedIn nao expoe API publica para Newsletter, esta entidade armazena
o conteudo local + URL final do Pulse (preenchida manualmente apos publicacao).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TenantMixin, TimestampMixin


class ContentNewsletter(Base, TenantMixin, TimestampMixin):
    """
    Edicao da newsletter "Operacao Inteligente" (skill 07-newsletter-linkedin).

    status: draft | approved | scheduled | published | deleted
    """

    __tablename__ = "content_newsletters"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    edition_number: Mapped[int] = mapped_column(Integer, nullable=False)

    title: Mapped[str] = mapped_column(Text, nullable=False)
    subtitle: Mapped[str | None] = mapped_column(Text, nullable=True)

    body_markdown: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    body_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    sections_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    cover_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_image_s3_key: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="draft",
        server_default="draft",
    )
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    linkedin_pulse_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    derived_article_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )
    last_reminder_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_by: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    notion_page_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    # Métricas manuais do LinkedIn Pulse (preenchidas pelo usuário)
    pulse_views_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pulse_reactions_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pulse_comments_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pulse_reposts_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
