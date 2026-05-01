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
    supports_inmail: bool = Field(
        default=False,
        description="Marque true quando esta conta emissora puder enviar InMail.",
    )
    unipile_account_id: str = Field(
        description="account_id da conta LinkedIn no Unipile",
    )


class LinkedInAccountHostedAuthRequest(BaseModel):
    """Gerar link Hosted Auth da Unipile para conectar LinkedIn."""

    display_name: str = Field(max_length=200)
    linkedin_username: str | None = Field(default=None, max_length=200)
    supports_inmail: bool = Field(
        default=False,
        description="Marque true quando esta conta emissora puder enviar InMail.",
    )


class LinkedInAccountHostedAuthResponse(BaseModel):
    auth_url: str


# ── Criação: Native (cookie li_at) ────────────────────────────────────


class LinkedInAccountNativeCreateRequest(BaseModel):
    """Conectar conta LinkedIn via cookie li_at (provider nativo)."""

    display_name: str = Field(max_length=200)
    linkedin_username: str = Field(
        max_length=200,
        description="Username do LinkedIn (parte final da URL do perfil)",
    )
    supports_inmail: bool = Field(
        default=False,
        description="Marque true quando esta conta emissora puder enviar InMail.",
    )
    li_at_cookie: str = Field(
        description="Cookie li_at extraído do browser (será criptografado)",
    )


# ── Update parcial ────────────────────────────────────────────────────


class LinkedInAccountUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=200)
    linkedin_username: str | None = Field(default=None, max_length=200)
    is_active: bool | None = None
    supports_inmail: bool | None = None


# ── Response ──────────────────────────────────────────────────────────


class LinkedInAccountResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    display_name: str
    linkedin_username: str | None
    owner_user_id: uuid.UUID | None = None
    owner_email: str | None = None
    owner_name: str | None = None
    created_by_user_id: uuid.UUID | None = None
    provider_type: str
    unipile_account_id: str | None
    # li_at_cookie NUNCA exposto na API
    is_active: bool
    supports_inmail: bool
    provider_status: str | None = None
    last_status_at: datetime | None = None
    last_health_check_at: datetime | None = None
    health_error: str | None = None
    connected_at: datetime | None = None
    disconnected_at: datetime | None = None
    reconnect_required_at: datetime | None = None
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
