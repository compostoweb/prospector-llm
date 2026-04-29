"""
models/content_gallery_image.py

Asset independente da galeria do Content Hub.

Usado para imagens geradas diretamente na galeria, sem criar ContentPost.
Pode futuramente ser vinculado a um post real via linked_post_id.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TenantMixin, TimestampMixin


class ContentGalleryImage(Base, TenantMixin, TimestampMixin):
    """Imagem independente armazenada na galeria."""

    __tablename__ = "content_gallery_images"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="generated",
        server_default="generated",
        comment="generated | uploaded",
    )
    linked_post_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("content_posts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    image_url: Mapped[str] = mapped_column(Text, nullable=False)
    image_s3_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_style: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="clean | with_text | infographic"
    )
    image_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_aspect_ratio: Mapped[str | None] = mapped_column(
        String(10), nullable=True, comment="4:5 | 1:1 | 16:9"
    )
    image_filename: Mapped[str | None] = mapped_column(String(500), nullable=True)
    image_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── Carrossel ─────────────────────────────────────────────────────
    position: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Ordem 0-based dentro do carrossel; NULL = imagem standalone/single.",
    )
    linkedin_image_urn: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="urn:li:digitalmediaAsset após upload (cache pré-publish).",
    )
    carousel_group_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="Agrupador visual (pasta na galeria) das imagens do mesmo carrossel.",
    )
