"""
models/capture_schedule.py

Configuração de captura automática agendada por tenant.

Cada tenant pode ter uma configuração para cada fonte:
  - google_maps: termos de busca, localização, categorias, limite
  - b2b_database: cargos, localizações, cidades, setores, palavras-chave, tamanhos de empresa, limite

O Celery Beat lê essas configs diariamente e dispara a captura para cada
tenant que tiver uma config ativa.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CaptureScheduleConfig(Base):
    """
    Configuração de captura automática agendada por tenant + fonte.
    Um tenant pode ter no máximo uma config por fonte (unique constraint).

    Fontes suportadas:
      - "google_maps": Apify Google Maps Actor
      - "b2b_database": Apify B2B Leads Actor
    """

    __tablename__ = "capture_schedule_configs"
    __table_args__ = (
        UniqueConstraint("tenant_id", "source", name="uq_capture_schedule_tenant_source"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="'google_maps' | 'b2b_database'",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    max_items: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=25,
    )

    # ── Campos Google Maps ─────────────────────────────────────────────
    maps_search_terms: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text),
        nullable=True,
        comment="Termos de busca para Google Maps (ex: ['academias SP'])",
    )
    maps_location: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
        comment="Cidade/região para Google Maps (ex: 'São Paulo, Brasil')",
    )
    maps_categories: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text),
        nullable=True,
        comment="Categorias para filtrar Google Maps (ex: ['academia', 'fitness'])",
    )

    # ── Campos B2B Database ────────────────────────────────────────────
    b2b_job_titles: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text),
        nullable=True,
        comment="Cargos de interesse para B2B (ex: ['CEO', 'Diretor'])",
    )
    b2b_locations: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text),
        nullable=True,
        comment="Países/regiões para B2B (ex: ['Brasil'])",
    )
    b2b_cities: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text),
        nullable=True,
        comment="Cidades para B2B (ex: ['São Paulo', 'Curitiba'])",
    )
    b2b_industries: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text),
        nullable=True,
        comment="Setores para B2B (ex: ['software', 'marketing'])",
    )
    b2b_company_keywords: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text),
        nullable=True,
        comment="Palavras-chave no nome da empresa (ex: ['SaaS', 'B2B'])",
    )
    b2b_company_sizes: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text),
        nullable=True,
        comment="Tamanhos de empresa (ex: ['11-20', '21-50'])",
    )

    # ── Campos de rotação ──────────────────────────────────────────────
    maps_locations: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text),
        nullable=True,
        comment="Lista de cidades/regiões para rotação automática Maps (uma por execução)",
    )
    maps_combo_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Índice atual no produto cartesiano terms × locations",
    )
    b2b_rotation_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Índice atual na lista b2b_cities para rotação",
    )
    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_list_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("lead_lists.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )
