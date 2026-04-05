"""
models/content_post.py

ContentPost — post do calendário editorial do módulo Content Hub.

Representa um post criado/agendado/publicado no LinkedIn pelo tenant.
Status flow: draft → approved → scheduled → published (ou failed).

Campos de métricas (impressions, likes, etc.) são inseridos manualmente
para perfis pessoais. Para Company Pages, podem ser puxados via API.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Integer, Numeric, String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TenantMixin, TimestampMixin


class ContentPost(Base, TenantMixin, TimestampMixin):
    """
    Post do calendário editorial.

    pillar: authority (autoridade) | case (caso) | vision (visão)
    status: draft | approved | scheduled | published | failed
    hook_type: loop_open | contrarian | identification | shortcut | benefit | data
    """

    __tablename__ = "content_posts"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ── Conteúdo ──────────────────────────────────────────────────────
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Título interno, ex: 'Semana 5 · Segunda | Tema'",
    )
    body: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Texto completo do post",
    )
    pillar: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="authority | case | vision",
    )
    hook_type: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
        comment="loop_open | contrarian | identification | shortcut | benefit | data",
    )
    hashtags: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Hashtags como texto livre, ex: '#ia #processos #automacao'",
    )
    character_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # ── Agendamento ───────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="draft",
        server_default="draft",
        comment="draft | approved | scheduled | published | failed",
    )
    publish_date: Mapped[str | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Data/hora agendada para publicação",
    )
    week_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Número da semana do calendário editorial",
    )

    # ── LinkedIn URNs ─────────────────────────────────────────────────
    linkedin_post_urn: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="urn:li:ugcPost:{id} após publicação bem-sucedida",
    )
    linkedin_scheduled_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="ID do post agendado no LinkedIn (lifecycleState=DRAFT)",
    )

    # ── Métricas ──────────────────────────────────────────────────────
    impressions: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    likes: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    comments: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    shares: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    saves: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    engagement_rate: Mapped[float | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Taxa de engajamento em % (calculada ou inserida manualmente)",
    )
    metrics_updated_at: Mapped[str | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ── Controle ──────────────────────────────────────────────────────
    published_at: Mapped[str | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Mensagem de erro se status=failed",
    )
