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

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TenantMixin, TimestampMixin
from models.enums import LeadSource, LeadStatus


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
    company: Mapped[str | None] = mapped_column(String(300))
    website: Mapped[str | None] = mapped_column(String(500))

    # ── LinkedIn ──────────────────────────────────────────────────────
    linkedin_url: Mapped[str | None] = mapped_column(String(500), unique=True, index=True)
    linkedin_profile_id: Mapped[str | None] = mapped_column(String(200), index=True)

    # ── Localização / Segmentação ─────────────────────────────────────
    city: Mapped[str | None] = mapped_column(String(200))
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
