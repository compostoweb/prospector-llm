"""
core/security.py

Autenticação via JWT + extração de tenant_id e user_id.

Responsabilidades:
  - Criar e decodificar tokens JWT (HS256 via python-jose)
  - Prover get_current_tenant_id() — dependência para rotas de tenant (API key)
  - Prover get_current_user_payload() — dependência para rotas de usuário (Google OAuth)
  - Levantar HTTPException 401 em token inválido, expirado ou payload incorreto

Dois tipos de JWT:
  - Tenant  → {"tenant_id": "...", "exp": ...}
  - Usuário → {"type": "user", "user_id": "...", "email": "...", "is_superuser": bool, "exp": ...}

Uso:
    tenant_id: UUID = Depends(get_current_tenant_id)
    user: UserPayload = Depends(get_current_user_payload)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from core.config import settings

ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


# ── Criação de tokens ─────────────────────────────────────────────────

def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """
    Gera um JWT assinado com HS256.
    O campo 'tenant_id' deve estar presente em data para tokens de tenant.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_user_token(
    user_id: uuid.UUID,
    email: str,
    is_superuser: bool,
    name: str | None = None,
) -> str:
    """
    Gera um JWT para usuário humano autenticado via Google OAuth.
    O campo 'type' = 'user' distingue do token de tenant.
    """
    return create_access_token({
        "type": "user",
        "user_id": str(user_id),
        "email": email,
        "is_superuser": is_superuser,
        "name": name,
    })


def decode_token(token: str) -> dict[str, Any]:
    """
    Decodifica e valida o JWT.
    Levanta JWTError (jose) se inválido ou expirado.
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])


# ── Dependências FastAPI ──────────────────────────────────────────────

def get_current_tenant_id(
    token: str = Depends(oauth2_scheme),
) -> uuid.UUID:
    """
    Dependência para rotas de tenant.
    Extrai o tenant_id de um JWT de API key.
    Rejeita tokens de usuário humano (type='user').
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido ou expirado.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        # Tokens de usuário humano não autorizam acesso de tenant
        if payload.get("type") == "user":
            raise credentials_exception
        tenant_id_str: str | None = payload.get("tenant_id")
        if tenant_id_str is None:
            raise credentials_exception
        return uuid.UUID(tenant_id_str)
    except (JWTError, ValueError):
        raise credentials_exception


@dataclass
class UserPayload:
    """Payload extraído de um JWT de usuário humano (Google OAuth)."""

    user_id: uuid.UUID
    email: str
    is_superuser: bool
    name: str | None


def get_current_user_payload(
    token: str = Depends(oauth2_scheme),
) -> UserPayload:
    """
    Dependência para rotas de usuário humano (painel admin).
    Rejeita tokens de tenant (sem type='user').
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token de usuário inválido ou expirado.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        if payload.get("type") != "user":
            raise credentials_exception
        user_id_str: str | None = payload.get("user_id")
        email: str | None = payload.get("email")
        if not user_id_str or not email:
            raise credentials_exception
        return UserPayload(
            user_id=uuid.UUID(user_id_str),
            email=email,
            is_superuser=bool(payload.get("is_superuser", False)),
            name=payload.get("name"),
        )
    except (JWTError, ValueError):
        raise credentials_exception


def require_superuser(
    user: UserPayload = Depends(get_current_user_payload),
) -> UserPayload:
    """
    Dependência para rotas exclusivas de superadmin.
    Levanta 403 se o usuário não for superuser.
    """
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a superadmins.",
        )
    return user

