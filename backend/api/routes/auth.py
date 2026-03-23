"""
api/routes/auth.py

Endpoints de autenticação do Prospector.

Dois fluxos suportados:

1. Tenant via API Key (máquina-a-máquina)
   POST /auth/token  — username=slug, password=api_key → JWT de tenant

2. Usuário humano via Google OAuth 2.0
   GET  /auth/google/login     → retorna URL de autorização do Google
   GET  /auth/google/callback  → recebe code do Google, valida email, emite JWT
   GET  /auth/me               → retorna dados do usuário logado (requer JWT de usuário)

Segurança do fluxo Google OAuth:
  - Parâmetro `state` (CSRF token) armazenado no Redis com TTL de 5 minutos
  - Apenas emails pre-cadastrados na tabela `users` são aceitos
  - Email deve estar verificado pelo Google (email_verified=true)
  - JWT de usuário inclui campo "type":"user" para distinguir de JWT de tenant
"""

from __future__ import annotations

import secrets
from collections.abc import AsyncGenerator
from urllib.parse import urlencode

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import AsyncSessionLocal
from core.redis_client import redis_client
from core.security import (
    UserPayload,
    create_access_token,
    create_user_token,
    get_current_user_payload,
)
from models.tenant import Tenant
from models.user import User
from schemas.user import GoogleLoginUrlResponse, UserResponse, UserTokenResponse

logger = structlog.get_logger()

router = APIRouter(prefix="/auth", tags=["Auth"])

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# TTL do state CSRF para o fluxo Google OAuth (segundos)
_OAUTH_STATE_TTL = 300


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── Sessão sem RLS (usada internamente em auth) ───────────────────────

async def _get_raw_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


# ═══════════════════════════════════════════════════════════════════════
# 1. Fluxo Tenant (API Key)
# ═══════════════════════════════════════════════════════════════════════

@router.post("/token", response_model=TokenResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(_get_raw_session),
) -> TokenResponse:
    """
    Autentica um tenant via slug + api_key e emite um JWT de tenant.

    - username: slug do tenant
    - password: api_key plaintext gerada no cadastro
    """
    _credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    result = await db.execute(
        select(Tenant).where(Tenant.slug == form.username, Tenant.is_active.is_(True))
    )
    tenant = result.scalar_one_or_none()

    # Verificação em tempo constante para evitar timing attack
    stored_hash = tenant.api_key_hash if tenant else "$2b$12$invalidhashpadding000000000000000"
    valid = _pwd_context.verify(form.password, stored_hash)

    if not valid or tenant is None:
        raise _credentials_error

    token = create_access_token({"tenant_id": str(tenant.id)})
    return TokenResponse(access_token=token)


# ═══════════════════════════════════════════════════════════════════════
# 2. Fluxo Usuário (Google OAuth 2.0)
# ═══════════════════════════════════════════════════════════════════════

@router.get("/google/login")
async def google_login() -> RedirectResponse:
    """
    Inicia o fluxo Google OAuth.

    Gera um `state` aleatório (CSRF), armazena no Redis por 5 minutos
    e redireciona o browser diretamente para a URL de autorização do Google.
    """
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth não configurado neste ambiente.",
        )

    state = secrets.token_urlsafe(32)
    await redis_client.set(f"google_oauth_state:{state}", "1", ex=_OAUTH_STATE_TTL)

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    logger.info("auth.google_login.initiated")
    return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)


