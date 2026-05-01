"""
services/linkedin_account_service.py

Serviço de gerenciamento de contas LinkedIn.

Responsabilidades:
  - Criptografar/descriptografar o cookie li_at (Fernet)
  - Testar ping de conta nativa(valida se o cookie ainda é válido)
"""

from __future__ import annotations

import base64
import hmac
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256

import structlog

from core.config import settings

logger = structlog.get_logger()


@dataclass(frozen=True)
class HostedLinkedInAuthState:
    tenant_id: uuid.UUID
    user_id: uuid.UUID | None
    display_name: str
    linkedin_username: str | None
    supports_inmail: bool


# ── Fernet — criptografia do cookie li_at ─────────────────────────────


def _get_fernet():
    """Retorna instância Fernet com a chave configurada."""
    from cryptography.fernet import Fernet  # noqa: PLC0415

    key = settings.LINKEDIN_ACCOUNT_ENCRYPTION_KEY
    if not key:
        # Fallback para a mesma chave de email — ambas são do mesmo tenant
        key = settings.EMAIL_ACCOUNT_ENCRYPTION_KEY
    if not key:
        raise RuntimeError(
            "LINKEDIN_ACCOUNT_ENCRYPTION_KEY não configurada. "
            'Gere com: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_credential(value: str) -> str:
    """Retorna valor criptografado com Fernet (base64 safe)."""
    f = _get_fernet()
    return f.encrypt(value.encode()).decode()


def decrypt_credential(encrypted_value: str, settings_obj=None) -> str:
    """Decripta um cookie/token armazenado com Fernet."""
    f = _get_fernet()
    return f.decrypt(encrypted_value.encode()).decode()


# ── Unipile Hosted Auth state ────────────────────────────────────────


def build_hosted_linkedin_auth_state(
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID | None,
    display_name: str,
    linkedin_username: str | None,
    supports_inmail: bool,
    ttl_minutes: int = 60,
) -> str:
    payload = {
        "tid": str(tenant_id),
        "uid": str(user_id) if user_id else None,
        "display_name": display_name,
        "linkedin_username": linkedin_username,
        "supports_inmail": supports_inmail,
        "exp": int((datetime.now(UTC) + timedelta(minutes=ttl_minutes)).timestamp()),
    }
    payload_b64 = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode()
    ).decode()
    signature = hmac.new(
        settings.SECRET_KEY.encode(),
        f"unipile-hosted-linkedin:{payload_b64}".encode(),
        sha256,
    ).hexdigest()
    return f"{payload_b64}.{signature}"


def parse_hosted_linkedin_auth_state(state: str) -> HostedLinkedInAuthState:
    try:
        payload_b64, signature = state.split(".", 1)
    except ValueError as exc:
        raise ValueError("Estado Hosted Auth inválido") from exc

    expected_signature = hmac.new(
        settings.SECRET_KEY.encode(),
        f"unipile-hosted-linkedin:{payload_b64}".encode(),
        sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        raise ValueError("Estado Hosted Auth inválido")

    try:
        payload = json.loads(base64.urlsafe_b64decode(payload_b64.encode()))
    except Exception as exc:
        raise ValueError("Estado Hosted Auth inválido") from exc

    expires_at = int(payload.get("exp") or 0)
    if expires_at < int(datetime.now(UTC).timestamp()):
        raise ValueError("Estado Hosted Auth expirado")

    display_name = str(payload.get("display_name") or "").strip()
    if not display_name:
        raise ValueError("Estado Hosted Auth sem nome de exibição")

    user_id = payload.get("uid")
    linkedin_username = payload.get("linkedin_username")
    return HostedLinkedInAuthState(
        tenant_id=uuid.UUID(str(payload["tid"])),
        user_id=uuid.UUID(str(user_id)) if user_id else None,
        display_name=display_name,
        linkedin_username=str(linkedin_username).strip() if linkedin_username else None,
        supports_inmail=bool(payload.get("supports_inmail", False)),
    )


# ── Ping de conta nativa ──────────────────────────────────────────────


async def ping_native_account(li_at: str) -> tuple[bool, str | None]:
    """
    Verifica se o cookie li_at ainda é válido fazendo uma chamada
    ao endpoint de perfil próprio da Voyager API.
    Retorna (ok: bool, erro: str | None).
    """
    import httpx  # noqa: PLC0415

    headers = {
        "Cookie": f"li_at={li_at}",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "X-Li-Lang": "pt_BR",
        "X-RestLi-Protocol-Version": "2.0.0",
        "Csrf-Token": "ajax:0000000000000000000",
        "X-Li-Page-Instance": "urn:li:page:d_flagship3_profile_view_base",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://www.linkedin.com/voyager/api/me",
                headers=headers,
            )
            if resp.status_code == 200:
                return True, None
            if resp.status_code in (401, 403):
                return False, "Cookie li_at inválido ou expirado"
            return False, f"Status inesperado: {resp.status_code}"
    except Exception as exc:
        return False, str(exc)
