"""
services/email_account_service.py

Serviço de gerenciamento de contas de e-mail.

Responsabilidades:
  - Criptografar/descriptografar campos sensíveis (Fernet)
  - Testar conexão SMTP antes de salvar
  - Gerar URL de OAuth do Google
  - Trocar authorization code por refresh_token (Google)
  - Construir o estado OAuth seguro (HMAC)
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta, timezone

import httpx
import structlog

from core.config import settings

logger = structlog.get_logger()


# ── Fernet — criptografia de campos sensíveis ─────────────────────────


def _get_fernet():
    """Retorna instância Fernet com a chave configurada."""
    from cryptography.fernet import Fernet  # noqa: PLC0415

    key = settings.EMAIL_ACCOUNT_ENCRYPTION_KEY
    if not key:
        raise RuntimeError(
            "EMAIL_ACCOUNT_ENCRYPTION_KEY não configurada no .env. "
            "Gere uma com: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_credential(value: str) -> str:
    """Retorna valor criptografado com Fernet (base64 safe)."""
    f = _get_fernet()
    return f.encrypt(value.encode()).decode()


def decrypt_credential(encrypted_value: str, settings_obj=None) -> str:
    """
    Decripta um campo criptografado com Fernet.
    O parâmetro settings_obj é aceito por compatibilidade mas ignorado
    (usa o settings global, consistente com o restante do sistema).
    """
    f = _get_fernet()
    return f.decrypt(encrypted_value.encode()).decode()


# ── SMTP — teste de conexão ───────────────────────────────────────────


async def test_smtp_connection(
    smtp_host: str,
    smtp_port: int,
    smtp_username: str,
    smtp_password: str,
    smtp_use_tls: bool = True,
) -> tuple[bool, str | None]:
    """
    Testa conexão SMTP sem enviar e-mail.
    Retorna (ok: bool, erro: str | None).
    """
    try:
        import aiosmtplib  # noqa: PLC0415

        if smtp_use_tls and smtp_port == 465:
            # SSL diretamente (SMTPS)
            smtp = aiosmtplib.SMTP(
                hostname=smtp_host,
                port=smtp_port,
                use_tls=True,
                timeout=15,
            )
        else:
            smtp = aiosmtplib.SMTP(
                hostname=smtp_host,
                port=smtp_port,
                timeout=15,
            )

        await smtp.connect()
        if smtp_use_tls and smtp_port != 465:
            await smtp.starttls()

        await smtp.login(smtp_username, smtp_password)
        await smtp.quit()
        return True, None

    except Exception as exc:
        error_msg = str(exc)
        logger.warning(
            "email_account.smtp_test_failed",
            host=smtp_host,
            port=smtp_port,
            error=error_msg,
        )
        return False, error_msg


# ── Google OAuth ──────────────────────────────────────────────────────

_GOOGLE_OAUTH_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.settings.basic",  # necessário para ler/escrever sendAs (assinatura)
    "openid",
    "email",
]


def _build_oauth_state(tenant_id: uuid.UUID) -> str:
    """
    Gera estado OAuth assinado com HMAC-SHA256.
    Formato JSON: {"tid": "<tenant_id>", "exp": <unix_ts>}
    Assinado com SECRET_KEY + prefixo "oauth-email-state:".
    """
    payload = {
        "tid": str(tenant_id),
        "exp": int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp()),
    }
    payload_b64 = base64.urlsafe_b64encode(
        json.dumps(payload).encode()
    ).decode()

    sig = hmac.new(
        (settings.SECRET_KEY + ":oauth-email-state").encode(),
        payload_b64.encode(),
        hashlib.sha256,
    ).hexdigest()

    return f"{payload_b64}.{sig}"


def _verify_oauth_state(state: str) -> dict | None:
    """
    Valida e decodifica o estado OAuth.
    Retorna o payload dict ou None se inválido/expirado.
    """
    try:
        payload_b64, sig = state.rsplit(".", 1)
    except ValueError:
        return None

    expected_sig = hmac.new(
        (settings.SECRET_KEY + ":oauth-email-state").encode(),
        payload_b64.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(sig, expected_sig):
        return None

    payload = json.loads(base64.urlsafe_b64decode(payload_b64 + "=="))

    if payload.get("exp", 0) < int(datetime.now(timezone.utc).timestamp()):
        return None  # expirado

    return payload


def get_tenant_id_from_oauth_state(state: str) -> uuid.UUID:
    """
    Valida o state OAuth HMAC e extrai o tenant_id.
    Lança ValueError se inválido ou expirado.
    """
    payload = _verify_oauth_state(state)
    if payload is None:
        raise ValueError("Estado OAuth inválido ou expirado")
    return uuid.UUID(payload["tid"])


def build_google_auth_url(tenant_id: uuid.UUID) -> str:
    """Constrói a URL de autorização OAuth do Google."""
    if not settings.GOOGLE_CLIENT_ID_EMAIL:
        raise RuntimeError("GOOGLE_CLIENT_ID_EMAIL não configurado no .env")

    state = _build_oauth_state(tenant_id)
    scope = " ".join(_GOOGLE_OAUTH_SCOPES)

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID_EMAIL,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI_EMAIL,
        "response_type": "code",
        "scope": scope,
        "access_type": "offline",
        "prompt": "consent",  # força retorno do refresh_token
        "state": state,
    }

    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"https://accounts.google.com/o/oauth2/v2/auth?{query}"


async def exchange_google_code(
    code: str,
    state: str,
) -> tuple[str, str]:
    """
    Troca o authorization code por (refresh_token, email).
    Retorna (refresh_token, email_address) ou lança exceção.
    """
    if not settings.GOOGLE_CLIENT_ID_EMAIL or not settings.GOOGLE_CLIENT_SECRET_EMAIL:
        raise RuntimeError("Google OAuth não configurado (credenciais ausentes)")

    # Valida o estado antes da troca
    payload = _verify_oauth_state(state)
    if payload is None:
        raise ValueError("Estado OAuth inválido ou expirado")

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID_EMAIL,
                "client_secret": settings.GOOGLE_CLIENT_SECRET_EMAIL,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI_EMAIL,
                "grant_type": "authorization_code",
            },
        )
        resp.raise_for_status()
        token_data = resp.json()

    refresh_token = token_data.get("refresh_token")
    if not refresh_token:
        raise ValueError(
            "Google não retornou refresh_token. "
            "Verifique se prompt=consent e access_type=offline estão corretos."
        )

    # Obtém o email do usuário via userinfo
    access_token = token_data.get("access_token")
    async with httpx.AsyncClient(timeout=10.0) as client:
        info_resp = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        info_resp.raise_for_status()
        email_address = info_resp.json().get("email", "")

    logger.info(
        "email_account.google_oauth_success",
        email=email_address,
    )
    return refresh_token, email_address


async def fetch_gmail_signature(encrypted_refresh_token: str) -> tuple[str | None, str]:
    """
    Busca a assinatura padrão do Gmail via API usando o refresh_token.
    Retorna (signature_html, send_as_email).
    """
    if not settings.GOOGLE_CLIENT_ID_EMAIL or not settings.GOOGLE_CLIENT_SECRET_EMAIL:
        raise RuntimeError("Google OAuth não configurado (credenciais ausentes)")

    # Troca refresh_token por access_token
    refresh_token = decrypt_credential(encrypted_refresh_token)
    async with httpx.AsyncClient(timeout=15.0) as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.GOOGLE_CLIENT_ID_EMAIL,
                "client_secret": settings.GOOGLE_CLIENT_SECRET_EMAIL,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        token_resp.raise_for_status()
        access_token = token_resp.json()["access_token"]

        # Lista os sendAs e pega a assinatura do alias padrão
        sig_resp = await client.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/settings/sendAs",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if sig_resp.status_code == 403:
            raise PermissionError(
                "Permissão insuficiente para ler assinatura do Gmail. "
                "Reconecte a conta: o escopo 'gmail.settings.basic' precisa ser autorizado."
            )
        sig_resp.raise_for_status()
        send_as_list = sig_resp.json().get("sendAs", [])

    # O alias padrão tem isDefault=True
    default_alias = next(
        (a for a in send_as_list if a.get("isDefault")),
        send_as_list[0] if send_as_list else None,
    )

    if default_alias is None:
        raise ValueError("Nenhum sendAs encontrado na conta Gmail")

    signature = default_alias.get("signature") or None  # pode ser "" → None
    send_as_email = default_alias.get("sendAsEmail", "")

    logger.info("email_account.gmail_signature_fetched", send_as=send_as_email)
    return signature, send_as_email