@router.get("/google/callback")
async def google_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(_get_raw_session),
) -> RedirectResponse:
    """
    Callback do Google OAuth.

    Passos:
      1. Valida o `state` (CSRF) no Redis — rejeita se expirado ou inválido
      2. Troca o `code` por access_token no Google
      3. Obtém o perfil do usuário via userinfo endpoint
      4. Verifica se o email está ativo na allowlist (`users`)
      5. Preenche google_sub e name no primeiro acesso
      6. Emite JWT de usuário

    Regras de acesso:
      - Email deve estar verificado pelo Google
      - Email deve estar previamente cadastrado na tabela `users`
      - Usuário deve estar ativo (is_active=True)
    """
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth não configurado neste ambiente.",
        )

    # ── 1. Verificar state CSRF ───────────────────────────────────────
    state_key = f"google_oauth_state:{state}"
    state_valid = await redis_client.get(state_key)
    if not state_valid:
        logger.warning("auth.google_callback.invalid_state")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parâmetro state inválido ou expirado. Reinicie o login.",
        )
    await redis_client.delete(state_key)

    # ── 2. Trocar code por access_token ──────────────────────────────
    async with httpx.AsyncClient(timeout=15.0) as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )

    if token_resp.status_code != 200:
        logger.error("auth.google_callback.token_exchange_failed", status=token_resp.status_code)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao trocar o código com o Google. Tente novamente.",
        )

    access_token_google: str = token_resp.json().get("access_token", "")
    if not access_token_google:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Google não retornou access_token.",
        )

    # ── 3. Buscar perfil do usuário no Google ─────────────────────────
    async with httpx.AsyncClient(timeout=15.0) as client:
        userinfo_resp = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token_google}"},
        )

    if userinfo_resp.status_code != 200:
        logger.error("auth.google_callback.userinfo_failed", status=userinfo_resp.status_code)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao obter perfil do Google.",
        )

    userinfo = userinfo_resp.json()
    email: str = userinfo.get("email", "").lower().strip()
    email_verified: bool = userinfo.get("verified_email", False)
    google_sub: str = str(userinfo.get("id", ""))
    name: str | None = userinfo.get("name")

    # ── 4. Validações de segurança ────────────────────────────────────
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google não retornou o email do usuário.",
        )

    if not email_verified:
        logger.warning("auth.google_callback.unverified_email", email=email)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email não verificado pelo Google. Verifique sua conta e tente novamente.",
        )

    # ── 5. Verificar se o email está na allowlist ─────────────────────
    result = await db.execute(
        select(User).where(func.lower(User.email) == email)
    )
    user = result.scalar_one_or_none()

    if user is None:
        logger.warning("auth.google_callback.email_not_registered", email=email)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Seu email não está cadastrado no sistema.",
        )

    if not user.is_active:
        logger.warning("auth.google_callback.user_inactive", email=email)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sua conta está inativa. Entre em contato com o administrador.",
        )

    # ── 6. Atualizar google_sub e name no primeiro login ──────────────
    changed = False
    if user.google_sub is None and google_sub:
        user.google_sub = google_sub
        changed = True
    if user.name is None and name:
        user.name = name
        changed = True
    if changed:
        await db.commit()
        await db.refresh(user)

    jwt_token = create_user_token(
        user_id=user.id,
        email=user.email,
        is_superuser=user.is_superuser,
        name=user.name,
    )

    logger.info(
        "auth.google_callback.success",
        email=user.email,
        is_superuser=user.is_superuser,
    )

    return RedirectResponse(
        url=f"{settings.FRONTEND_URL}/auth/callback?token={jwt_token}",
        status_code=status.HTTP_302_FOUND,
    )


# ═══════════════════════════════════════════════════════════════════════
# 3. Dados do usuário autenticado
# ═══════════════════════════════════════════════════════════════════════

@router.get("/me", response_model=UserResponse)
async def get_me(
    user_payload: UserPayload = Depends(get_current_user_payload),
    db: AsyncSession = Depends(_get_raw_session),
) -> UserResponse:
    """
    Retorna os dados do usuário humano autenticado.
    Requer JWT de usuário (Google OAuth) — não funciona com token de tenant.
    """
    result = await db.execute(
        select(User).where(User.id == user_payload.user_id, User.is_active.is_(True))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado ou inativo.",
        )
    return UserResponse.model_validate(user)


# ═══════════════════════════════════════════════════════════════════════
# Utilitário (usada na criação de tenant)
# ═══════════════════════════════════════════════════════════════════════

def hash_api_key(plaintext: str) -> str:
    """Gera hash bcrypt para armazenamento seguro da api_key."""
    return _pwd_context.hash(plaintext)

