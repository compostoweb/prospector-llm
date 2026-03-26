"""
api/dependencies.py

Dependências FastAPI centralizadas para injeção via Depends().

Responsabilidades:
  - get_session: sessão async com tenant injetado via RLS
  - get_current_tenant_id: extrai UUID do JWT (apenas tenant tokens)
  - get_effective_tenant_id: resolve tenant_id para ambos token types (tenant + user)
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

import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import AsyncSessionLocal, get_session as _get_session
from core.redis_client import RedisClient, redis_client
from core.security import (
    decode_token,
    get_current_tenant_id as _get_current_tenant_id,
)
from integrations.llm.registry import LLMRegistry
from integrations.tts.registry import TTSRegistry
from models.tenant import Tenant

logger = structlog.get_logger()

_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


# ── Session sem autenticação (webhooks externos) ─────────────────────

async def get_session_no_auth() -> AsyncGenerator[AsyncSession, None]:
    """
    Abre uma AsyncSession SEM injeção de tenant (sem RLS).
    Usar APENAS em webhooks externos que autenticam via HMAC/signature.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


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


async def get_effective_tenant_id(
    token: str = Depends(_oauth2_scheme),
) -> uuid.UUID:
    """
    Resolve tenant_id a partir de QUALQUER tipo de token:
      - Tenant token  → usa tenant_id do JWT diretamente.
      - User token    → busca o primeiro tenant ativo no banco (MVP single-tenant).

    Usar em rotas que precisam ser acessíveis tanto pelo painel admin (user)
    quanto por API keys (tenant).
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido ou expirado.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
    except (JWTError, ValueError):
        raise credentials_exception

    # Token de tenant → retorna tenant_id direto
    if payload.get("type") != "user":
        tenant_id_str: str | None = payload.get("tenant_id")
        if tenant_id_str is None:
            raise credentials_exception
        return uuid.UUID(tenant_id_str)

    # Token de usuário → busca o primeiro tenant ativo (MVP)
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Tenant.id).where(Tenant.is_active.is_(True)).limit(1)
        )
        tenant_id = result.scalar_one_or_none()

    if tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhum tenant ativo encontrado.",
        )
    logger.debug("auth.user_tenant_resolved", tenant_id=str(tenant_id))
    return tenant_id


async def get_session_flexible(
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
) -> AsyncGenerator[AsyncSession, None]:
    """
    Session com tenant injetado via RLS — aceita tanto tenant tokens
    quanto user tokens (resolve tenant via get_effective_tenant_id).
    """
    async for session in _get_session(tenant_id):
        yield session


async def get_current_tenant(
    tenant_id: uuid.UUID = Depends(_get_current_tenant_id),
    db: AsyncSession = Depends(get_session),
) -> Tenant:
    """
    Busca o Tenant ativo pelo tenant_id extraído do JWT.
    Levanta HTTP 404 se o tenant não existir ou estiver inativo.
    Aceita APENAS tenant tokens (api_key).
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


async def get_current_tenant_flexible(
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> Tenant:
    """
    Busca o Tenant ativo — aceita tanto tenant tokens quanto user tokens.
    Usa get_effective_tenant_id para resolver o tenant_id.
    """
    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(Tenant)
        .where(Tenant.id == tenant_id, Tenant.is_active.is_(True))
        .options(selectinload(Tenant.integration))
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


# ── TTS Registry ──────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _build_tts_registry() -> TTSRegistry:
    """Constrói o TTSRegistry uma única vez (singleton via lru_cache)."""
    from core.config import settings
    return TTSRegistry(settings=settings, redis=redis_client)


def get_tts_registry() -> TTSRegistry:
    """Dependência FastAPI que retorna o singleton TTSRegistry."""
    return _build_tts_registry()


# ── Redis ─────────────────────────────────────────────────────────────

def get_redis() -> RedisClient:
    """Retorna o redis_client global."""
    return redis_client
