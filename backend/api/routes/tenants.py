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
from dataclasses import dataclass
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
    UnipileRegisteredWebhookResponse,
    UnipileWebhookRegistrationItem,
    UnipileWebhookRegistrationResponse,
    UnipileWebhookSourceStatus,
    UnipileWebhookStatusResponse,
)
from services.content.theme_bank import seed_theme_bank_for_tenant

logger = structlog.get_logger()

router = APIRouter(prefix="/tenants", tags=["Tenants"])


@dataclass(frozen=True)
class UnipileWebhookSourceConfig:
    source: str
    label: str
    events: tuple[str, ...]
    request_events: tuple[str, ...] | None = None


_UNIPILE_WEBHOOK_DOCS_URL = "https://developer.unipile.com/docs/webhooks-2"
_UNIPILE_WEBHOOK_DASHBOARD_URL = "https://dashboard.unipile.com"
_UNIPILE_WEBHOOK_SOURCES: tuple[UnipileWebhookSourceConfig, ...] = (
    UnipileWebhookSourceConfig(
        source="messaging",
        label="Mensagens LinkedIn",
        events=("message_received",),
        request_events=("message_received",),
    ),
    UnipileWebhookSourceConfig(
        source="users",
        label="Novas conexões LinkedIn",
        events=("new_relation",),
    ),
    UnipileWebhookSourceConfig(
        source="email",
        label="Emails inbound",
        events=("mail_received",),
        request_events=("mail_received",),
    ),
)

