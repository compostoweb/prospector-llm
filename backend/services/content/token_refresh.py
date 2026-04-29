"""
services/content/token_refresh.py

Phase 3B — refresh token LinkedIn.

Helpers para detectar 401, renovar access_token via refresh_token e persistir
o novo token criptografado.

Uso:
    access_token = await ensure_fresh_token(db, account)
    # ou em caso de 401 inesperado:
    access_token = await refresh_and_persist(db, account)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from models.content_linkedin_account import ContentLinkedInAccount
from services.content.linkedin_client import LinkedInClient, LinkedInClientError

logger = structlog.get_logger()


# Margem de seguranca para considerar token "perto de expirar"
_REFRESH_MARGIN = timedelta(minutes=10)


def _maybe_encrypt(value: str) -> str:
    if not settings.LINKEDIN_ACCOUNT_ENCRYPTION_KEY:
        return value
    try:
        from cryptography.fernet import Fernet

        fernet = Fernet(settings.LINKEDIN_ACCOUNT_ENCRYPTION_KEY.encode())
        return fernet.encrypt(value.encode()).decode()
    except Exception as exc:
        logger.warning("content.token_refresh.encrypt_failed", error=str(exc))
        return value


def _maybe_decrypt(value: str) -> str:
    if not settings.LINKEDIN_ACCOUNT_ENCRYPTION_KEY:
        return value
    try:
        from cryptography.fernet import Fernet

        fernet = Fernet(settings.LINKEDIN_ACCOUNT_ENCRYPTION_KEY.encode())
        return fernet.decrypt(value.encode()).decode()
    except Exception as exc:
        logger.warning("content.token_refresh.decrypt_failed", error=str(exc))
        return value


async def refresh_and_persist(
    db: AsyncSession,
    account: ContentLinkedInAccount,
) -> str:
    """
    Renova access_token via refresh_token e persiste no banco.

    Retorna o novo access_token (plain text).
    Levanta LinkedInClientError ou ValueError em caso de falha.
    """
    if not account.refresh_token:
        raise ValueError(f"Conta {account.id} sem refresh_token — usuário precisa reconectar.")
    if not settings.LINKEDIN_CLIENT_ID or not settings.LINKEDIN_CLIENT_SECRET:
        raise ValueError("LINKEDIN_CLIENT_ID/SECRET não configurados.")

    refresh_token_plain = _maybe_decrypt(account.refresh_token)

    response = await LinkedInClient.refresh_access_token(
        refresh_token=refresh_token_plain,
        client_id=settings.LINKEDIN_CLIENT_ID,
        client_secret=settings.LINKEDIN_CLIENT_SECRET,
    )

    new_access_token: str = response["access_token"]
    expires_in: int = int(response.get("expires_in", 0))
    new_refresh_token: str | None = response.get("refresh_token")
    refresh_expires_in: int | None = response.get("refresh_token_expires_in")

    now = datetime.now(UTC)
    account.access_token = _maybe_encrypt(new_access_token)
    if expires_in:
        account.token_expires_at = now + timedelta(seconds=expires_in)
    if new_refresh_token:
        account.refresh_token = _maybe_encrypt(new_refresh_token)
    if refresh_expires_in:
        account.refresh_token_expires_at = now + timedelta(seconds=refresh_expires_in)

    await db.commit()
    logger.info(
        "content.token_refreshed",
        account_id=str(account.id),
        tenant_id=str(account.tenant_id),
        expires_in=expires_in,
    )
    return new_access_token


async def ensure_fresh_token(
    db: AsyncSession,
    account: ContentLinkedInAccount,
) -> str:
    """
    Retorna access_token plain text. Renova proativamente se faltar < 10min para expirar.

    Fallback: se nao tiver refresh_token, retorna o token atual sem renovar.
    """
    expires_at = account.token_expires_at
    if expires_at is not None and account.refresh_token:
        # Normaliza tz-aware
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at - datetime.now(UTC) < _REFRESH_MARGIN:
            try:
                return await refresh_and_persist(db, account)
            except (LinkedInClientError, ValueError) as exc:
                logger.warning(
                    "content.token_refresh.proactive_failed",
                    account_id=str(account.id),
                    error=str(exc),
                )
                # Cai para o token atual — pode falhar no uso
    return _maybe_decrypt(account.access_token)


def is_token_expired_error(exc: LinkedInClientError) -> bool:
    """Heuristica: 401 indica token invalido/expirado."""
    return exc.status_code == 401
