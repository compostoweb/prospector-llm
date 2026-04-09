"""
models/content_calculator_result.py

Resultados persistidos da calculadora pública de ROI.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TenantMixin, TimestampMixin


class ContentCalculatorResult(Base, TenantMixin, TimestampMixin):
    __tablename__ = "content_calculator_results"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    lead_magnet_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("content_lead_magnets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    pessoas: Mapped[int] = mapped_column(Integer, nullable=False)
    horas_semana: Mapped[float] = mapped_column(Numeric(5, 1), nullable=False)
    custo_hora: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    cargo: Mapped[str] = mapped_column(String(50), nullable=False)
    retrabalho_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    tipo_processo: Mapped[str] = mapped_column(String(30), nullable=False)
    company_segment: Mapped[str | None] = mapped_column(String(30), nullable=True)
    company_size: Mapped[str | None] = mapped_column(String(20), nullable=True)
    process_area_span: Mapped[str | None] = mapped_column(String(10), nullable=True)
    custo_mensal: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    custo_retrabalho: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    custo_total_mensal: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    custo_anual: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    investimento_estimado_min: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    investimento_estimado_max: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    roi_estimado: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    payback_meses: Mapped[float] = mapped_column(Numeric(5, 1), nullable=False)
    name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    company: Mapped[str | None] = mapped_column(String(150), nullable=True)
    role: Mapped[str | None] = mapped_column(String(150), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    converted_to_lead: Mapped[bool] = mapped_column(
        default=False, nullable=False, server_default="false"
    )
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    session_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
