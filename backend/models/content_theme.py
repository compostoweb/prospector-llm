"""
models/content_theme.py

ContentTheme — banco de temas para geração de posts LinkedIn.

Cada tema pertence a um pilar editorial e pode ser marcado como usado
quando um post for gerado a partir dele.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, DateTime
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TenantMixin, TimestampMixin


class ContentTheme(Base, TenantMixin, TimestampMixin):
    """
    Tema do banco de conteúdo.

    pillar: authority | case | vision
    is_custom: True quando criado manualmente pelo usuário (vs seed inicial)
    """

    __tablename__ = "content_themes"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Descrição curta do tema",
    )
    pillar: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="authority | case | vision",
    )

    # ── Controle de uso ───────────────────────────────────────────────
    used: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    used_in_post_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("content_posts.id", ondelete="SET NULL"),
        nullable=True,
        comment="FK para o post gerado a partir deste tema",
    )

    is_custom: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        comment="True = criado pelo usuário; False = seed do sistema",
    )
