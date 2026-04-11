"""
models/lead_list.py

Model LeadList — listas manuais de leads.

Responsabilidades:
  - Agrupar leads em listas nomeadas pelo usuário
  - Relação M:N via tabela associativa lead_list_members
  - Integrar com tenant via TenantMixin (RLS automático)
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey, String, Table
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TenantMixin, TimestampMixin

if TYPE_CHECKING:
    from models.lead import Lead


# Tabela associativa M:N entre lead_lists e leads
lead_list_members = Table(
    "lead_list_members",
    Base.metadata,
    Column(
        "lead_list_id",
        PGUUID(as_uuid=True),
        ForeignKey("lead_lists.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "lead_id",
        PGUUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class LeadList(Base, TenantMixin, TimestampMixin):
    """
    Uma lista nomeada de leads criada pelo usuário.
    """

    __tablename__ = "lead_lists"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationship M:N
    leads: Mapped[list[Lead]] = relationship(
        "Lead",
        secondary=lead_list_members,
        back_populates="lists",
        lazy="selectin",
    )
