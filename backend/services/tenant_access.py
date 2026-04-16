"""
services/tenant_access.py

Helpers para resolver contexto de acesso e memberships de tenant.
"""

from __future__ import annotations

import uuid

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from models.enums import TenantRole
from models.tenant import Tenant
from models.tenant_user import TenantUser
from models.user import User


async def resolve_default_active_tenant_id(db: AsyncSession) -> uuid.UUID | None:
    result = await db.execute(
        select(Tenant.id)
        .where(Tenant.is_active.is_(True))
        .order_by((Tenant.slug == settings.DEFAULT_TENANT_SLUG).desc(), Tenant.created_at.asc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def resolve_user_login_context(
    db: AsyncSession,
    user: User,
) -> tuple[uuid.UUID | None, TenantRole | None]:
    if user.is_superuser:
        return await resolve_default_active_tenant_id(db), None

    result = await db.execute(
        select(TenantUser.tenant_id, TenantUser.role)
        .join(Tenant, Tenant.id == TenantUser.tenant_id)
        .where(
            TenantUser.user_id == user.id,
            TenantUser.is_active.is_(True),
            Tenant.is_active.is_(True),
        )
        .order_by(
            case((TenantUser.role == TenantRole.TENANT_ADMIN, 0), else_=1),
            TenantUser.joined_at.asc(),
        )
        .limit(1)
    )
    row = result.one_or_none()
    if row is None:
        return None, None
    return row.tenant_id, row.role


async def get_active_membership(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> TenantUser | None:
    result = await db.execute(
        select(TenantUser)
        .join(Tenant, Tenant.id == TenantUser.tenant_id)
        .where(
            TenantUser.user_id == user_id,
            TenantUser.tenant_id == tenant_id,
            TenantUser.is_active.is_(True),
            Tenant.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def upsert_tenant_membership(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    email: str,
    role: TenantRole,
    invited_by_user_id: uuid.UUID | None,
    name: str | None = None,
) -> tuple[User, TenantUser, bool]:
    normalized_email = email.lower().strip()
    user_result = await db.execute(select(User).where(User.email == normalized_email))
    user = user_result.scalar_one_or_none()
    created_user = False

    if user is None:
        user = User(
            email=normalized_email,
            name=name,
            is_active=True,
            is_superuser=False,
        )
        db.add(user)
        await db.flush()
        created_user = True
    else:
        user.is_active = True
        if name and not user.name:
            user.name = name

    membership_result = await db.execute(
        select(TenantUser).where(
            TenantUser.tenant_id == tenant_id,
            TenantUser.user_id == user.id,
        )
    )
    membership = membership_result.scalar_one_or_none()
    if membership is None:
        membership = TenantUser(
            tenant_id=tenant_id,
            user_id=user.id,
            role=role,
            is_active=True,
            invited_by_user_id=invited_by_user_id,
        )
        db.add(membership)
        await db.flush()
    else:
        membership.role = role
        membership.is_active = True
        membership.invited_by_user_id = invited_by_user_id

    return user, membership, created_user


async def count_active_members(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    role: TenantRole | None = None,
) -> int:
    conditions = [TenantUser.tenant_id == tenant_id, TenantUser.is_active.is_(True)]
    if role is not None:
        conditions.append(TenantUser.role == role)
    result = await db.execute(select(func.count(TenantUser.id)).where(*conditions))
    return int(result.scalar_one() or 0)
