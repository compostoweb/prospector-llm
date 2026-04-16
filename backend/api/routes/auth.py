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

import json
import secrets
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
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
from models.enums import TenantRole
from models.tenant import Tenant
from models.user import User
from schemas.browser_extension import (
    BrowserExtensionExchangeRequest,
    BrowserExtensionExchangeResponse,
    BrowserExtensionStartSessionRequest,
    BrowserExtensionStartSessionResponse,
    BrowserExtensionUserSummary,
)
from schemas.user import UserResponse
from services.browser_extension import build_extension_callback_url, ensure_extension_id_allowed
from services.tenant_access import resolve_user_login_context

logger = structlog.get_logger()

router = APIRouter(prefix="/auth", tags=["Auth"])

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# TTL do state CSRF para o fluxo Google OAuth (segundos)
_OAUTH_STATE_TTL = 300
_EXTENSION_OAUTH_STATE_PREFIX = "google_oauth_extension_state:"
_EXTENSION_GRANT_PREFIX = "extension_auth_grant:"
_EXTENSION_GRANT_TTL = 120


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


def _build_google_authorization_url(*, redirect_uri: str, state: str) -> str:
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)


async def _exchange_google_code_for_access_token(*, code: str, redirect_uri: str) -> str:
    async with httpx.AsyncClient(timeout=15.0) as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
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

    return access_token_google


async def _fetch_google_userinfo(access_token_google: str) -> dict[str, object]:
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

    return dict(userinfo_resp.json())


async def _resolve_active_user_from_google_profile(
    *,
    db: AsyncSession,
    userinfo: dict[str, object],
) -> User:
    email = str(userinfo.get("email", "")).lower().strip()
    email_verified = bool(userinfo.get("verified_email", False))
    google_sub = str(userinfo.get("id", ""))
    name_value = userinfo.get("name")
    name = str(name_value) if isinstance(name_value, str) else None

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

    result = await db.execute(select(User).where(func.lower(User.email) == email))
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

    return user


async def _build_user_access_context(
    *,
    db: AsyncSession,
    user: User,
) -> tuple[uuid.UUID | None, TenantRole | None]:
    tenant_id, tenant_role = await resolve_user_login_context(db, user)
    if not user.is_superuser and tenant_id is None:
        logger.warning("auth.user_without_tenant_membership", email=user.email)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seu usuário não está vinculado a nenhum tenant ativo.",
        )
    return tenant_id, tenant_role


def _build_extension_redirect(
    *, extension_id: str, grant_code: str | None = None, error: str | None = None
) -> str:
    params: dict[str, str] = {}
    if grant_code:
        params["grant_code"] = grant_code
    if error:
        params["error"] = error
    return build_extension_callback_url(extension_id, params)


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

    url = _build_google_authorization_url(
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
        state=state,
    )
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

    access_token_google = await _exchange_google_code_for_access_token(
        code=code,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
    )
    userinfo = await _fetch_google_userinfo(access_token_google)
    user = await _resolve_active_user_from_google_profile(db=db, userinfo=userinfo)
    tenant_id, tenant_role = await _build_user_access_context(db=db, user=user)

    jwt_token = create_user_token(
        user_id=user.id,
        email=user.email,
        is_superuser=user.is_superuser,
        name=user.name,
        tenant_id=tenant_id,
        tenant_role=tenant_role,
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


@router.post(
    "/extension/session/start",
    response_model=BrowserExtensionStartSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_extension_session(
    body: BrowserExtensionStartSessionRequest,
) -> BrowserExtensionStartSessionResponse:
    if not settings.EXTENSION_LINKEDIN_CAPTURE_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Captura via extensao desabilitada neste ambiente.",
        )

    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth nao configurado neste ambiente.",
        )

    extension_id = ensure_extension_id_allowed(body.extension_id)
    auth_session_id = uuid.uuid4()
    state = secrets.token_urlsafe(32)
    state_key = f"{_EXTENSION_OAUTH_STATE_PREFIX}{state}"
    payload = {
        "auth_session_id": str(auth_session_id),
        "extension_id": extension_id,
        "extension_version": body.extension_version,
        "browser": body.browser,
    }
    await redis_client.set(state_key, json.dumps(payload), ex=_OAUTH_STATE_TTL)

    authorization_url = _build_google_authorization_url(
        redirect_uri=settings.GOOGLE_EXTENSION_REDIRECT_URI,
        state=state,
    )
    logger.info(
        "extension.auth.started",
        auth_session_id=str(auth_session_id),
        extension_id=extension_id,
        browser=body.browser,
        extension_version=body.extension_version,
    )
    return BrowserExtensionStartSessionResponse(
        auth_session_id=auth_session_id,
        authorization_url=authorization_url,
        expires_in=_OAUTH_STATE_TTL,
    )


