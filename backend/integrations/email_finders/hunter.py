"""
integrations/email_finders/hunter.py

Cliente HTTP assíncrono para Hunter.io — email finder por nome + domínio.

Base URL: https://api.hunter.io/v2
Auth:     api_key query param
"""

from __future__ import annotations

import httpx
import structlog

from core.config import settings

logger = structlog.get_logger()

_BASE_URL = "https://api.hunter.io/v2"
_TIMEOUT = 20.0


class HunterClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=_BASE_URL,
            timeout=_TIMEOUT,
        )
        self._api_key = settings.HUNTER_API_KEY or ""

    async def find_email(
        self,
        first_name: str,
        last_name: str,
        domain: str,
    ) -> tuple[str, float] | None:
        """
        Busca o e-mail corporativo via Hunter /email-finder.

        Retorna (email, confidence) ou None se não encontrado.
        confidence é o campo 'score' do Hunter (0-100) normalizado para 0.0–1.0.
        """
        try:
            resp = await self._client.get(
                "/email-finder",
                params={
                    "domain": domain,
                    "first_name": first_name,
                    "last_name": last_name,
                    "api_key": self._api_key,
                },
            )
            resp.raise_for_status()
            data = resp.json().get("data", {})
            email: str | None = data.get("email")
            score: int = int(data.get("score", 0) or 0)
            if not email:
                return None
            logger.info("hunter.found", email=email, domain=domain, score=score)
            return email, score / 100.0
        except httpx.HTTPStatusError as exc:
            logger.warning("hunter.error", status=exc.response.status_code, domain=domain)
            return None
        except Exception as exc:  # noqa: BLE001
            logger.error("hunter.exception", error=str(exc), domain=domain)
            return None

    async def aclose(self) -> None:
        await self._client.aclose()
