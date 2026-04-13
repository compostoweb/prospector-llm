"""
models/cadence_step.py

Model CadenceStep — representa um envio agendado dentro de uma cadência.

Responsabilidades:
  - Armazenar cada step (canal + número + dia) de um lead em uma cadência
  - Controlar o status de execução (pending → sent/skipped/failed)
  - Permitir voice note (só para linkedin_dm)
  - Ser consultado pelo cadence_worker a cada minuto (Beat tick)

Fluxo:
  cadence_manager.enroll() cria os CadenceSteps com day_offset calculados.
  cadence_worker.tick() busca steps com scheduled_at <= now() e status=pending.
  dispatch_worker.dispatch_step() executa o envio e atualiza o status.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TenantMixin
from models.enums import Channel, StepStatus


class CadenceStep(Base, TenantMixin):
    """
    Representa um único envio planejado de uma cadência para um lead.
    Um lead em cadência tem N steps, um por canal/dia configurado.
    """

    __tablename__ = "cadence_steps"

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

    # ── Canal e posição ───────────────────────────────────────────────
    channel: Mapped[Channel] = mapped_column(
        SAEnum(Channel, name="cadence_step_channel"),
        nullable=False,
    )
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    day_offset: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Dias após o início da cadência para enviar este step",
    )

    # ── Voice note (apenas linkedin_dm) ──────────────────────────────
    use_voice: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Se True, gera audio MP3 via Speechify e envia como voice note",
    )

    # ── Áudio pré-gravado (alternativa ao TTS) ───────────────────────
    audio_file_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("audio_files.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
        comment="Se preenchido, usa áudio pré-gravado ao invés de TTS",
    )

    # ── Status e agendamento ──────────────────────────────────────────
    status: Mapped[StepStatus] = mapped_column(
        SAEnum(StepStatus, name="cadence_step_status"),
        default=StepStatus.PENDING,
        nullable=False,
        index=True,
    )
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Momento em que este step deve ser disparado",
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # ── A/B de assunto (cold email) ───────────────────────────────────
    subject_used: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        default=None,
        comment="Variante de assunto usada no envio (A/B testing). NULL = subject padrão.",
    )

    # ── Cache de composição LLM (evita recomposição em retry) ─────────
    composed_text: Mapped[str | None] = mapped_column(
        Text(),
        nullable=True,
        default=None,
        comment="Cache do texto/body gerado pela LLM — evita recomposição em retry",
    )
    composed_subject: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        default=None,
        comment="Cache do subject gerado pela LLM (email) — evita recomposição em retry",
    )

    # ── Relacionamentos ───────────────────────────────────────────────
    cadence: Mapped[Cadence] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Cadence",
        lazy="select",
    )
    lead: Mapped[Lead] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Lead",
        lazy="select",
    )
