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
from collections.abc import AsyncGenerator
from functools import lru_cache

import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import AsyncSessionLocal
from core.database import get_session as _get_session
from core.redis_client import RedisClient, redis_client
from core.security import (
    UserPayload,
    decode_token,
    get_current_user_payload,
)
from core.security import (
    get_current_tenant_id as _get_current_tenant_id,
)
from integrations.llm.registry import LLMRegistry
from integrations.tts.registry import TTSRegistry
from models.tenant import Tenant
from models.tenant_user import TenantUser
from models.user import User
from services.tenant_access import get_active_membership, resolve_user_login_context

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


async def _require_active_tenant_id(tenant_id: uuid.UUID) -> uuid.UUID:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Tenant.id).where(
                Tenant.id == tenant_id,
                Tenant.is_active.is_(True),
            )
        )
        active_tenant_id = result.scalar_one_or_none()

    if active_tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant não encontrado ou inativo.",
        )

    return tenant_id


# ── Session com tenant injetado ───────────────────────────────────────


async def get_session(
    tenant_id: uuid.UUID = Depends(_get_current_tenant_id),
) -> AsyncGenerator[AsyncSession, None]:
    """
    Abre uma AsyncSession com o tenant_id injetado via SET LOCAL (RLS).
    Commit automático no final, rollback em caso de exceção.
    """
    active_tenant_id = await _require_active_tenant_id(tenant_id)
    async for session in _get_session(active_tenant_id):
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
        return await _require_active_tenant_id(uuid.UUID(tenant_id_str))

    # Token de usuário → valida membership/tentant explícito
    user_id_str: str | None = payload.get("user_id")
    if user_id_str is None:
        raise credentials_exception

    async with AsyncSessionLocal() as session:
        user_result = await session.execute(
            select(User).where(
                User.id == uuid.UUID(user_id_str),
                User.is_active.is_(True),
            )
        )
        user = user_result.scalar_one_or_none()

        if user is None:
            raise credentials_exception

        token_tenant_id = payload.get("tenant_id")
        tenant_id = uuid.UUID(token_tenant_id) if token_tenant_id else None
        if tenant_id is None:
            tenant_id, _tenant_role = await resolve_user_login_context(session, user)

        if tenant_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuário sem acesso a tenant ativo.",
            )

        await _require_active_tenant_id(tenant_id)

        if not user.is_superuser:
            membership = await get_active_membership(session, user_id=user.id, tenant_id=tenant_id)
            if membership is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Usuário não possui acesso a este tenant.",
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


async def get_current_active_user(
    user: UserPayload = Depends(get_current_user_payload),
) -> User:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.id == user.user_id, User.is_active.is_(True))
        )
        db_user = result.scalar_one_or_none()
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado ou inativo.",
        )
    return db_user


async def get_current_tenant_membership(
    user: UserPayload = Depends(get_current_user_payload),
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
) -> TenantUser | None:
    if user.is_superuser:
        return None

    async with AsyncSessionLocal() as session:
        membership = await get_active_membership(session, user_id=user.user_id, tenant_id=tenant_id)

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário não possui acesso a este tenant.",
        )
    return membership


async def require_tenant_admin(
    user: UserPayload = Depends(get_current_user_payload),
    membership: TenantUser | None = Depends(get_current_tenant_membership),
) -> UserPayload:
    if user.is_superuser:
        return user
    if membership is None or membership.role.value != "tenant_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a admins do tenant.",
        )
    return user


# ── LLM Registry ──────────────────────────────────────────────────────


@lru_cache(maxsize=1)
def _build_llm_registry() -> LLMRegistry:
    """Constrói o LLMRegistry uma única vez (singleton via lru_cache)."""

    return LLMRegistry(settings=settings, redis=redis_client)


def get_llm_registry() -> LLMRegistry:
    """Dependência FastAPI que retorna o singleton LLMRegistry."""
    return _build_llm_registry()


# ── TTS Registry ──────────────────────────────────────────────────────


@lru_cache(maxsize=1)
def _build_tts_registry() -> TTSRegistry:
    """Constrói o TTSRegistry uma única vez (singleton via lru_cache)."""

    return TTSRegistry(settings=settings, redis=redis_client)


def get_tts_registry() -> TTSRegistry:
    """Dependência FastAPI que retorna o singleton TTSRegistry."""
    return _build_tts_registry()


# ── Redis ─────────────────────────────────────────────────────────────


def get_redis() -> RedisClient:
    """Retorna o redis_client global."""
    return redis_client
