"""
models/llm_usage_event.py

Eventos de consumo de LLM por tenant, módulo e tarefa.
Servem como base para analytics de tokens/custo e otimizações operacionais.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TenantMixin, TimestampMixin


class LLMUsageEvent(Base, TenantMixin, TimestampMixin):
    __tablename__ = "llm_usage_events"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    module: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    task_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    feature: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    secondary_entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    secondary_entity_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    prompt_chars: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_chars: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    is_estimated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    request_metadata: Mapped[dict[str, object] | None] = mapped_column(
        JSONB(astext_type=Text()),
        nullable=True,
    )