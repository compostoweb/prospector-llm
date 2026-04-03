"""
models/content_reference.py

ContentReference — posts de alta performance do nicho usados como
exemplos few-shot nos prompts de geracao de conteudo com LLM.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TenantMixin, TimestampMixin


class ContentReference(Base, TenantMixin, TimestampMixin):
    """
    Post de referencia de alta performance do nicho.

    Usado como exemplo few-shot no LLM ao gerar novos posts.
    engagement_score = comentarios*3 + likes + compartilhamentos*2
    """

    __tablename__ = "content_references"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    author_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    author_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
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
    engagement_score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="comentarios*3 + likes + compartilhamentos*2",
    )
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
