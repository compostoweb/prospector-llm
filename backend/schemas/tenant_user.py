"""
schemas/tenant_user.py

Schemas para gestão de membros de tenant.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from models.enums import TenantRole


class TenantUserInviteRequest(BaseModel):
    email: EmailStr
    name: str | None = Field(default=None, max_length=300)
    role: TenantRole = TenantRole.TENANT_USER


class TenantUserUpdateRequest(BaseModel):
    role: TenantRole
    is_active: bool | None = None


class TenantUserResponse(BaseModel):
    model_config = {"from_attributes": True}

    membership_id: uuid.UUID
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    name: str | None
    role: TenantRole
    is_active: bool
    is_superuser: bool
    joined_at: datetime
    invited_by_email: str | None = None
    created_at: datetime
    updated_at: datetime
