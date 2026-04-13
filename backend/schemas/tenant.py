"""
schemas/tenant.py

Schemas Pydantic v2 para Tenant e TenantIntegration.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class TenantCreateRequest(BaseModel):
    """Onboarding de novo tenant/cliente."""

    name: str = Field(..., min_length=2, max_length=200)
    slug: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")


class TenantResponse(BaseModel):
    """Dados do tenant autenticado."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    slug: str
    is_active: bool
    created_at: datetime
    integration: TenantIntegrationResponse | None = None


class TenantCreateResponse(TenantResponse):
    """
    Resposta exclusiva da criação de tenant.
    Inclui a api_key em plaintext — exibida UMA única vez.
    Nunca retornada em outros endpoints.
    """

    api_key: str  # plaintext — não armazenado, só retornado aqui


class TenantIntegrationUpdate(BaseModel):
    """
    Atualização parcial das integrações do tenant.
    Todos os campos são opcionais para UPDATE parcial via PUT.
    """

    # Unipile
    unipile_linkedin_account_id: str | None = None
    unipile_gmail_account_id: str | None = None

    # Pipedrive
    pipedrive_domain: str | None = None
    pipedrive_api_token: str | None = None
    pipedrive_owner_id: int | None = None
    pipedrive_stage_interest: int | None = None
    pipedrive_stage_objection: int | None = None

    # Notificações
    notify_email: str | None = None
    notify_on_interest: bool | None = None
    notify_on_objection: bool | None = None

    # Configurações de envio
    allow_personal_email: bool | None = None
    limit_linkedin_connect: int | None = Field(default=None, ge=1, le=50)
    limit_linkedin_dm: int | None = Field(default=None, ge=1, le=100)
    limit_email: int | None = Field(default=None, ge=1, le=500)

    # LLM — padrão do sistema
    llm_default_provider: str | None = Field(default=None, max_length=50)
    llm_default_model: str | None = Field(default=None, max_length=100)
    llm_default_temperature: float | None = Field(default=None, ge=0.0, le=1.0)
    llm_default_max_tokens: int | None = Field(default=None, ge=64, le=8192)

    # LLM — padrão Cold Email
    cold_email_llm_provider: str | None = Field(default=None, max_length=50)
    cold_email_llm_model: str | None = Field(default=None, max_length=100)
    cold_email_llm_temperature: float | None = Field(default=None, ge=0.0, le=1.0)
    cold_email_llm_max_tokens: int | None = Field(default=None, ge=64, le=8192)


class TenantIntegrationResponse(BaseModel):
    """Dados das integrações do tenant (sem expor tokens sensíveis em texto limpo)."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    unipile_linkedin_account_id: str | None
    unipile_gmail_account_id: str | None
    pipedrive_api_token_set: bool = False
    pipedrive_domain: str | None
    pipedrive_owner_id: int | None
    pipedrive_stage_interest: int | None
    pipedrive_stage_objection: int | None
    notify_email: str | None
    notify_on_interest: bool
    notify_on_objection: bool
    allow_personal_email: bool
    limit_linkedin_connect: int
    limit_linkedin_dm: int
    limit_email: int
    # LLM — padrão do sistema
    llm_default_provider: str
    llm_default_model: str
    llm_default_temperature: float
    llm_default_max_tokens: int
    # LLM — padrão Cold Email
    cold_email_llm_provider: str
    cold_email_llm_model: str
    cold_email_llm_temperature: float
    cold_email_llm_max_tokens: int
    created_at: datetime


class UnipileWebhookStatusResponse(BaseModel):
    """Status operacional do webhook da Unipile para o tenant atual."""

    url: str
    docs_url: str
    dashboard_url: str
    expected_events: list[str]
    secret_configured: bool
    public_endpoint_healthy: bool
    public_endpoint_status_code: int | None
    linkedin_account_configured: bool
    gmail_account_configured: bool
    api_registration_supported: bool
    api_registration_ready: bool
    api_registration_blockers: list[str]
    registered_in_unipile: bool
    registered_webhook_id: str | None
    registered_webhook_enabled: bool | None
    registered_webhook_source: str | None
    registered_webhook_events: list[str]
    registration_lookup_error: str | None
    supports_signature_auth: bool = True
    supports_custom_header_auth: bool = True
    auth_headers: list[Literal["X-Unipile-Signature", "Unipile-Auth"]]
    ready: bool


class UnipileWebhookRegistrationResponse(BaseModel):
    """Resultado do registro automático do webhook da Unipile."""

    created: bool
    already_exists: bool
    webhook_id: str | None
    request_url: str
    source: Literal["messaging"]
    auth_header: Literal["Unipile-Auth"]
    events: list[str]
    message: str
