"""
integrations/email_finders/prospeo.py

Cliente HTTP assíncrono para Prospeo — Enrich Person API (v2, mar/2026).

Base URL: https://api.prospeo.io
Auth:     X-KEY header
Docs:     https://prospeo.io/api-docs/enrich-person
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx
import structlog

from core.config import settings

logger = structlog.get_logger()

_BASE_URL = "https://api.prospeo.io"
_TIMEOUT = 20.0


@dataclass(frozen=True)
class ProspeoPersonEnrichment:
    email: str | None
    email_status: str | None
    email_revealed: bool
    mobile: str | None
    mobile_status: str | None
    raw_payload: dict[str, object]

    @property
    def email_confidence(self) -> float:
        return 1.0 if (self.email_status or "").upper() == "VERIFIED" else 0.5


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

    async def enrich_person(
        self,
        first_name: str,
        last_name: str,
        domain: str,
        *,
        include_mobile: bool = False,
    ) -> ProspeoPersonEnrichment | None:
        """Busca dados estruturados da pessoa via Enrich Person."""
        try:
            resp = await self._client.post(
                "/enrich-person",
                json={
                    "only_verified_email": False,
                    "enrich_mobile": include_mobile,
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
            mobile_obj = person.get("mobile") or {}
            email = email_obj.get("email")
            email_revealed = bool(email_obj.get("revealed", False))
            if email and not email_revealed:
                email = None

            mobile = mobile_obj.get("number") or mobile_obj.get("phone") or mobile_obj.get("mobile")
            enrichment = ProspeoPersonEnrichment(
                email=email,
                email_status=email_obj.get("status"),
                email_revealed=email_revealed,
                mobile=mobile,
                mobile_status=mobile_obj.get("status"),
                raw_payload=person,
            )
            if not enrichment.email and not enrichment.mobile:
                return None

            logger.info(
                "prospeo.enriched_person",
                domain=domain,
                email=enrichment.email,
                email_status=enrichment.email_status,
                mobile_status=enrichment.mobile_status,
            )
            return enrichment
        except httpx.HTTPStatusError as exc:
            logger.warning("prospeo.error", status=exc.response.status_code, domain=domain)
            return None
        except Exception as exc:  # noqa: BLE001
            logger.error("prospeo.exception", error=str(exc), domain=domain)
            return None

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
        enrichment = await self.enrich_person(first_name, last_name, domain, include_mobile=False)
        if enrichment is None or not enrichment.email:
            return None
        return enrichment.email, enrichment.email_confidence

    async def aclose(self) -> None:
        await self._client.aclose()
