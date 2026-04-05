"""
api/routes/tenants.py

Rotas REST para gerenciamento de tenants (onboarding + integrações).

Endpoints:
  POST   /tenants                   — onboarding: cria Tenant + TenantIntegration
  GET    /tenants/me                — dados do tenant autenticado
  PUT    /tenants/me/integrations   — atualiza TenantIntegration (parcial)
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from secrets import token_urlsafe
from typing import Any

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
from core.database import AsyncSessionLocal
from models.tenant import Tenant, TenantIntegration
from schemas.tenant import (
    TenantCreateRequest,
    TenantCreateResponse,
    TenantIntegrationResponse,
    TenantIntegrationUpdate,
    TenantResponse,
)
from services.content.theme_bank import seed_theme_bank_for_tenant

logger = structlog.get_logger()

router = APIRouter(prefix="/tenants", tags=["Tenants"])


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

    await db.commit()
    await db.refresh(integration)

    logger.info(
        "tenant.integrations_updated", tenant_id=str(tenant_id), fields=list(updates.keys())
    )
    resp = TenantIntegrationResponse.model_validate(integration)
    resp.pipedrive_api_token_set = bool(integration.pipedrive_api_token)
    return resp
