"""
models/lead.py

Model Lead — principal entidade de prospecção.

Responsabilidades:
  - Armazenar todos os dados de um prospect (nome, empresa, contatos, enriquecimento)
  - Rastrear status na jornada (raw → enriched → in_cadence → converted/archived)
  - Suportar múltiplos emails (corporativo + pessoal) com metadados de origem
  - Integrar com tenant via TenantMixin (RLS automático)
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TenantMixin, TimestampMixin
from models.enums import LeadSource, LeadStatus

if TYPE_CHECKING:
    from models.lead_list import LeadList


class Lead(Base, TenantMixin, TimestampMixin):
    """
    Representa um prospect que pode ser trabalhado em cadências de prospecção.
    """

    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    # ── Identificação ─────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(150))
    last_name: Mapped[str | None] = mapped_column(String(150))
    job_title: Mapped[str | None] = mapped_column(String(200))
    company: Mapped[str | None] = mapped_column(String(300))
    company_domain: Mapped[str | None] = mapped_column(String(500))
    website: Mapped[str | None] = mapped_column(String(500))
    industry: Mapped[str | None] = mapped_column(String(200))
    company_size: Mapped[str | None] = mapped_column(String(50))

    # ── LinkedIn ──────────────────────────────────────────────────────
    linkedin_url: Mapped[str | None] = mapped_column(String(500), unique=True, index=True)
    linkedin_profile_id: Mapped[str | None] = mapped_column(String(200), index=True)
    linkedin_connection_status: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        default=None,
        comment="Status da conexão LinkedIn: pending | connected | None",
    )
    linkedin_connected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    # ── Localização / Segmentação ─────────────────────────────────────
    city: Mapped[str | None] = mapped_column(String(200))
    location: Mapped[str | None] = mapped_column(String(300))
    segment: Mapped[str | None] = mapped_column(String(200))

    # ── Status e origem ───────────────────────────────────────────────
    source: Mapped[LeadSource] = mapped_column(
        SAEnum(LeadSource, name="lead_source"),
        default=LeadSource.MANUAL,
        nullable=False,
    )
    status: Mapped[LeadStatus] = mapped_column(
        SAEnum(LeadStatus, name="lead_status"),
        default=LeadStatus.RAW,
        nullable=False,
        index=True,
    )
    score: Mapped[float | None] = mapped_column(Float)

    # ── Email corporativo ─────────────────────────────────────────────
    email_corporate: Mapped[str | None] = mapped_column(String(254), index=True)
    email_corporate_source: Mapped[str | None] = mapped_column(String(100))
    email_corporate_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── Email pessoal ─────────────────────────────────────────────────
    email_personal: Mapped[str | None] = mapped_column(String(254))
    email_personal_source: Mapped[str | None] = mapped_column(String(100))

    # ── Contato ───────────────────────────────────────────────────────
    phone: Mapped[str | None] = mapped_column(String(50))

    # ── Enriquecimento ────────────────────────────────────────────────
    enriched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # ── Notas internas ────────────────────────────────────────────────
    notes: Mapped[str | None] = mapped_column(Text)

    # ── Cache de posts LinkedIn (populado no enrich) ──────────────────
    linkedin_recent_posts_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
        comment="JSON com últimos posts do lead no LinkedIn (cache de enriquecimento)",
    )

    # ── Cold email ────────────────────────────────────────────────────
    timezone: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        default=None,
        comment="Fuso horário do lead ex: 'America/Sao_Paulo'. Usado para scheduling por timezone.",
    )
    email_bounced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        comment="Se preenchido, e-mails para este lead são pulados (bounce detectado).",
    )
    email_bounce_type: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
        default=None,
        comment="Tipo do bounce: 'hard' (permanente) ou 'soft' (temporário).",
    )

    # ── Análise LLM (Anthropic Batch API) ────────────────────────────
    llm_icp_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        default=None,
        comment="Score de fit ICP (0–100) avaliado pelo LLM via Batch API",
    )
    llm_icp_reasoning: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
        comment="Justificativa do score de ICP gerada pelo LLM",
    )
    llm_personalization_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
        comment="Ângulos de personalização sugeridos pelo LLM para abordagem",
    )
    llm_analyzed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        comment="Timestamp da última análise LLM via Batch API",
    )

    lists: Mapped[list[LeadList]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "LeadList",
        secondary="lead_list_members",
        back_populates="leads",
        lazy="selectin",
    )
