"""
models/anthropic_batch_job.py

Model para rastrear jobs submetidos à Anthropic Message Batches API.

A Batch API processa até 100.000 requests de forma assíncrona (até 24h),
com desconto de 50% sobre os preços padrão.

Fluxo de estados:
  in_progress → ended (sucesso)
             ↘ failed (erro interno do batch)
             ↘ canceling → ended (cancelado pelo usuário)
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TenantMixin, TimestampMixin


class AnthropicBatchJob(Base, TenantMixin, TimestampMixin):
    """
    Representa um Message Batch submetido à Anthropic Batches API.

    O `lead_ids_json` armazena a lista de UUIDs dos leads incluídos no batch.
    A correlação dos resultados é feita via `custom_id` = str(lead.id).
    """

    __tablename__ = "anthropic_batch_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    # ID retornado pela Anthropic API (ex: "msgbatch_01HkcTjaV5uDC8jWR4ZsDV8d")
    anthropic_batch_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    # Tipo de job — extensível para outros casos de uso
    job_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="lead_analysis",
        comment="Tipo do batch: lead_analysis (único por enquanto)",
    )

    # Status atual do batch
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="in_progress",
        index=True,
        comment="in_progress | ended | failed | canceling",
    )

    # JSON list de UUIDs dos leads: ["uuid1", "uuid2", ...]
    lead_ids_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="JSON array de UUIDs dos leads incluídos neste batch",
    )

    # URL para download dos resultados (disponível após status=ended)
    results_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        default=None,
    )

    # Contadores de resultados
    request_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    succeeded_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expired_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Quando o batch foi processado pela Anthropic
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    # Modelo usado no batch
    model: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="claude-haiku-4-5",
        comment="Modelo Anthropic usado para analisar os leads",
    )