@router.get("/extension/google/callback")
async def extension_google_callback(
    state: str,
    code: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
    db: AsyncSession = Depends(_get_raw_session),
) -> RedirectResponse:
    state_key = f"{_EXTENSION_OAUTH_STATE_PREFIX}{state}"
    raw_state = await redis_client.get(state_key)
    if not raw_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sessao OAuth da extensao invalida ou expirada.",
        )
    await redis_client.delete(state_key)

    state_payload = json.loads(raw_state)
    extension_id = ensure_extension_id_allowed(str(state_payload["extension_id"]))

    if error:
        logger.warning(
            "extension.auth.google_error",
            extension_id=extension_id,
            error=error,
            error_description=error_description,
        )
        return RedirectResponse(
            url=_build_extension_redirect(
                extension_id=extension_id,
                error=(error_description or error),
            ),
            status_code=status.HTTP_302_FOUND,
        )

    if not code:
        return RedirectResponse(
            url=_build_extension_redirect(
                extension_id=extension_id,
                error="Authorization code ausente.",
            ),
            status_code=status.HTTP_302_FOUND,
        )

    try:
        access_token_google = await _exchange_google_code_for_access_token(
            code=code,
            redirect_uri=settings.GOOGLE_EXTENSION_REDIRECT_URI,
        )
        userinfo = await _fetch_google_userinfo(access_token_google)
        user = await _resolve_active_user_from_google_profile(db=db, userinfo=userinfo)
        tenant_id, tenant_role = await _build_user_access_context(db=db, user=user)
    except HTTPException as exc:
        logger.warning(
            "extension.auth.callback_failed",
            extension_id=extension_id,
            error_detail=str(exc.detail),
        )
        return RedirectResponse(
            url=_build_extension_redirect(
                extension_id=extension_id,
                error=str(exc.detail),
            ),
            status_code=status.HTTP_302_FOUND,
        )

    grant_code = secrets.token_urlsafe(32)
    grant_key = f"{_EXTENSION_GRANT_PREFIX}{grant_code}"
    grant_payload = {
        "extension_id": extension_id,
        "user_id": str(user.id),
        "email": user.email,
        "name": user.name,
        "is_superuser": user.is_superuser,
        "tenant_id": str(tenant_id) if tenant_id else None,
        "tenant_role": tenant_role.value if tenant_role else None,
    }
    await redis_client.set(grant_key, json.dumps(grant_payload), ex=_EXTENSION_GRANT_TTL)
    logger.info(
        "extension.auth.grant_created",
        extension_id=extension_id,
        user_id=str(user.id),
    )
    return RedirectResponse(
        url=_build_extension_redirect(extension_id=extension_id, grant_code=grant_code),
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/extension/session/exchange", response_model=BrowserExtensionExchangeResponse)
async def exchange_extension_session(
    body: BrowserExtensionExchangeRequest,
) -> BrowserExtensionExchangeResponse:
    extension_id = ensure_extension_id_allowed(body.extension_id)
    grant_key = f"{_EXTENSION_GRANT_PREFIX}{body.grant_code}"
    raw_grant = await redis_client.get(grant_key)
    if not raw_grant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Grant da extensao invalido ou expirado.",
        )

    grant_payload = json.loads(raw_grant)
    if grant_payload.get("extension_id") != extension_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Grant nao pertence a esta extensao.",
        )

    await redis_client.delete(grant_key)
    user_id = uuid.UUID(str(grant_payload["user_id"]))
    jwt_token = create_user_token(
        user_id=user_id,
        email=str(grant_payload["email"]),
        is_superuser=bool(grant_payload.get("is_superuser", False)),
        name=str(grant_payload["name"]) if grant_payload.get("name") else None,
        tenant_id=(
            uuid.UUID(str(grant_payload["tenant_id"])) if grant_payload.get("tenant_id") else None
        ),
        tenant_role=(
            TenantRole(str(grant_payload["tenant_role"]))
            if grant_payload.get("tenant_role")
            else None
        ),
    )
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    logger.info(
        "extension.auth.exchanged",
        extension_id=extension_id,
        user_id=str(user_id),
    )
    return BrowserExtensionExchangeResponse(
        access_token=jwt_token,
        expires_at=expires_at,
        user=BrowserExtensionUserSummary(
            id=user_id,
            email=str(grant_payload["email"]),
            name=str(grant_payload["name"]) if grant_payload.get("name") else None,
            is_superuser=bool(grant_payload.get("is_superuser", False)),
        ),
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
    tenant_id, tenant_role = await _build_user_access_context(db=db, user=user)
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        tenant_id=tenant_id,
        tenant_role=tenant_role,
        created_at=user.created_at,
    )


# ═══════════════════════════════════════════════════════════════════════
# Utilitário (usada na criação de tenant)
# ═══════════════════════════════════════════════════════════════════════


def hash_api_key(plaintext: str) -> str:
    """Gera hash bcrypt para armazenamento seguro da api_key."""
    return _pwd_context.hash(plaintext)
