"""
integrations/email_finders/prospeo.py

Cliente HTTP assíncrono para Prospeo — email finder por nome + domínio.

Base URL: https://api.prospeo.io/v1
Auth:     X-KEY header
"""

from __future__ import annotations

import httpx
import structlog

from core.config import settings

logger = structlog.get_logger()

_BASE_URL = "https://api.prospeo.io/v1"
_TIMEOUT = 20.0


class ProspeoClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=_BASE_URL,
            headers={"X-KEY": settings.PROSPEO_API_KEY or ""},
            timeout=_TIMEOUT,
        )

    async def find_email(
        self,
        first_name: str,
        last_name: str,
        domain: str,
    ) -> tuple[str, float] | None:
        """
        Busca o e-mail corporativo pelo nome e domínio da empresa.

        Retorna (email, confidence) ou None se não encontrado.
        confidence está entre 0.0 e 1.0 (Prospeo retorna score 0-100).
        """
        try:
            resp = await self._client.post(
                "/email-finder",
                json={
                    "first_name": first_name,
                    "last_name": last_name,
                    "company": domain,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            email: str | None = data.get("response", {}).get("email")
            score: int = int(data.get("response", {}).get("accept_all_score", 0) or 0)
            if not email:
                return None
            logger.info("prospeo.found", email=email, domain=domain, score=score)
            return email, score / 100.0
        except httpx.HTTPStatusError as exc:
            logger.warning("prospeo.error", status=exc.response.status_code, domain=domain)
            return None
        except Exception as exc:  # noqa: BLE001
            logger.error("prospeo.exception", error=str(exc), domain=domain)
            return None

    async def aclose(self) -> None:
        await self._client.aclose()
