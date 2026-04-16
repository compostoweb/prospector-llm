"""
models/tenant_user.py

Vínculo entre usuário humano e tenant com papel de acesso.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TenantMixin, TimestampMixin
from models.enums import TenantRole

if TYPE_CHECKING:
    from models.tenant import Tenant
    from models.user import User


def _utcnow() -> datetime:
    return datetime.now(UTC)


class TenantUser(TenantMixin, TimestampMixin, Base):
    """Membership de um usuário humano dentro de um tenant."""

    __tablename__ = "tenant_users"
    __table_args__ = (UniqueConstraint("tenant_id", "user_id", name="uq_tenant_users_tenant_user"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[TenantRole] = mapped_column(
        Enum(TenantRole, name="tenant_user_role"),
        nullable=False,
        default=TenantRole.TENANT_USER,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    invited_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )

    tenant: Mapped[Tenant] = relationship("Tenant", back_populates="members")
    user: Mapped[User] = relationship(
        "User",
        back_populates="memberships",
        foreign_keys=[user_id],
    )
    invited_by_user: Mapped[User | None] = relationship(
        "User",
        back_populates="invited_memberships",
        foreign_keys=[invited_by_user_id],
    )
