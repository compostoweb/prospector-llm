"""
services/linkedin_account_service.py

Serviço de gerenciamento de contas LinkedIn.

Responsabilidades:
  - Criptografar/descriptografar o cookie li_at (Fernet)
  - Testar ping de conta nativa(valida se o cookie ainda é válido)
"""

from __future__ import annotations

import structlog

from core.config import settings

logger = structlog.get_logger()


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
            "Gere com: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
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
