from __future__ import annotations

import re
from urllib.parse import urlencode

from fastapi import HTTPException, status

from core.config import settings

_EXTENSION_ID_RE = re.compile(r"^[a-z0-9]{8,64}$")


def normalize_extension_id(extension_id: str) -> str:
    return extension_id.strip().lower()


def validate_extension_id_format(extension_id: str) -> str:
    normalized = normalize_extension_id(extension_id)
    if not _EXTENSION_ID_RE.fullmatch(normalized):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Extension ID invalido.",
        )
    return normalized


def ensure_extension_id_allowed(extension_id: str) -> str:
    normalized = validate_extension_id_format(extension_id)
    raw_allowed_ids = settings.EXTENSION_ALLOWED_IDS or ""
    allowed_ids = {item.strip().lower() for item in raw_allowed_ids.split(",") if item.strip()}

    if allowed_ids and normalized not in allowed_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Extension ID nao autorizado neste ambiente.",
        )

    if not allowed_ids and settings.ENV == "prod":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Allowlist da extensao nao configurada neste ambiente.",
        )

    return normalized


def build_extension_callback_url(extension_id: str, params: dict[str, str]) -> str:
    normalized = validate_extension_id_format(extension_id)
    query = urlencode(params)
    return f"https://{normalized}.chromiumapp.org/provider_cb?{query}"
