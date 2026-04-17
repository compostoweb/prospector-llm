"""
models/capture_execution_log.py

Histórico de execuções de captura automática.
Cada vez que o worker roda uma captura agendada, um registro é criado
armazenando a lista gerada, métricas e status.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class CaptureExecutionLog(Base):
    __tablename__ = "capture_execution_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    capture_config_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("capture_schedule_configs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    list_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("lead_lists.id", ondelete="SET NULL"),
        nullable=True,
    )
    list_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    combo_label: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Ex: 'academias em São Paulo' ou 'CEO, Sócio — Curitiba'",
    )
    leads_received: Mapped[int] = mapped_column(Integer, default=0)
    leads_inserted: Mapped[int] = mapped_column(Integer, default=0)
    leads_skipped: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(
        String(20),
        default="success",
        comment="'success' | 'failed'",
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )
