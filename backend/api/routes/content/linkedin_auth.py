"""
api/routes/content/linkedin_auth.py

OAuth 2.0 do LinkedIn para o modulo Content Hub.
Produto: Share on LinkedIn (scopes: r_liteprofile w_member_social).

GET  /content/linkedin/auth-url   — gera URL de autorizacao OAuth com state
GET  /content/linkedin/callback   — recebe code, troca por token, salva conta
GET  /content/linkedin/status     — retorna conta LinkedIn ativa do tenant
DELETE /content/linkedin/disconnect — desativa conta (is_active=False)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_effective_tenant_id, get_session_flexible
from core.config import settings
from core.database import AsyncSessionLocal, get_session
from core.redis_client import redis_client
from models.content_linkedin_account import ContentLinkedInAccount
from schemas.content import ContentLinkedInAccountResponse, LinkedInAuthUrl
from services.content.linkedin_client import LinkedInClient, LinkedInClientError

logger = structlog.get_logger()

router = APIRouter(prefix="/linkedin", tags=["Content Hub — LinkedIn OAuth"])

_OAUTH_SCOPES = "openid profile email w_member_social"
_OAUTH_AUTHORIZE_URL = "https://www.linkedin.com/oauth/v2/authorization"
_STATE_REDIS_PREFIX = "content:linkedin:oauth_state:"
_STATE_TTL_SECONDS = 600  # 10 minutos


# ── Gerar URL de autorizacao ──────────────────────────────────────────

@router.get("/auth-url", response_model=LinkedInAuthUrl)
async def get_auth_url(
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
) -> LinkedInAuthUrl:
    """
    Gera a URL de autorizacao OAuth do LinkedIn.
    Salva um state UUID no Redis (TTL 10 min) para validacao no callback.
    """
    if not settings.LINKEDIN_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LinkedIn OAuth nao configurado. Defina LINKEDIN_CLIENT_ID e LINKEDIN_CLIENT_SECRET.",
        )

    state = str(uuid.uuid4())
    redis_key = f"{_STATE_REDIS_PREFIX}{state}"
    await redis_client.set(redis_key, str(tenant_id), ex=_STATE_TTL_SECONDS)

    params = urlencode({
        "response_type": "code",
        "client_id": settings.LINKEDIN_CLIENT_ID,
        "redirect_uri": settings.LINKEDIN_REDIRECT_URI,
        "scope": _OAUTH_SCOPES,
        "state": state,
    })
    url = f"{_OAUTH_AUTHORIZE_URL}?{params}"
    logger.info("content.linkedin_oauth_url_generated", tenant_id=str(tenant_id))
    return LinkedInAuthUrl(url=url)


# ── Callback OAuth ────────────────────────────────────────────────────

@router.get("/callback")
async def oauth_callback(
    state: str = Query(..., description="State UUID gerado em /auth-url"),
    code: str | None = Query(None, description="Authorization code retornado pelo LinkedIn"),
    error: str | None = Query(None),
    error_description: str | None = Query(None),
) -> RedirectResponse:
    """
    Recebe o authorization_code do LinkedIn, troca por tokens e salva a conta.

    Valida o state no Redis para prevenir CSRF.
    Faz upsert em content_linkedin_accounts (um por tenant).
    Nao exige JWT — tenant_id e extraido do state armazenado no Redis.
    Redireciona para o frontend apos sucesso ou erro.
    """
    _frontend_settings = f"{settings.FRONTEND_URL}/content/configuracoes"

    # LinkedIn redirecionou com erro
    if error:
        logger.warning(
            "content.linkedin_oauth_error",
            error=error,
            error_description=error_description,
        )
        from urllib.parse import quote
        msg = quote(f"LinkedIn recusou: {error}. {error_description or ''}".strip())
        return RedirectResponse(url=f"{_frontend_settings}?linkedin_error={msg}")

    # Validar state (anti-CSRF)
    redis_key = f"{_STATE_REDIS_PREFIX}{state}"
    tenant_id_str: str | None = await redis_client.get(redis_key)
    if not tenant_id_str:
        return RedirectResponse(url=f"{_frontend_settings}?linkedin_error=State+invalido+ou+expirado")
    await redis_client.delete(redis_key)
    tenant_id = uuid.UUID(tenant_id_str)

    if not settings.LINKEDIN_CLIENT_ID or not settings.LINKEDIN_CLIENT_SECRET:
        return RedirectResponse(url=f"{_frontend_settings}?linkedin_error=LinkedIn+OAuth+nao+configurado")

    if not code:
        return RedirectResponse(url=f"{_frontend_settings}?linkedin_error=Authorization+code+ausente")

    # Trocar code por tokens
    try:
        token_data = await LinkedInClient.exchange_code_for_token(
            code=code,
            client_id=settings.LINKEDIN_CLIENT_ID,
            client_secret=settings.LINKEDIN_CLIENT_SECRET,
            redirect_uri=settings.LINKEDIN_REDIRECT_URI,
        )
    except LinkedInClientError as exc:
        logger.error("content.linkedin_token_exchange_failed", error=str(exc), tenant_id=str(tenant_id))
        from urllib.parse import quote
        msg = quote(f"Falha ao trocar token: {exc.detail}")
        return RedirectResponse(url=f"{_frontend_settings}?linkedin_error={msg}")

    access_token: str = token_data["access_token"]
    refresh_token: str | None = token_data.get("refresh_token")
    expires_in: int | None = token_data.get("expires_in")
    token_expires_at: datetime | None = None
    if expires_in:
        token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    # Buscar perfil do LinkedIn
    try:
        profile = await LinkedInClient.get_profile(access_token)
    except LinkedInClientError as exc:
        logger.error("content.linkedin_profile_fetch_failed", error=str(exc), tenant_id=str(tenant_id))
        from urllib.parse import quote
        msg = quote(f"Falha ao buscar perfil: {exc.detail}")
        return RedirectResponse(url=f"{_frontend_settings}?linkedin_error={msg}")

    # OpenID Connect retorna 'sub' como id; fallback para 'id' (v2 legacy)
    person_id: str = profile.get("sub") or profile.get("id") or ""
    person_urn = f"urn:li:person:{person_id}"
    first_name = profile.get("given_name") or profile.get("localizedFirstName", "")
    last_name = profile.get("family_name") or profile.get("localizedLastName", "")
    display_name = f"{first_name} {last_name}".strip() or profile.get("name") or None

    # Criptografar tokens se chave disponivel
    access_token_stored = _maybe_encrypt(access_token)
    refresh_token_stored = _maybe_encrypt(refresh_token) if refresh_token else None

    # Upsert — um registro por tenant (sessao sem RLS; tenant ja validado via state)
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ContentLinkedInAccount).where(ContentLinkedInAccount.tenant_id == tenant_id)
        )
        account = result.scalar_one_or_none()

        now = datetime.now(timezone.utc)
        if account is None:
            account = ContentLinkedInAccount(
                tenant_id=tenant_id,
                person_id=person_id,
                person_urn=person_urn,
                display_name=display_name,
                access_token=access_token_stored,
                refresh_token=refresh_token_stored,
                token_expires_at=token_expires_at,
                scopes=_OAUTH_SCOPES,
                is_active=True,
                connected_at=now,
            )
            db.add(account)
        else:
            account.person_id = person_id
            account.person_urn = person_urn
            account.display_name = display_name
            account.access_token = access_token_stored
            account.refresh_token = refresh_token_stored
            account.token_expires_at = token_expires_at
            account.scopes = _OAUTH_SCOPES
            account.is_active = True
            account.connected_at = now

        await db.commit()
        await db.refresh(account)
        logger.info(
            "content.linkedin_account_connected",
            tenant_id=str(tenant_id),
            person_id=person_id,
            display_name=display_name,
        )
        return RedirectResponse(url=f"{_frontend_settings}?linkedin_connected=1")


# ── Status ────────────────────────────────────────────────────────────

@router.get("/status", response_model=ContentLinkedInAccountResponse)
async def get_linkedin_status(
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ContentLinkedInAccountResponse:
    """Retorna a conta LinkedIn ativa do tenant, ou 404 se nao conectada."""
    result = await db.execute(
        select(ContentLinkedInAccount).where(
            ContentLinkedInAccount.tenant_id == tenant_id,
            ContentLinkedInAccount.is_active.is_(True),
        )
    )
    account = result.scalar_one_or_none()
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhuma conta LinkedIn conectada para este tenant.",
        )
    return ContentLinkedInAccountResponse.model_validate(account)


# ── Desconectar ───────────────────────────────────────────────────────

@router.delete("/disconnect", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def disconnect_linkedin(
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> None:
    """Desativa a conta LinkedIn do tenant (is_active=False)."""
    result = await db.execute(
        select(ContentLinkedInAccount).where(
            ContentLinkedInAccount.tenant_id == tenant_id,
        )
    )
    account = result.scalar_one_or_none()
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhuma conta LinkedIn encontrada para desconectar.",
        )
    account.is_active = False
    await db.commit()
    logger.info("content.linkedin_account_disconnected", tenant_id=str(tenant_id))


# ── Criptografia de tokens ────────────────────────────────────────────

def _maybe_encrypt(value: str) -> str:
    """
    Criptografa o valor com Fernet se LINKEDIN_ACCOUNT_ENCRYPTION_KEY estiver configurada.
    Retorna o valor plain text caso a chave nao esteja disponivel.
    """
    if not settings.LINKEDIN_ACCOUNT_ENCRYPTION_KEY:
        return value
    try:
        from cryptography.fernet import Fernet
        fernet = Fernet(settings.LINKEDIN_ACCOUNT_ENCRYPTION_KEY.encode())
        return fernet.encrypt(value.encode()).decode()
    except Exception as exc:
        logger.warning("content.linkedin_token_encryption_failed", error=str(exc))
        return value
