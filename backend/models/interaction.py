"""
models/interaction.py

Model Interaction — registro de mensagens enviadas e recebidas.

Responsabilidades:
  - Registrar cada mensagem outbound enviada para um lead
  - Registrar cada mensagem inbound recebida de um lead
  - Armazenar conteúdo de texto e/ou URL de áudio (LinkedIn DM de voz)
  - Guardar a intenção detectada pelo ReplyParser em mensagens inbound
  - Rastrear leitura de emails (campo opened)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TenantMixin
from models.enums import Channel, Intent, InteractionDirection


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Interaction(Base, TenantMixin):
    """
    Representa uma mensagem trocada com um lead em qualquer canal.
    direction="outbound" → enviada pelo sistema
    direction="inbound"  → recebida do lead (resposta)
    """

    __tablename__ = "interactions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    # ── Lead associado ────────────────────────────────────────────────
    lead_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cadence_step_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cadence_steps.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ── Canal e direção ───────────────────────────────────────────────
    channel: Mapped[Channel] = mapped_column(
        SAEnum(Channel, name="interaction_channel"),
        nullable=False,
        index=True,
    )
    direction: Mapped[InteractionDirection] = mapped_column(
        SAEnum(InteractionDirection, name="interaction_direction"),
        nullable=False,
    )

    # ── Conteúdo ──────────────────────────────────────────────────────
    content_text: Mapped[str | None] = mapped_column(Text)
    content_audio_url: Mapped[str | None] = mapped_column(String(1000))

    # ── Intenção (preenchida pelo ReplyParser em mensagens inbound) ───
    intent: Mapped[Intent | None] = mapped_column(
        SAEnum(Intent, name="interaction_intent"),
        nullable=True,
    )

    # ── Metadados de canal ────────────────────────────────────────────
    unipile_message_id: Mapped[str | None] = mapped_column(String(200), index=True)
    email_message_id: Mapped[str | None] = mapped_column(String(255), index=True)
    provider_thread_id: Mapped[str | None] = mapped_column(String(255), index=True)
    reply_match_status: Mapped[str | None] = mapped_column(String(30), index=True)
    reply_match_source: Mapped[str | None] = mapped_column(String(50))
    reply_match_sent_cadence_count: Mapped[int | None] = mapped_column(Integer)
    opened: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    opened_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        comment="Timestamp da primeira abertura do e-mail (via tracking pixel).",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )

    # Relacionamento com Lead (lazy para evitar N+1 desnecessário)
    lead: Mapped["Lead"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Lead",
        lazy="select",
    )
