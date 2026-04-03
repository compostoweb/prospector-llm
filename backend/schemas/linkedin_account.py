"""
schemas/linkedin_account.py

Schemas Pydantic v2 para LinkedInAccount — request/response da API REST.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ── Criação: Unipile ──────────────────────────────────────────────────

class LinkedInAccountUnipileCreateRequest(BaseModel):
    """Conectar conta LinkedIn via Unipile (account_id já configurado lá)."""

    display_name: str = Field(max_length=200)
    linkedin_username: str | None = Field(default=None, max_length=200)
    unipile_account_id: str = Field(
        description="account_id da conta LinkedIn no Unipile",
    )


# ── Criação: Native (cookie li_at) ────────────────────────────────────

class LinkedInAccountNativeCreateRequest(BaseModel):
    """Conectar conta LinkedIn via cookie li_at (provider nativo)."""

    display_name: str = Field(max_length=200)
    linkedin_username: str = Field(
        max_length=200,
        description="Username do LinkedIn (parte final da URL do perfil)",
    )
    li_at_cookie: str = Field(
        description="Cookie li_at extraído do browser (será criptografado)",
    )


# ── Update parcial ────────────────────────────────────────────────────

class LinkedInAccountUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=200)
    linkedin_username: str | None = Field(default=None, max_length=200)
    is_active: bool | None = None


# ── Response ──────────────────────────────────────────────────────────

class LinkedInAccountResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    display_name: str
    linkedin_username: str | None
    provider_type: str
    unipile_account_id: str | None
    # li_at_cookie NUNCA exposto na API
    is_active: bool
    last_polled_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LinkedInAccountListResponse(BaseModel):
    accounts: list[LinkedInAccountResponse]
    total: int


class LinkedInAccountStatusResponse(BaseModel):
    account_id: uuid.UUID
    is_active: bool
    provider_type: str
    ping_ok: bool
    error: str | None = None
