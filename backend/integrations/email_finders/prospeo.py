"""
integrations/email_finders/prospeo.py

Cliente HTTP assíncrono para Prospeo — Enrich Person API (v2, mar/2026).

Base URL: https://api.prospeo.io
Auth:     X-KEY header
Docs:     https://prospeo.io/api-docs/enrich-person
"""

from __future__ import annotations

import httpx
import structlog

from core.config import settings

logger = structlog.get_logger()

_BASE_URL = "https://api.prospeo.io"
_TIMEOUT = 20.0


class ProspeoClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=_BASE_URL,
            headers={
                "X-KEY": settings.PROSPEO_API_KEY or "",
                "Content-Type": "application/json",
            },
            timeout=_TIMEOUT,
        )

    async def find_email(
        self,
        first_name: str,
        last_name: str,
        domain: str,
    ) -> tuple[str, float] | None:
        """
        Busca o e-mail corporativo via Enrich Person (POST /enrich-person).

        Retorna (email, confidence) ou None se não encontrado.
        confidence: 1.0 se VERIFIED, 0.5 caso contrário.
        """
        try:
            resp = await self._client.post(
                "/enrich-person",
                json={
                    "only_verified_email": False,
                    "enrich_mobile": False,
                    "data": {
                        "first_name": first_name,
                        "last_name": last_name,
                        "company_website": domain,
                    },
                },
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("error"):
                error_code = data.get("error_code", "UNKNOWN")
                logger.info("prospeo.no_match", error_code=error_code, domain=domain)
                return None
            person = data.get("person") or {}
            email_obj = person.get("email") or {}
            email: str | None = email_obj.get("email")
            status: str = email_obj.get("status", "")
            revealed: bool = email_obj.get("revealed", False)
            if not email or not revealed:
                return None
            confidence = 1.0 if status == "VERIFIED" else 0.5
            logger.info(
                "prospeo.found",
                email=email,
                domain=domain,
                status=status,
                confidence=confidence,
            )
            return email, confidence
        except httpx.HTTPStatusError as exc:
            logger.warning("prospeo.error", status=exc.response.status_code, domain=domain)
            return None
        except Exception as exc:  # noqa: BLE001
            logger.error("prospeo.exception", error=str(exc), domain=domain)
            return None

    async def aclose(self) -> None:
        await self._client.aclose()
