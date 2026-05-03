"""
models/content_landing_page.py

Configuração das landing pages públicas de captura.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TenantMixin, TimestampMixin


class ContentLandingPage(Base, TenantMixin, TimestampMixin):
    __tablename__ = "content_landing_pages"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    lead_magnet_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("content_lead_magnets.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    subtitle: Mapped[str | None] = mapped_column(Text, nullable=True)
    hero_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    benefits: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    social_proof_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    author_bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    author_photo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    meta_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    publisher_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    features: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)
    expected_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    badge_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    form_fields: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)
    published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    total_views: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    total_submissions: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    conversion_rate: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)