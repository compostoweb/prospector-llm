"""
models/linkedin_search_param.py

Cache global de parâmetros de busca LinkedIn (LOCATION, INDUSTRY).
Dados globais do LinkedIn, não vinculados a tenant.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class LinkedInSearchParam(Base):
    """Cache de parâmetros de busca LinkedIn (localização, setor)."""

    __tablename__ = "linkedin_search_params"
    __table_args__ = (
        UniqueConstraint("param_type", "external_id", name="uq_li_search_param_type_eid"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    param_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )
