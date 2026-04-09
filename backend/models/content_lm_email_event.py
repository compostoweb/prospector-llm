"""
models/content_lm_email_event.py

Log normalizado de eventos de e-mail do SendPulse para métricas e auditoria.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TenantMixin


def _utcnow() -> datetime:
    from datetime import timezone

    return datetime.now(timezone.utc)


class ContentLMEmailEvent(Base, TenantMixin):
    __tablename__ = "content_lm_email_events"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "payload_hash",
            name="uq_content_lm_email_events_provider_payload_hash",
        ),
    )

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
    lm_lead_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("content_lm_leads.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    calculator_result_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("content_calculator_results.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(30), nullable=False, default="sendpulse", server_default="sendpulse")
    provider_event_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    event_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    link_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)