"""
models/content_settings.py

ContentSettings — configurações do módulo Content Hub por tenant.

Um único registro por tenant (UNIQUE tenant_id).
Contém voz do autor para prompts LLM, frequência de posts e outros defaults.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Index, Integer, String, Text, Time
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TenantMixin, TimestampMixin


class ContentSettings(Base, TenantMixin, TimestampMixin):
    """
    Configuracoes do Content Hub para um tenant.
    Exatamente um registro por tenant.
    """

    __tablename__ = "content_settings"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    default_publish_time: Mapped[str | None] = mapped_column(
        Time,
        nullable=True,
        comment="Horario padrao de publicacao, ex: 09:00",
    )
    posts_per_week: Mapped[int] = mapped_column(
        Integer,
        default=3,
        server_default="3",
        comment="Meta de posts por semana",
    )
    author_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Nome do autor para o prompt LLM",
    )
    author_voice: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Descricao da voz/persona do autor para o prompt LLM",
    )

    # ── Integração Notion ─────────────────────────────────────────────
    notion_api_key: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Internal Integration token do Notion (secret_xxx)",
    )
    notion_database_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="ID do banco de dados Notion com os posts (UUID da URL)",
    )
    notion_column_mappings: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="JSON: mapeamento colunas Notion -> campos ContentPost (campo_interno: nome_coluna_notion)",
    )
