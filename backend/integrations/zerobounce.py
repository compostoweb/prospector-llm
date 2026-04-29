"""
integrations/zerobounce.py

Cliente HTTP assíncrono para ZeroBounce — validação de endereços de e-mail.

Base URL: https://api.zerobounce.net/v2
Auth:     api_key query param
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx
import structlog

from core.config import settings
from models.enums import EmailVerificationStatus

logger = structlog.get_logger()

_BASE_URL = "https://api.zerobounce.net/v2"
_TIMEOUT = 20.0

_STATUS_MAPPING = {
    "valid": EmailVerificationStatus.VALID,
    "catch-all": EmailVerificationStatus.ACCEPT_ALL,
    "catch_all": EmailVerificationStatus.ACCEPT_ALL,
    "accept_all": EmailVerificationStatus.ACCEPT_ALL,
    "unknown": EmailVerificationStatus.UNKNOWN,
    "invalid": EmailVerificationStatus.INVALID,
    "disposable": EmailVerificationStatus.DISPOSABLE,
    "abuse": EmailVerificationStatus.ABUSE,
    "do_not_mail": EmailVerificationStatus.DO_NOT_MAIL,
    "spamtrap": EmailVerificationStatus.SPAMTRAP,
    "webmail": EmailVerificationStatus.WEBMAIL,
}


@dataclass(frozen=True)
class ZeroBounceValidationResult:
    email: str
    status: EmailVerificationStatus
    sub_status: str | None = None
    mx_found: bool | None = None
    smtp_provider: str | None = None
    active_in_days: str | None = None
    free_email: bool | None = None
    domain_age_days: str | None = None
    processed_at: str | None = None

    @property
    def is_verified(self) -> bool:
        return self.status == EmailVerificationStatus.VALID

    @property
    def is_usable(self) -> bool:
        return self.status in {
            EmailVerificationStatus.VALID,
            EmailVerificationStatus.ACCEPT_ALL,
        }


class ZeroBounceClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=_BASE_URL,
            timeout=_TIMEOUT,
        )
        self._api_key = settings.ZEROBOUNCE_API_KEY or ""

    async def validate_with_details(self, email: str) -> ZeroBounceValidationResult:
        """
        Valida o endereço de e-mail via ZeroBounce /validate.

        Retorna um resultado estruturado para distinguir e-mails válidos,
        accept-all, unknown e inválidos sem depender de bool/fail open.
        """
        try:
            resp = await self._client.get(
                "/validate",
                params={"api_key": self._api_key, "email": email},
            )
            resp.raise_for_status()
            data = resp.json()
            status_raw: str = (data.get("status") or "unknown").lower()
            sub_status: str = (data.get("sub_status") or "").lower()
            status = _STATUS_MAPPING.get(status_raw, EmailVerificationStatus.UNKNOWN)

            logger.info(
                "zerobounce.checked",
                email=email,
                status=status.value,
                sub_status=sub_status or None,
            )
            return ZeroBounceValidationResult(
                email=email,
                status=status,
                sub_status=sub_status or None,
                mx_found=_optional_bool(data.get("mx_found")),
                smtp_provider=_optional_str(data.get("smtp_provider")),
                active_in_days=_optional_str(data.get("active_in_days")),
                free_email=_optional_bool(data.get("free_email")),
                domain_age_days=_optional_str(data.get("domain_age_days")),
                processed_at=_optional_str(data.get("processed_at")),
            )

        except httpx.HTTPStatusError as exc:
            logger.warning("zerobounce.http_error", status=exc.response.status_code, email=email)
            return ZeroBounceValidationResult(email=email, status=EmailVerificationStatus.UNKNOWN)
        except Exception as exc:  # noqa: BLE001
            logger.error("zerobounce.exception", error=str(exc), email=email)
            return ZeroBounceValidationResult(email=email, status=EmailVerificationStatus.UNKNOWN)

    async def validate(self, email: str) -> bool:
        """
        Retorna True apenas quando a validação confirma entrega (`valid`).

        `accept_all` e `unknown` não são tratados como verificados, para evitar
        score artificialmente alto no enriquecimento.
        """
        result = await self.validate_with_details(email)
        return result.is_verified

    async def aclose(self) -> None:
        await self._client.aclose()


# Singleton
zerobounce_client = ZeroBounceClient()


def _optional_bool(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


def _optional_str(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None
