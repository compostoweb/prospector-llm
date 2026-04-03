"""
models/email_unsubscribe.py

Registro de descadastros de e-mail (unsubscribe).
Consultado antes de cada envio outbound — leads listados aqui têm steps de e-mail PULADOS.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TenantMixin


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EmailUnsubscribe(Base, TenantMixin):
    """
    Registro de descadastro de um endereço de e-mail.
    Por tenant: um e-mail descadastrado em um tenant não afeta outros tenants.
    """

    __tablename__ = "email_unsubscribes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    email: Mapped[str] = mapped_column(
        String(254),
        nullable=False,
        index=True,
        comment="Endereço descadastrado (lowercase)",
    )
    reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        default=None,
        comment="Motivo informado pelo destinatário (opcional)",
    )
    unsubscribed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )
