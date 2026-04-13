"""
api/routes/tenants.py

Rotas REST para gerenciamento de tenants (onboarding + integrações).

Endpoints:
  POST   /tenants                   — onboarding: cria Tenant + TenantIntegration
  GET    /tenants/me                — dados do tenant autenticado
  PUT    /tenants/me/integrations   — atualiza TenantIntegration (parcial)
"""

from __future__ import annotations

import ipaddress
import uuid
from collections.abc import AsyncGenerator
from secrets import token_urlsafe
from typing import Any
from urllib.parse import urlparse

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import (
    get_current_tenant_flexible,
    get_effective_tenant_id,
    get_session_flexible,
)
from api.routes.auth import hash_api_key
from core.config import settings
from core.database import AsyncSessionLocal
from integrations.unipile_client import UnipileNonRetryableError, unipile_client
from models.cadence import Cadence
from models.tenant import Tenant, TenantIntegration
from schemas.tenant import (
    TenantCreateRequest,
    TenantCreateResponse,
    TenantIntegrationResponse,
    TenantIntegrationUpdate,
    TenantResponse,
    UnipileWebhookRegistrationResponse,
    UnipileWebhookStatusResponse,
)
from services.content.theme_bank import seed_theme_bank_for_tenant

logger = structlog.get_logger()

router = APIRouter(prefix="/tenants", tags=["Tenants"])

_UNIPILE_WEBHOOK_EVENTS = [
    "message_received",
    "relation_created",
    "account_connected",
]
_UNIPILE_WEBHOOK_DOCS_URL = "https://developer.unipile.com/docs/webhooks-2"
_UNIPILE_WEBHOOK_DASHBOARD_URL = "https://dashboard.unipile.com"


# ── Helper: session sem RLS (para criação de tenant) ─────────────────


async def _get_raw_session() -> AsyncGenerator[AsyncSession, Any]:
    """
    Abre uma sessão sem injeção de tenant_id via RLS.
    Necessário para criar tenants antes de qualquer autenticação.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Onboarding ────────────────────────────────────────────────────────


@router.post("", response_model=TenantCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    body: TenantCreateRequest,
    db: AsyncSession = Depends(_get_raw_session),
) -> TenantCreateResponse:
    """
    Cria um novo tenant e gera a api_key.
    A api_key é retornada em plaintext APENAS nesta resposta — salve-a imediatamente.
    """
    existing = await db.execute(select(Tenant).where(Tenant.slug == body.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Slug já em uso.",
        )

    plaintext_key = token_urlsafe(32)
    tenant = Tenant(
        name=body.name,
        slug=body.slug,
        api_key_hash=hash_api_key(plaintext_key),
    )
    db.add(tenant)
    await db.flush()

    integration = TenantIntegration(tenant_id=tenant.id)
    db.add(integration)

    seeded = await seed_theme_bank_for_tenant(db, tenant.id)

    await db.commit()
    await db.refresh(tenant)

    logger.info("tenant.created", tenant_id=str(tenant.id), slug=body.slug)
    if seeded:
        logger.info("content.theme_bank_seeded", tenant_id=str(tenant.id), inserted=seeded)
    return TenantCreateResponse(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        is_active=tenant.is_active,
        created_at=tenant.created_at,
        api_key=plaintext_key,
    )


# ── Dados do tenant autenticado ───────────────────────────────────────


@router.get("/me", response_model=TenantResponse)
async def get_me(
    tenant: Tenant = Depends(get_current_tenant_flexible),
) -> TenantResponse:
    resp = TenantResponse.model_validate(tenant)
    if tenant.integration:
        int_resp = TenantIntegrationResponse.model_validate(tenant.integration)
        int_resp.pipedrive_api_token_set = bool(tenant.integration.pipedrive_api_token)
        resp.integration = int_resp
    return resp


@router.get("/me/unipile/webhook", response_model=UnipileWebhookStatusResponse)
async def get_unipile_webhook_status(
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> UnipileWebhookStatusResponse:
    """Retorna o status operacional do webhook da Unipile para o tenant atual."""
    result = await db.execute(
        select(TenantIntegration).where(TenantIntegration.tenant_id == tenant_id)
    )
    integration = result.scalar_one_or_none()

    url = _build_unipile_webhook_url()
    status_code = await _probe_unipile_webhook_endpoint(url)
    endpoint_healthy = status_code in {200, 401}
    secret = (settings.UNIPILE_WEBHOOK_SECRET or "").strip()
    secret_configured = bool(secret and secret != "...")
    api_registration_supported = bool(settings.UNIPILE_API_KEY and settings.UNIPILE_BASE_URL)
    api_registration_blockers = _get_unipile_webhook_registration_blockers(url=url)
    registered_webhook: dict[str, Any] | None = None
    registration_lookup_error: str | None = None
    if api_registration_supported:
        try:
            registered_webhook = await unipile_client.get_webhook_by_url(url)
        except UnipileNonRetryableError as exc:
            registration_lookup_error = str(exc)
            logger.warning(
                "tenant.unipile_webhook_lookup_rejected",
                tenant_id=str(tenant_id),
                error=registration_lookup_error,
                request_url=url,
            )
        except httpx.HTTPError as exc:
            registration_lookup_error = "Falha ao consultar webhooks existentes na Unipile."
            logger.warning(
                "tenant.unipile_webhook_lookup_failed",
                tenant_id=str(tenant_id),
                error=str(exc),
                request_url=url,
            )
    linkedin_account_configured = bool(
        (integration and integration.unipile_linkedin_account_id)
        or settings.UNIPILE_ACCOUNT_ID_LINKEDIN
    )
    gmail_account_configured = bool(
        (integration and integration.unipile_gmail_account_id) or settings.UNIPILE_ACCOUNT_ID_GMAIL
    )

    return UnipileWebhookStatusResponse(
        url=url,
        docs_url=_UNIPILE_WEBHOOK_DOCS_URL,
        dashboard_url=_UNIPILE_WEBHOOK_DASHBOARD_URL,
        expected_events=list(_UNIPILE_WEBHOOK_EVENTS),
        secret_configured=secret_configured,
        public_endpoint_healthy=endpoint_healthy,
        public_endpoint_status_code=status_code,
        linkedin_account_configured=linkedin_account_configured,
        gmail_account_configured=gmail_account_configured,
        api_registration_supported=api_registration_supported,
        api_registration_ready=not api_registration_blockers,
        api_registration_blockers=api_registration_blockers,
        registered_in_unipile=registered_webhook is not None,
        registered_webhook_id=_coerce_webhook_value(registered_webhook, "id", "webhook_id"),
        registered_webhook_enabled=_coerce_webhook_bool(registered_webhook, "enabled"),
        registered_webhook_source=_coerce_webhook_value(registered_webhook, "source"),
        registered_webhook_events=_coerce_webhook_events(registered_webhook),
        registration_lookup_error=registration_lookup_error,
        auth_headers=["X-Unipile-Signature", "Unipile-Auth"],
        ready=(
            secret_configured
            and endpoint_healthy
            and (linkedin_account_configured or gmail_account_configured)
        ),
    )


@router.post(
    "/me/unipile/webhook/register",
    response_model=UnipileWebhookRegistrationResponse,
)
async def register_unipile_webhook(
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
) -> UnipileWebhookRegistrationResponse:
    """Registra o webhook da Unipile via API para o tenant atual."""
    url = _build_unipile_webhook_url()
    blockers = _get_unipile_webhook_registration_blockers(url=url)
    if blockers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=" ".join(blockers),
        )

    secret = (settings.UNIPILE_WEBHOOK_SECRET or "").strip()

    try:
        result = await unipile_client.ensure_messaging_webhook(
            request_url=url,
            secret=secret,
            events=list(_UNIPILE_WEBHOOK_EVENTS),
        )
    except UnipileNonRetryableError as exc:
        logger.warning(
            "tenant.unipile_webhook_register_rejected",
            tenant_id=str(tenant_id),
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except httpx.HTTPError as exc:
        logger.error(
            "tenant.unipile_webhook_register_failed",
            tenant_id=str(tenant_id),
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao registrar webhook na Unipile.",
        ) from exc

    created = bool(result.get("created"))
    already_exists = bool(result.get("already_exists"))
    webhook_id_raw = result.get("webhook_id")
    webhook_id = str(webhook_id_raw) if webhook_id_raw else None

    logger.info(
        "tenant.unipile_webhook_registered",
        tenant_id=str(tenant_id),
        created=created,
        already_exists=already_exists,
        webhook_id=webhook_id,
        request_url=url,
    )

    return UnipileWebhookRegistrationResponse(
        created=created,
        already_exists=already_exists,
        webhook_id=webhook_id,
        request_url=url,
        source="messaging",
        auth_header="Unipile-Auth",
        events=list(_UNIPILE_WEBHOOK_EVENTS),
        message=(
            "Webhook registrado com sucesso na Unipile."
            if created
            else "Já existe um webhook ativo da Unipile apontando para esta URL."
        ),
    )


# ── Atualização de integrações ────────────────────────────────────────


@router.put("/me/integrations", response_model=TenantIntegrationResponse)
async def update_integrations(
    body: TenantIntegrationUpdate,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> TenantIntegrationResponse:
    """Atualiza as configurações de integração do tenant (parcial)."""
    result = await db.execute(
        select(TenantIntegration).where(TenantIntegration.tenant_id == tenant_id)
    )
    integration = result.scalar_one_or_none()

    if integration is None:
        # Cria a integration caso o tenant tenha sido criado previamente sem ela
        integration = TenantIntegration(tenant_id=tenant_id)
        db.add(integration)

    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(integration, field, value)

    system_llm_fields = {
        "llm_default_provider",
        "llm_default_model",
        "llm_default_temperature",
        "llm_default_max_tokens",
    }
    cold_email_llm_fields = {
        "cold_email_llm_provider",
        "cold_email_llm_model",
        "cold_email_llm_temperature",
        "cold_email_llm_max_tokens",
    }

    if system_llm_fields.intersection(updates):
        cadences_result = await db.execute(
            select(Cadence).where(
                Cadence.tenant_id == tenant_id,
                Cadence.cadence_type != "email_only",
            )
        )
        for cadence in cadences_result.scalars().all():
            cadence.llm_provider = integration.llm_default_provider
            cadence.llm_model = integration.llm_default_model
            cadence.llm_temperature = integration.llm_default_temperature
            cadence.llm_max_tokens = integration.llm_default_max_tokens

    if cold_email_llm_fields.intersection(updates):
        cadences_result = await db.execute(
            select(Cadence).where(
                Cadence.tenant_id == tenant_id,
                Cadence.cadence_type == "email_only",
            )
        )
        for cadence in cadences_result.scalars().all():
            cadence.llm_provider = integration.cold_email_llm_provider
            cadence.llm_model = integration.cold_email_llm_model
            cadence.llm_temperature = integration.cold_email_llm_temperature
            cadence.llm_max_tokens = integration.cold_email_llm_max_tokens

    await db.commit()
    await db.refresh(integration)

    logger.info(
        "tenant.integrations_updated", tenant_id=str(tenant_id), fields=list(updates.keys())
    )
    resp = TenantIntegrationResponse.model_validate(integration)
    resp.pipedrive_api_token_set = bool(integration.pipedrive_api_token)
    return resp


async def _probe_unipile_webhook_endpoint(url: str) -> int | None:
    """Faz um probe simples no endpoint público para validar se ele está acessível."""
    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            response = await client.post(
                url,
                content=b"{}",
                headers={"Content-Type": "application/json"},
            )
        return response.status_code
    except httpx.HTTPError as exc:
        logger.warning("tenant.unipile_webhook_probe_failed", url=url, error=str(exc))
        return None


def _build_unipile_webhook_url() -> str:
    return f"{settings.API_PUBLIC_URL.rstrip('/')}/webhooks/unipile"


def _get_unipile_webhook_registration_blockers(url: str) -> list[str]:
    blockers: list[str] = []
    if not settings.UNIPILE_API_KEY or not settings.UNIPILE_BASE_URL:
        blockers.append("Preencha UNIPILE_API_KEY e UNIPILE_BASE_URL no backend.")

    secret = (settings.UNIPILE_WEBHOOK_SECRET or "").strip()
    if not secret or secret == "...":
        blockers.append("Preencha UNIPILE_WEBHOOK_SECRET no ambiente.")

    if not _is_public_webhook_target(url):
        blockers.append(
            "API_PUBLIC_URL precisa ser uma URL HTTPS pública para registro automático."
        )

    return blockers


def _is_public_webhook_target(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except ValueError:
        return False

    if parsed.scheme != "https":
        return False

    hostname = parsed.hostname
    if not hostname:
        return False

    normalized = hostname.lower()
    if normalized in {"localhost"} or normalized.endswith(".local"):
        return False

    try:
        ip = ipaddress.ip_address(normalized)
    except ValueError:
        return "." in normalized

    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _coerce_webhook_value(webhook: dict[str, Any] | None, *keys: str) -> str | None:
    if not webhook:
        return None
    for key in keys:
        value = webhook.get(key)
        if value is not None:
            text = str(value).strip()
            if text:
                return text
    return None


def _coerce_webhook_bool(webhook: dict[str, Any] | None, key: str) -> bool | None:
    if not webhook or key not in webhook:
        return None
    value = webhook.get(key)
    if isinstance(value, bool):
        return value
    return None


def _coerce_webhook_events(webhook: dict[str, Any] | None) -> list[str]:
    if not webhook:
        return []
    events = webhook.get("events")
    if not isinstance(events, list):
        return []
    return [str(event) for event in events if str(event).strip()]
