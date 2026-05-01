"""
api/routes/linkedin_accounts.py

Endpoints para gerenciamento de contas LinkedIn do tenant.

Rotas:
  GET    /linkedin-accounts               — lista contas do tenant
  POST   /linkedin-accounts/unipile       — conecta conta via Unipile
  POST   /linkedin-accounts/native        — conecta conta via cookie li_at
  GET    /linkedin-accounts/{id}          — detalhe de uma conta
  PATCH  /linkedin-accounts/{id}          — edita campos não-sensíveis
  DELETE /linkedin-accounts/{id}          — remove conta
  GET    /linkedin-accounts/{id}/status   — ping ao provider

Autenticação: user token ou tenant token (get_session_flexible).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_effective_tenant_id, get_session_flexible
from core.config import settings
from core.security import UserPayload, get_current_user_payload, get_optional_user_payload
from integrations.unipile_client import UnipileNonRetryableError, unipile_client
from models.linkedin_account import LinkedInAccount
from models.user import User
from schemas.linkedin_account import (
    LinkedInAccountHostedAuthRequest,
    LinkedInAccountHostedAuthResponse,
    LinkedInAccountListResponse,
    LinkedInAccountNativeCreateRequest,
    LinkedInAccountResponse,
    LinkedInAccountStatusResponse,
    LinkedInAccountUnipileCreateRequest,
    LinkedInAccountUpdateRequest,
)
from services.account_audit_log_service import record_account_audit_log
from services.linkedin_account_service import (
    build_hosted_linkedin_auth_state,
    decrypt_credential,
    encrypt_credential,
    ping_native_account,
)

router = APIRouter(prefix="/linkedin-accounts", tags=["LinkedIn Accounts"])
logger = structlog.get_logger()


# ── Listagem ──────────────────────────────────────────────────────────


@router.get("", response_model=LinkedInAccountListResponse)
async def list_linkedin_accounts(
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> LinkedInAccountListResponse:
    """Lista todas as contas LinkedIn do tenant."""
    result = await db.execute(
        select(LinkedInAccount)
        .where(LinkedInAccount.tenant_id == tenant_id)
        .order_by(LinkedInAccount.created_at)
    )
    accounts = result.scalars().all()
    return LinkedInAccountListResponse(
        accounts=[await _build_linkedin_account_response(db, a) for a in accounts],
        total=len(accounts),
    )


# ── Conectar via Unipile ──────────────────────────────────────────────


@router.post("/unipile/hosted-auth", response_model=LinkedInAccountHostedAuthResponse)
async def create_unipile_hosted_auth_link(
    body: LinkedInAccountHostedAuthRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    user: UserPayload = Depends(get_current_user_payload),
) -> LinkedInAccountHostedAuthResponse:
    """Gera um link Hosted Auth da Unipile limitado ao provider LinkedIn."""
    if not settings.UNIPILE_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="UNIPILE_API_KEY não configurada.",
        )

    state = build_hosted_linkedin_auth_state(
        tenant_id=tenant_id,
        user_id=user.user_id,
        display_name=body.display_name,
        linkedin_username=body.linkedin_username,
        supports_inmail=body.supports_inmail,
    )
    frontend_url = settings.FRONTEND_URL.rstrip("/")
    api_url = settings.API_PUBLIC_URL.rstrip("/")

    try:
        hosted_link = await unipile_client.create_hosted_auth_link(
            auth_type="create",
            providers=["LINKEDIN"],
            expires_on=(datetime.now(UTC) + timedelta(minutes=30))
            .isoformat()
            .replace("+00:00", "Z"),
            success_redirect_url=f"{frontend_url}/configuracoes/linkedin-accounts?unipile=success",
            failure_redirect_url=f"{frontend_url}/configuracoes/linkedin-accounts?unipile=error",
            notify_url=f"{api_url}/webhooks/unipile/hosted-auth",
            name=state,
        )
    except UnipileNonRetryableError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error(
            "linkedin_account.hosted_auth.failed", error=str(exc), tenant_id=str(tenant_id)
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Falha ao gerar link Hosted Auth da Unipile.",
        ) from exc

    logger.info(
        "linkedin_account.hosted_auth.created",
        tenant_id=str(tenant_id),
        user_id=str(user.user_id),
    )
    return LinkedInAccountHostedAuthResponse(auth_url=hosted_link.url)


@router.post(
    "/{account_id}/unipile/reconnect-link", response_model=LinkedInAccountHostedAuthResponse
)
async def create_unipile_reconnect_link(
    account_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    user: UserPayload = Depends(get_current_user_payload),
    db: AsyncSession = Depends(get_session_flexible),
) -> LinkedInAccountHostedAuthResponse:
    """Gera um link Hosted Auth da Unipile para reconectar uma conta LinkedIn."""
    if not settings.UNIPILE_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="UNIPILE_API_KEY não configurada.",
        )

    account = await _get_or_404(account_id, tenant_id, db)
    if account.provider_type != "unipile" or not account.unipile_account_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Somente contas LinkedIn Unipile podem ser reconectadas por Hosted Auth.",
        )

    state = build_hosted_linkedin_auth_state(
        tenant_id=tenant_id,
        user_id=user.user_id,
        display_name=account.display_name,
        linkedin_username=account.linkedin_username,
        supports_inmail=account.supports_inmail,
    )
    frontend_url = settings.FRONTEND_URL.rstrip("/")
    api_url = settings.API_PUBLIC_URL.rstrip("/")

    try:
        hosted_link = await unipile_client.create_hosted_auth_link(
            auth_type="reconnect",
            providers=["LINKEDIN"],
            expires_on=(datetime.now(UTC) + timedelta(minutes=30))
            .isoformat()
            .replace("+00:00", "Z"),
            success_redirect_url=f"{frontend_url}/configuracoes/linkedin-accounts?unipile=reconnected",
            failure_redirect_url=f"{frontend_url}/configuracoes/linkedin-accounts?unipile=error",
            notify_url=f"{api_url}/webhooks/unipile/hosted-auth",
            name=state,
            reconnect_account=account.unipile_account_id,
        )
    except UnipileNonRetryableError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error(
            "linkedin_account.reconnect_link.failed",
            error=str(exc),
            tenant_id=str(tenant_id),
            account_id=str(account.id),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Falha ao gerar link de reconexão da Unipile.",
        ) from exc

    logger.info(
        "linkedin_account.reconnect_link.created",
        tenant_id=str(tenant_id),
        user_id=str(user.user_id),
        account_id=str(account.id),
    )
    await record_account_audit_log(
        db,
        tenant_id=tenant_id,
        account_type="linkedin",
        account_id=account.id,
        external_account_id=account.unipile_account_id,
        provider_type=account.provider_type,
        event_type="reconnect_link_created",
        actor_user_id=user.user_id,
        provider_status=account.provider_status,
        message="Link de reconexão Hosted Auth gerado.",
    )
    return LinkedInAccountHostedAuthResponse(auth_url=hosted_link.url)


@router.post(
    "/unipile",
    response_model=LinkedInAccountResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_unipile_account(
    body: LinkedInAccountUnipileCreateRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    user: UserPayload | None = Depends(get_optional_user_payload),
    db: AsyncSession = Depends(get_session_flexible),
) -> LinkedInAccountResponse:
    """Conecta uma conta LinkedIn via Unipile (account_id já existe no Unipile)."""
    account = LinkedInAccount(
        tenant_id=tenant_id,
        display_name=body.display_name,
        linkedin_username=body.linkedin_username,
        owner_user_id=user.user_id if user else None,
        created_by_user_id=user.user_id if user else None,
        provider_type="unipile",
        unipile_account_id=body.unipile_account_id,
        supports_inmail=body.supports_inmail,
        provider_status="connected",
        connected_at=datetime.now(UTC),
    )
    db.add(account)
    await db.flush()
    await record_account_audit_log(
        db,
        tenant_id=tenant_id,
        account_type="linkedin",
        account_id=account.id,
        external_account_id=account.unipile_account_id,
        provider_type=account.provider_type,
        event_type="connected",
        actor_user_id=user.user_id if user else None,
        provider_status=account.provider_status,
        message="Conta LinkedIn Unipile conectada.",
    )
    logger.info(
        "linkedin_account.created",
        provider="unipile",
        account_id=str(account.id),
        tenant_id=str(tenant_id),
    )
    return await _build_linkedin_account_response(db, account)


# ── Conectar via cookie li_at (provider nativo) ───────────────────────


@router.post(
    "/native",
    response_model=LinkedInAccountResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_native_account(
    body: LinkedInAccountNativeCreateRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    user: UserPayload | None = Depends(get_optional_user_payload),
    db: AsyncSession = Depends(get_session_flexible),
) -> LinkedInAccountResponse:
    """
    Conecta uma conta LinkedIn via cookie li_at.
    O cookie é armazenado criptografado com Fernet.
    A validade real será confirmada pelo primeiro ping ou sync
    (LinkedIn bloqueia validação a partir de IPs de servidor).
    """
    if len(body.li_at_cookie.strip()) < 50:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cookie li_at parece inválido (muito curto). Copie o valor completo.",
        )

    encrypted_li_at = encrypt_credential(body.li_at_cookie)

    account = LinkedInAccount(
        tenant_id=tenant_id,
        display_name=body.display_name,
        linkedin_username=body.linkedin_username,
        owner_user_id=user.user_id if user else None,
        created_by_user_id=user.user_id if user else None,
        provider_type="native",
        li_at_cookie=encrypted_li_at,
        supports_inmail=body.supports_inmail,
        provider_status="connected",
        connected_at=datetime.now(UTC),
    )
    db.add(account)
    await db.flush()
    await record_account_audit_log(
        db,
        tenant_id=tenant_id,
        account_type="linkedin",
        account_id=account.id,
        provider_type=account.provider_type,
        event_type="connected",
        actor_user_id=user.user_id if user else None,
        provider_status=account.provider_status,
        message="Conta LinkedIn nativa conectada.",
    )
    logger.info(
        "linkedin_account.created",
        provider="native",
        account_id=str(account.id),
        tenant_id=str(tenant_id),
    )
    return await _build_linkedin_account_response(db, account)


# ── Detalhe ───────────────────────────────────────────────────────────


@router.get("/{account_id}", response_model=LinkedInAccountResponse)
async def get_linkedin_account(
    account_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> LinkedInAccountResponse:
    account = await _get_or_404(account_id, tenant_id, db)
    return await _build_linkedin_account_response(db, account)


# ── Editar ────────────────────────────────────────────────────────────


@router.patch("/{account_id}", response_model=LinkedInAccountResponse)
async def update_linkedin_account(
    account_id: uuid.UUID,
    body: LinkedInAccountUpdateRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> LinkedInAccountResponse:
    account = await _get_or_404(account_id, tenant_id, db)

    updates = body.model_dump(exclude_none=True)
    for field, value in updates.items():
        setattr(account, field, value)

    await db.flush()
    return await _build_linkedin_account_response(db, account)


# ── Remover ───────────────────────────────────────────────────────────


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_linkedin_account(
    account_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    user: UserPayload | None = Depends(get_optional_user_payload),
    db: AsyncSession = Depends(get_session_flexible),
) -> None:
    account = await _get_or_404(account_id, tenant_id, db)
    await record_account_audit_log(
        db,
        tenant_id=tenant_id,
        account_type="linkedin",
        account_id=account.id,
        external_account_id=account.unipile_account_id,
        provider_type=account.provider_type,
        event_type="deleted",
        actor_user_id=user.user_id if user else None,
        provider_status=account.provider_status,
        message="Conta LinkedIn removida.",
    )
    await db.delete(account)
    logger.info(
        "linkedin_account.deleted",
        account_id=str(account_id),
        tenant_id=str(tenant_id),
    )


# ── Status (ping) ─────────────────────────────────────────────────────


@router.get("/{account_id}/status", response_model=LinkedInAccountStatusResponse)
async def get_account_status(
    account_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    user: UserPayload | None = Depends(get_optional_user_payload),
    db: AsyncSession = Depends(get_session_flexible),
) -> LinkedInAccountStatusResponse:
    """
    Faz um ping no provider para verificar se a conta está funcionando.
    Para contas nativas, decripta o cookie e chama a Voyager API.
    Para contas Unipile, delega ao UnipileLinkedInProvider.ping().
    """
    account = await _get_or_404(account_id, tenant_id, db)

    ping_ok = False
    error: str | None = None

    try:
        if account.provider_type == "native":
            if not account.li_at_cookie:
                error = "Cookie li_at não configurado."
            else:
                li_at = decrypt_credential(account.li_at_cookie)
                ping_ok, error = await ping_native_account(li_at)
        else:
            from core.config import settings as _settings  # noqa: PLC0415
            from integrations.linkedin import LinkedInRegistry  # noqa: PLC0415

            registry = LinkedInRegistry(settings=_settings)
            ping_ok = await registry.ping(account)
            error = None
    except Exception as exc:
        ping_ok = False
        error = str(exc)

    account.last_health_check_at = datetime.now(UTC)
    account.health_error = error
    account.provider_status = "ok" if ping_ok else "error"
    await record_account_audit_log(
        db,
        tenant_id=tenant_id,
        account_type="linkedin",
        account_id=account.id,
        external_account_id=account.unipile_account_id,
        provider_type=account.provider_type,
        event_type="health_check_ok" if ping_ok else "health_check_failed",
        actor_user_id=user.user_id if user else None,
        provider_status=account.provider_status,
        message=error,
    )

    return LinkedInAccountStatusResponse(
        account_id=account.id,
        is_active=account.is_active,
        provider_type=account.provider_type,
        ping_ok=ping_ok,
        error=error,
    )


# ── Helper ────────────────────────────────────────────────────────────


async def _get_or_404(
    account_id: uuid.UUID,
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> LinkedInAccount:
    result = await db.execute(
        select(LinkedInAccount).where(
            LinkedInAccount.id == account_id,
            LinkedInAccount.tenant_id == tenant_id,
        )
    )
    account = result.scalar_one_or_none()
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conta LinkedIn não encontrada.",
        )
    return account


async def _build_linkedin_account_response(
    db: AsyncSession,
    account: LinkedInAccount,
) -> LinkedInAccountResponse:
    owner_email: str | None = None
    owner_name: str | None = None
    if account.owner_user_id:
        owner_result = await db.execute(
            select(User.email, User.name).where(User.id == account.owner_user_id)
        )
        owner = owner_result.one_or_none()
        if owner is not None:
            owner_email = owner.email
            owner_name = owner.name

    return LinkedInAccountResponse(
        id=account.id,
        tenant_id=account.tenant_id,
        display_name=account.display_name,
        linkedin_username=account.linkedin_username,
        owner_user_id=account.owner_user_id,
        owner_email=owner_email,
        owner_name=owner_name,
        created_by_user_id=account.created_by_user_id,
        provider_type=account.provider_type,
        unipile_account_id=account.unipile_account_id,
        is_active=account.is_active,
        supports_inmail=account.supports_inmail,
        provider_status=account.provider_status,
        last_status_at=account.last_status_at,
        last_health_check_at=account.last_health_check_at,
        health_error=account.health_error,
        connected_at=account.connected_at,
        disconnected_at=account.disconnected_at,
        reconnect_required_at=account.reconnect_required_at,
        last_polled_at=account.last_polled_at,
        created_at=account.created_at,
        updated_at=account.updated_at,
    )
