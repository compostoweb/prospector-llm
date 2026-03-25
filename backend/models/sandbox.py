"""
models/sandbox.py

Models SandboxRun e SandboxStep — sandbox de teste de cadências.

Responsabilidades:
  - SandboxRun: representa uma execução de sandbox (dry-run) de uma cadência
  - SandboxStep: representa um step simulado dentro do sandbox run

O sandbox permite testar a cadência antes de ativá-la:
  - Preview de mensagens geradas pela IA
  - Simulação de timeline com rate limits
  - Simulação de replies (auto/manual) com classificação de intent
  - Dry-run de integração Pipedrive

Zero side-effects: nenhuma mensagem é enviada via Unipile.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TenantMixin, TimestampMixin
from models.enums import (
    Channel,
    Intent,
    SandboxLeadSource,
    SandboxRunStatus,
    SandboxStepStatus,
)


class SandboxRun(Base, TenantMixin, TimestampMixin):
    """
    Representa uma execução de sandbox (dry-run) de uma cadência.
    Agrupa N SandboxSteps para N leads × M steps do template.
    """

    __tablename__ = "sandbox_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    cadence_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cadences.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status: Mapped[SandboxRunStatus] = mapped_column(
        SAEnum(SandboxRunStatus, name="sandbox_run_status"),
        default=SandboxRunStatus.RUNNING,
        nullable=False,
    )

    lead_source: Mapped[SandboxLeadSource] = mapped_column(
        SAEnum(SandboxLeadSource, name="sandbox_lead_source"),
        nullable=False,
    )

    # Dry-run Pipedrive — armazena preview de deals/persons
    pipedrive_dry_run: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        default=None,
    )

    # ── Relacionamentos ───────────────────────────────────────────────
    cadence: Mapped["Cadence"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Cadence",
        lazy="select",
    )
    steps: Mapped[list["SandboxStep"]] = relationship(
        "SandboxStep",
        back_populates="sandbox_run",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="SandboxStep.step_number, SandboxStep.lead_id",
    )


class SandboxStep(Base, TenantMixin, TimestampMixin):
    """
    Representa um step simulado dentro de um sandbox run.
    Cada step é a combinação de 1 lead × 1 step do template da cadência.
    """

    __tablename__ = "sandbox_steps"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    sandbox_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sandbox_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Lead real (nullable — None para leads fictícios)
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Dados do lead fictício (JSONB) — usado quando lead_id is None
    fictitious_lead_data: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        default=None,
    )

    # ── Canal e posição ───────────────────────────────────────────────
    channel: Mapped[Channel] = mapped_column(
        SAEnum(Channel, name="cadence_step_channel", create_type=False),
        nullable=False,
    )
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    day_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    use_voice: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── Preview de timeline ───────────────────────────────────────────
    scheduled_at_preview: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # ── Mensagem gerada pela IA ───────────────────────────────────────
    message_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_preview_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    email_subject: Mapped[str | None] = mapped_column(String(300), nullable=True)

    # ── Status do step ────────────────────────────────────────────────
    status: Mapped[SandboxStepStatus] = mapped_column(
        SAEnum(SandboxStepStatus, name="sandbox_step_status"),
        default=SandboxStepStatus.PENDING,
        nullable=False,
    )

    # ── Info LLM ──────────────────────────────────────────────────────
    llm_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    llm_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tokens_in: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_out: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── Simulação de reply (inbound) ──────────────────────────────────
    simulated_reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    simulated_intent: Mapped[Intent | None] = mapped_column(
        SAEnum(Intent, name="interaction_intent", create_type=False),
        nullable=True,
    )
    simulated_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    simulated_reply_summary: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # ── Simulação de rate limit ───────────────────────────────────────
    is_rate_limited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rate_limit_reason: Mapped[str | None] = mapped_column(String(300), nullable=True)
    adjusted_scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ── Relacionamentos ───────────────────────────────────────────────
    sandbox_run: Mapped["SandboxRun"] = relationship(
        "SandboxRun",
        back_populates="steps",
    )
    lead: Mapped["Lead | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Lead",
        lazy="select",
    )
