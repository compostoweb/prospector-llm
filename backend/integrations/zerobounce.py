"""
integrations/zerobounce.py

Cliente HTTP assíncrono para ZeroBounce — validação de endereços de e-mail.

Base URL: https://api.zerobounce.net/v2
Auth:     api_key query param
"""

from __future__ import annotations

import httpx
import structlog

from core.config import settings

logger = structlog.get_logger()

_BASE_URL = "https://api.zerobounce.net/v2"
_TIMEOUT = 20.0

# Statuses considerados válidos para uso em prospecção
_VALID_STATUSES = {"valid", "catch-all"}
# Statuses que descartam o e-mail definitivamente
_INVALID_STATUSES = {"invalid", "disposable", "abuse", "do_not_mail"}


class ZeroBounceClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=_BASE_URL,
            timeout=_TIMEOUT,
        )
        self._api_key = settings.ZEROBOUNCE_API_KEY or ""

    async def validate(self, email: str) -> bool:
        """
        Valida o endereço de e-mail via ZeroBounce /validate.

        Retorna True se o e-mail é utilizável (valid ou catch-all).
        Retorna False se inválido, temporário ou descartável.
        Em caso de erro de rede, retorna True para não bloquear o pipeline
        (fail open — o e-mail permanece e será reavaliado mais tarde).
        """
        try:
            resp = await self._client.get(
                "/validate",
                params={"api_key": self._api_key, "email": email},
            )
            resp.raise_for_status()
            data = resp.json()
            status: str = (data.get("status") or "unknown").lower()
            sub_status: str = (data.get("sub_status") or "").lower()

            if status in _INVALID_STATUSES:
                logger.info("zerobounce.invalid", email=email, status=status, sub_status=sub_status)
                return False

            logger.info("zerobounce.valid", email=email, status=status)
            return status in _VALID_STATUSES

        except httpx.HTTPStatusError as exc:
            logger.warning("zerobounce.http_error", status=exc.response.status_code, email=email)
            return True  # fail open
        except Exception as exc:  # noqa: BLE001
            logger.error("zerobounce.exception", error=str(exc), email=email)
            return True  # fail open

    async def aclose(self) -> None:
        await self._client.aclose()


# Singleton
zerobounce_client = ZeroBounceClient()
