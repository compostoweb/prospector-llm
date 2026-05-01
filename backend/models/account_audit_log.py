"""
models/account_audit_log.py

Trilha operacional de eventos de contas conectadas por tenant e usuário.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TenantMixin, TimestampMixin


class AccountAuditLog(Base, TenantMixin, TimestampMixin):
    __tablename__ = "account_audit_logs"
    __table_args__ = (Index("ix_account_audit_logs_tenant_created", "tenant_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    account_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    external_account_id: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    provider_type: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    provider_status: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_metadata: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
