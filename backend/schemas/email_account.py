"""
schemas/email_account.py

Schemas Pydantic v2 para EmailAccount — request/response da API REST.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

# ── Criação: Unipile ──────────────────────────────────────────────────


class EmailAccountUnipileCreateRequest(BaseModel):
    """Conectar conta Gmail via Unipile (account_id já configurado lá)."""

    display_name: str = Field(max_length=200)
    email_address: EmailStr
    from_name: str | None = Field(default=None, max_length=200)
    unipile_account_id: str = Field(
        description="account_id da conta Gmail no Unipile",
    )
    daily_send_limit: int = Field(default=50, ge=1, le=1000)


# ── Criação: SMTP ─────────────────────────────────────────────────────


class EmailAccountSMTPCreateRequest(BaseModel):
    """Conectar conta via SMTP genérico."""

    display_name: str = Field(max_length=200)
    email_address: EmailStr
    from_name: str | None = Field(default=None, max_length=200)
    smtp_host: str = Field(max_length=255)
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str = Field(max_length=255)
    smtp_password: str = Field(description="Senha SMTP — será criptografada")
    smtp_use_tls: bool = True
    daily_send_limit: int = Field(default=50, ge=1, le=1000)
    # IMAP — opcional para polling de replies
    imap_host: str | None = Field(default=None, max_length=255)
    imap_port: int | None = Field(default=None, ge=1, le=65535)
    imap_use_ssl: bool = True
    imap_password: str | None = Field(
        default=None,
        description="Senha IMAP (deixe em branco para usar a mesma senha SMTP)",
    )


class SMTPTestRequest(BaseModel):
    """Testa conexão SMTP sem salvar a conta."""

    smtp_host: str
    smtp_port: int = 587
    smtp_username: str
    smtp_password: str
    smtp_use_tls: bool = True


class SMTPTestResponse(BaseModel):
    ok: bool
    error: str | None = None


# ── Update parcial ────────────────────────────────────────────────────


class EmailAccountUpdateRequest(BaseModel):
    """Campos editáveis de uma conta já conectada."""

    display_name: str | None = Field(default=None, max_length=200)
    from_name: str | None = Field(default=None, max_length=200)
    daily_send_limit: int | None = Field(default=None, ge=1, le=1000)
    is_active: bool | None = None
    is_warmup_enabled: bool | None = None
    email_signature: str | None = Field(default=None)
    # IMAP — editável após criação da conta SMTP
    imap_host: str | None = Field(default=None, max_length=255)
    imap_port: int | None = Field(default=None, ge=1, le=65535)
    imap_use_ssl: bool | None = None
    imap_password: str | None = Field(
        default=None,
        description="Nova senha IMAP (só enviada quando alterar)",
    )


# ── Response ──────────────────────────────────────────────────────────


class EmailAccountResponse(BaseModel):
    """Resposta da API com dados públicos (sem tokens/senhas)."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    display_name: str
    email_address: str
    owner_user_id: uuid.UUID | None = None
    owner_email: str | None = None
    owner_name: str | None = None
    created_by_user_id: uuid.UUID | None = None
    from_name: str | None
    provider_type: str
    effective_provider_type: str
    outbound_uses_fallback: bool = False
    unipile_account_id: str | None
    smtp_host: str | None
    smtp_port: int | None
    smtp_username: str | None
    smtp_use_tls: bool
    imap_host: str | None
    imap_port: int | None
    imap_use_ssl: bool
    daily_send_limit: int
    is_active: bool
    provider_status: str | None = None
    last_status_at: datetime | None = None
    last_health_check_at: datetime | None = None
    health_error: str | None = None
    connected_at: datetime | None = None
    disconnected_at: datetime | None = None
    reconnect_required_at: datetime | None = None
    is_warmup_enabled: bool
    email_signature: str | None
    created_at: datetime
    updated_at: datetime


class EmailAccountListResponse(BaseModel):
    accounts: list[EmailAccountResponse]
    total: int


class GmailSignatureResponse(BaseModel):
    """Assinatura retornada da API do Gmail."""

    signature: str | None
    send_as_email: str
    display_name: str | None = None


# ── OAuth (Google) ────────────────────────────────────────────────────


class GoogleOAuthUrlResponse(BaseModel):
    """URL para iniciar o fluxo OAuth do Google."""

    auth_url: str


class GoogleOAuthCallbackRequest(BaseModel):
    """Chamado pelo frontend ao receber o code do Google."""

    code: str
    state: str
    display_name: str = Field(max_length=200)
    from_name: str | None = Field(default=None, max_length=200)
    daily_send_limit: int = Field(default=50, ge=1, le=1000)


# ── Status ────────────────────────────────────────────────────────────


class EmailAccountStatusResponse(BaseModel):
    """Resultado de um ping ao provider da conta."""

    account_id: uuid.UUID
    email_address: str
    provider_type: str
    is_reachable: bool
    error: str | None = None
