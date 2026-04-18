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

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_effective_tenant_id, get_session_flexible
from models.linkedin_account import LinkedInAccount
from schemas.linkedin_account import (
    LinkedInAccountListResponse,
    LinkedInAccountNativeCreateRequest,
    LinkedInAccountResponse,
    LinkedInAccountStatusResponse,
    LinkedInAccountUnipileCreateRequest,
    LinkedInAccountUpdateRequest,
)
from services.linkedin_account_service import (
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
        accounts=[LinkedInAccountResponse.model_validate(a) for a in accounts],
        total=len(accounts),
    )


# ── Conectar via Unipile ──────────────────────────────────────────────


@router.post(
    "/unipile",
    response_model=LinkedInAccountResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_unipile_account(
    body: LinkedInAccountUnipileCreateRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> LinkedInAccountResponse:
    """Conecta uma conta LinkedIn via Unipile (account_id já existe no Unipile)."""
    account = LinkedInAccount(
        tenant_id=tenant_id,
        display_name=body.display_name,
        linkedin_username=body.linkedin_username,
        provider_type="unipile",
        unipile_account_id=body.unipile_account_id,
        supports_inmail=body.supports_inmail,
    )
    db.add(account)
    await db.flush()
    logger.info(
        "linkedin_account.created",
        provider="unipile",
        account_id=str(account.id),
        tenant_id=str(tenant_id),
    )
    return LinkedInAccountResponse.model_validate(account)


# ── Conectar via cookie li_at (provider nativo) ───────────────────────


@router.post(
    "/native",
    response_model=LinkedInAccountResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_native_account(
    body: LinkedInAccountNativeCreateRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
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
        provider_type="native",
        li_at_cookie=encrypted_li_at,
        supports_inmail=body.supports_inmail,
    )
    db.add(account)
    await db.flush()
    logger.info(
        "linkedin_account.created",
        provider="native",
        account_id=str(account.id),
        tenant_id=str(tenant_id),
    )
    return LinkedInAccountResponse.model_validate(account)


# ── Detalhe ───────────────────────────────────────────────────────────


@router.get("/{account_id}", response_model=LinkedInAccountResponse)
async def get_linkedin_account(
    account_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> LinkedInAccountResponse:
    account = await _get_or_404(account_id, tenant_id, db)
    return LinkedInAccountResponse.model_validate(account)


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
    return LinkedInAccountResponse.model_validate(account)


# ── Remover ───────────────────────────────────────────────────────────


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_linkedin_account(
    account_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> None:
    account = await _get_or_404(account_id, tenant_id, db)
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
