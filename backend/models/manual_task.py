"""
models/manual_task.py

Model ManualTask — tarefa manual da cadência semi-automática.

Ciclo de vida:
  PENDING → CONTENT_GENERATED → SENT | DONE_EXTERNAL | SKIPPED

Criada automaticamente quando:
  - Cadência semi-manual detecta aceite de conexão LinkedIn
  - Webhook relation_created ou polling fallback dispara criação
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TenantMixin, TimestampMixin
from models.enums import Channel, ManualTaskStatus


class ManualTask(Base, TenantMixin, TimestampMixin):
    """
    Tarefa manual gerada por cadência semi-automática.
    O operador revisa conteúdo LLM, edita e envia via sistema ou marca como feita.
    """

    __tablename__ = "manual_tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    # ── Referências ───────────────────────────────────────────────────
    cadence_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cadences.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cadence_step_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("cadence_steps.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
    )

    # ── Canal e status ────────────────────────────────────────────────
    channel: Mapped[Channel] = mapped_column(
        SAEnum(Channel, name="channel"),
        nullable=False,
    )
    step_number: Mapped[int] = mapped_column(nullable=False, default=1)
    status: Mapped[ManualTaskStatus] = mapped_column(
        SAEnum(ManualTaskStatus, name="manual_task_status"),
        default=ManualTaskStatus.PENDING,
        nullable=False,
        index=True,
    )

    # ── Conteúdo gerado/editado ───────────────────────────────────────
    generated_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_audio_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    edited_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Envio ─────────────────────────────────────────────────────────
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    unipile_message_id: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # ── Notas do operador ─────────────────────────────────────────────
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ─────────────────────────────────────────────────
    lead = relationship("Lead", lazy="selectin")
    cadence = relationship("Cadence", lazy="selectin")

    @property
    def cadence_name(self) -> str | None:
        return self.cadence.name if self.cadence is not None else None

    @property
    def manual_task_type(self) -> str | None:
        return self._template_step_value("manual_task_type")

    @property
    def manual_task_detail(self) -> str | None:
        return self._template_step_value("manual_task_detail")

    def _template_step_value(self, key: str) -> str | None:
        if self.cadence is None:
            return None

        from services.cadence_manager import get_template_step_config

        step_config = get_template_step_config(self.cadence, self.step_number)
        value: Any = step_config.get(key) if step_config else None
        if value is None:
            return None
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned or None
        return str(value)
