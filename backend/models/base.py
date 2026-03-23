"""
models/base.py

Base declarativa SQLAlchemy + mixins reutilizáveis.

Responsabilidades:
  - Definir a Base para todos os models SQLAlchemy do projeto
  - TenantMixin: adiciona tenant_id com FK para tenants.id (obrigatório em todas as tabelas)
  - TimestampMixin: adiciona created_at e updated_at com valores automáticos

Todos os models do projeto devem herdar de Base e incluir os mixins adequados.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Base declarativa para todos os models SQLAlchemy."""
    pass


class TenantMixin:
    """
    Mixin obrigatório em todas as tabelas multi-tenant.
    Adiciona tenant_id com FK para tenants.id e índice para performance.
    O PostgreSQL Row-Level Security usa esse campo via SET LOCAL app.current_tenant_id.
    """

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )


class TimestampMixin:
    """
    Mixin que adiciona created_at e updated_at com timezone UTC.
    updated_at é atualizado automaticamente a cada UPDATE.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )
