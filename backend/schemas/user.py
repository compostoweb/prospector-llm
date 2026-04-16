"""
schemas/user.py

Schemas Pydantic v2 para usuários humanos (autenticação via Google OAuth).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from models.enums import TenantRole


class UserResponse(BaseModel):
    """Dados do usuário autenticado — retornado em GET /auth/me."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    email: str
    name: str | None
    is_active: bool
    is_superuser: bool
    tenant_id: uuid.UUID | None = None
    tenant_role: TenantRole | None = None
    created_at: datetime


class GoogleLoginUrlResponse(BaseModel):
    """
    URL de autorização do Google.
    O cliente deve redirecionar o usuário para esta URL.
    """

    authorization_url: str


class UserTokenResponse(BaseModel):
    """Resposta do callback OAuth — JWT + metadados do usuário logado."""

    access_token: str
    token_type: str = "bearer"
    email: str
    name: str | None
    is_superuser: bool
    tenant_id: uuid.UUID | None = None
    tenant_role: TenantRole | None = None


class UserCreateRequest(BaseModel):
    """
    Adiciona um email à allowlist de acesso.
    Usado pelo superadmin em POST /admin/users.
    """

    email: EmailStr
    name: str | None = Field(default=None, max_length=300)
    is_superuser: bool = False
