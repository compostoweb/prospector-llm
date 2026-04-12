"""
models/llm_usage_hourly.py

Agregados horários de consumo de LLM para analytics rápidos.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TenantMixin, TimestampMixin


class LLMUsageHourlyAggregate(Base, TenantMixin, TimestampMixin):
    __tablename__ = "llm_usage_hourly"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "bucket_start",
            "provider",
            "model",
            "module",
            "task_type",
            "feature",
            name="uq_llm_usage_hourly_bucket_dimensions",
        ),
    )

    bucket_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    provider: Mapped[str] = mapped_column(String(50), primary_key=True)
    model: Mapped[str] = mapped_column(String(120), primary_key=True)
    module: Mapped[str] = mapped_column(String(80), primary_key=True)
    task_type: Mapped[str] = mapped_column(String(80), primary_key=True)
    feature: Mapped[str] = mapped_column(String(80), primary_key=True, default="")
    requests: Mapped[int] = mapped_column(default=0, nullable=False)
    input_tokens: Mapped[int] = mapped_column(default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(default=0, nullable=False)
    estimated_cost_usd: Mapped[float] = mapped_column(default=0.0, nullable=False)