_UNIPILE_SOURCE_ALIASES: dict[str, tuple[str, ...]] = {
    "messaging": ("messaging",),
    "users": ("users",),
    "email": ("email", "mailing"),
}


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
    linkedin_account_configured = bool(
        (integration and integration.unipile_linkedin_account_id)
        or settings.UNIPILE_ACCOUNT_ID_LINKEDIN
    )
    gmail_account_configured = bool(
        (integration and integration.unipile_gmail_account_id) or settings.UNIPILE_ACCOUNT_ID_GMAIL
    )
    expected_source_keys = _get_expected_unipile_sources(
        linkedin_account_configured=linkedin_account_configured,
        gmail_account_configured=gmail_account_configured,
    )
    api_registration_blockers = _get_unipile_webhook_registration_blockers(
        url=url,
        expected_source_keys=expected_source_keys,
    )
    registered_webhooks: list[dict[str, Any]] = []
    registration_lookup_error: str | None = None
    if api_registration_supported:
        try:
            registered_webhooks = await unipile_client.get_webhooks_by_url(url)
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
    expected_sources = _build_unipile_source_statuses(
        expected_source_keys=expected_source_keys,
        registered_webhooks=registered_webhooks,
    )

    return UnipileWebhookStatusResponse(
        url=url,
        docs_url=_UNIPILE_WEBHOOK_DOCS_URL,
        dashboard_url=_UNIPILE_WEBHOOK_DASHBOARD_URL,
        expected_events=[
            event_name for item in expected_sources for event_name in item.expected_events
        ],
        expected_sources=expected_sources,
        secret_configured=secret_configured,
        public_endpoint_healthy=endpoint_healthy,
        public_endpoint_status_code=status_code,
        linkedin_account_configured=linkedin_account_configured,
        gmail_account_configured=gmail_account_configured,
        api_registration_supported=api_registration_supported,
        api_registration_ready=not api_registration_blockers,
        api_registration_blockers=api_registration_blockers,
        registered_in_unipile=bool(registered_webhooks),
        registered_webhooks=[
            UnipileRegisteredWebhookResponse(
                webhook_id=_coerce_webhook_value(webhook, "id", "webhook_id"),
                source=_coerce_webhook_value(webhook, "source"),
                enabled=_coerce_webhook_bool(webhook, "enabled"),
                events=_coerce_webhook_events(webhook),
            )
            for webhook in registered_webhooks
        ],
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
    db: AsyncSession = Depends(get_session_flexible),
) -> UnipileWebhookRegistrationResponse:
    """Registra o webhook da Unipile via API para o tenant atual."""
    db_result = await db.execute(
        select(TenantIntegration).where(TenantIntegration.tenant_id == tenant_id)
    )
    integration = db_result.scalar_one_or_none()

    url = _build_unipile_webhook_url()
    expected_source_keys = _get_expected_unipile_sources(
        linkedin_account_configured=bool(
            (integration and integration.unipile_linkedin_account_id)
            or settings.UNIPILE_ACCOUNT_ID_LINKEDIN
        ),
        gmail_account_configured=bool(
            (integration and integration.unipile_gmail_account_id)
            or settings.UNIPILE_ACCOUNT_ID_GMAIL
        ),
    )
    blockers = _get_unipile_webhook_registration_blockers(
        url=url,
        expected_source_keys=expected_source_keys,
    )
    if blockers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=" ".join(blockers),
        )

    secret = (settings.UNIPILE_WEBHOOK_SECRET or "").strip()
    registration_items: list[UnipileWebhookRegistrationItem] = []

    try:
        for source in expected_source_keys:
            config = _get_unipile_source_config(source)
            registration_result: dict[str, Any] = await unipile_client.ensure_webhook(
                request_url=url,
                secret=secret,
                source=source,
                events=list(config.request_events) if config.request_events else None,
                name=f"prospector-{source}-webhook",
            )
            webhook_id_raw = registration_result.get("webhook_id")
            registration_items.append(
                UnipileWebhookRegistrationItem(
                    source=source,
                    events=list(config.events),
                    created=bool(registration_result.get("created")),
                    already_exists=bool(registration_result.get("already_exists")),
                    webhook_id=str(webhook_id_raw) if webhook_id_raw else None,
                )
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

    created = any(item.created for item in registration_items)
    already_exists = all(item.already_exists for item in registration_items)

    logger.info(
        "tenant.unipile_webhook_registered",
        tenant_id=str(tenant_id),
        created=created,
        already_exists=already_exists,
        source_count=len(registration_items),
        request_url=url,
    )

    return UnipileWebhookRegistrationResponse(
        created=created,
        already_exists=already_exists,
        request_url=url,
        auth_header="Unipile-Auth",
        webhooks=registration_items,
        message=(
            "Webhooks registrados com sucesso na Unipile."
            if created and not already_exists
            else "Os webhooks esperados já existem na Unipile para esta URL."
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


def _get_expected_unipile_sources(
    *,
    linkedin_account_configured: bool,
    gmail_account_configured: bool,
) -> list[str]:
    expected: list[str] = []

    if linkedin_account_configured or not (linkedin_account_configured or gmail_account_configured):
        expected.extend(["messaging", "users"])
    if gmail_account_configured or not (linkedin_account_configured or gmail_account_configured):
        expected.append("email")

    return expected


def _get_unipile_webhook_registration_blockers(
    url: str, expected_source_keys: list[str]
) -> list[str]:
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

    if not expected_source_keys:
        blockers.append(
            "Configure ao menos uma conta LinkedIn ou Gmail antes de registrar o webhook."
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


def _build_unipile_source_statuses(
    *,
    expected_source_keys: list[str],
    registered_webhooks: list[dict[str, Any]],
) -> list[UnipileWebhookSourceStatus]:
    statuses: list[UnipileWebhookSourceStatus] = []
    for source in expected_source_keys:
        config = _get_unipile_source_config(source)
        webhook = _select_webhook_for_source(registered_webhooks, source)
        registered_events = _coerce_webhook_events(webhook)
        expected_events = list(config.events)
        statuses.append(
            UnipileWebhookSourceStatus(
                source=source,
                label=config.label,
                expected_events=expected_events,
                registered=webhook is not None,
                webhook_id=_coerce_webhook_value(webhook, "id", "webhook_id"),
                enabled=_coerce_webhook_bool(webhook, "enabled"),
                registered_events=registered_events,
                missing_events=[
                    event_name
                    for event_name in expected_events
                    if event_name not in registered_events
                ],
                extra_events=[
                    event_name
                    for event_name in registered_events
                    if event_name not in expected_events
                ],
            )
        )
    return statuses


def _select_webhook_for_source(
    registered_webhooks: list[dict[str, Any]],
    source: str,
) -> dict[str, Any] | None:
    accepted_sources = _UNIPILE_SOURCE_ALIASES.get(source, (source,))
    source_matches = [
        webhook for webhook in registered_webhooks if webhook.get("source") in accepted_sources
    ]
    for webhook in source_matches:
        if webhook.get("enabled") is not False:
            return webhook
    return source_matches[0] if source_matches else None


def _get_unipile_source_config(source: str) -> UnipileWebhookSourceConfig:
    for config in _UNIPILE_WEBHOOK_SOURCES:
        if config.source == source:
            return config
    raise KeyError(f"Unknown Unipile webhook source: {source}")
