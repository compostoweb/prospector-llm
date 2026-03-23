"""
integrations/email_finders/apollo.py

Cliente HTTP assíncrono para Apollo.io — email finder por URL do LinkedIn.

Base URL: https://api.apollo.io/v1
Auth:     api_key no corpo JSON
"""

from __future__ import annotations

import httpx
import structlog

from core.config import settings

logger = structlog.get_logger()

_BASE_URL = "https://api.apollo.io/v1"
_TIMEOUT = 20.0


class ApolloClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=_BASE_URL,
            headers={"Content-Type": "application/json"},
            timeout=_TIMEOUT,
        )
        self._api_key = settings.APOLLO_API_KEY or ""

    async def find_email(
        self,
        linkedin_url: str,
    ) -> tuple[str, float] | None:
        """
        Busca o e-mail do lead via URL do LinkedIn usando Apollo /people/match.

        Retorna (email, confidence) ou None se não encontrado.
        confidence: 1.0 se email confirmado, 0.7 se predicted, 0.0 se ausente.
        """
        try:
            resp = await self._client.post(
                "/people/match",
                json={
                    "api_key": self._api_key,
                    "linkedin_url": linkedin_url,
                    "reveal_personal_emails": False,
                },
            )
            resp.raise_for_status()
            person = resp.json().get("person") or {}
            email: str | None = person.get("email")
            email_status: str = person.get("email_status", "")
            if not email:
                return None
            confidence = 1.0 if email_status == "verified" else 0.7
            logger.info("apollo.found", email=email, linkedin_url=linkedin_url, status=email_status)
            return email, confidence
        except httpx.HTTPStatusError as exc:
            logger.warning("apollo.error", status=exc.response.status_code, linkedin_url=linkedin_url)
            return None
        except Exception as exc:  # noqa: BLE001
            logger.error("apollo.exception", error=str(exc), linkedin_url=linkedin_url)
            return None

    async def aclose(self) -> None:
        await self._client.aclose()
