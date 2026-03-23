"""
api/dependencies.py

Dependências FastAPI centralizadas para injeção via Depends().

Responsabilidades:
  - get_session: sessão async com tenant injetado via RLS
  - get_current_tenant_id: extrai UUID do JWT
  - get_current_tenant: busca o Tenant no banco (404 se não existir)
  - get_llm_registry: singleton LLMRegistry via lru_cache
  - get_redis: acesso ao redis_client global

Uso:
    @router.get("/leads")
    async def list_leads(
        db: AsyncSession = Depends(get_session),
        tenant: Tenant = Depends(get_current_tenant),
    ):
        ...
"""

from __future__ import annotations

import uuid
from functools import lru_cache
from typing import AsyncGenerator

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_session as _get_session
from core.redis_client import RedisClient, redis_client
from core.security import get_current_tenant_id as _get_current_tenant_id
from integrations.llm.registry import LLMRegistry
from models.tenant import Tenant


# ── Session com tenant injetado ───────────────────────────────────────

async def get_session(
    tenant_id: uuid.UUID = Depends(_get_current_tenant_id),
) -> AsyncGenerator[AsyncSession, None]:
    """
    Abre uma AsyncSession com o tenant_id injetado via SET LOCAL (RLS).
    Commit automático no final, rollback em caso de exceção.
    """
    async for session in _get_session(tenant_id):
        yield session


# ── Tenant atual ──────────────────────────────────────────────────────

def get_current_tenant_id(
    tenant_id: uuid.UUID = Depends(_get_current_tenant_id),
) -> uuid.UUID:
    """Re-exporta get_current_tenant_id para uso nos routers."""
    return tenant_id


async def get_current_tenant(
    tenant_id: uuid.UUID = Depends(_get_current_tenant_id),
    db: AsyncSession = Depends(get_session),
) -> Tenant:
    """
    Busca o Tenant ativo pelo tenant_id extraído do JWT.
    Levanta HTTP 404 se o tenant não existir ou estiver inativo.
    """
    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id, Tenant.is_active.is_(True))
    )
    tenant = result.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant não encontrado ou inativo.",
        )
    return tenant


# ── LLM Registry ──────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _build_llm_registry() -> LLMRegistry:
    """Constrói o LLMRegistry uma única vez (singleton via lru_cache)."""
    from core.config import settings
    return LLMRegistry(settings=settings, redis=redis_client)


def get_llm_registry() -> LLMRegistry:
    """Dependência FastAPI que retorna o singleton LLMRegistry."""
    return _build_llm_registry()


# ── Redis ─────────────────────────────────────────────────────────────

def get_redis() -> RedisClient:
    """Retorna o redis_client global."""
    return redis_client
