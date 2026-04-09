"""
integrations/sendpulse_client.py

Cliente HTTP assíncrono para SendPulse.
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from core.config import settings
from core.redis_client import RedisClient, redis_client

logger = structlog.get_logger()


class SendPulseClientError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class SendPulseClient:
    BASE_URL = settings.SENDPULSE_BASE_URL
    _TOKEN_CACHE_KEY = "sendpulse:oauth:access_token"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        redis: RedisClient | None = None,
    ) -> None:
        self._api_key = api_key or settings.SENDPULSE_API_KEY
        self._client_id = client_id or settings.SENDPULSE_CLIENT_ID
        self._client_secret = client_secret or settings.SENDPULSE_CLIENT_SECRET
        self._redis = redis or redis_client
        self._client = httpx.AsyncClient(base_url=self.BASE_URL, timeout=20.0)

    @property
    def uses_static_token(self) -> bool:
        return bool(self._api_key)

    async def get_access_token(self, *, force_refresh: bool = False) -> str:
        if self.uses_static_token:
            return self._api_key

        if not self._client_id or not self._client_secret:
            raise SendPulseClientError(
                "Credenciais do SendPulse não configuradas. Informe SENDPULSE_API_KEY ou SENDPULSE_CLIENT_ID/SENDPULSE_CLIENT_SECRET"
            )

        if not force_refresh:
            cached = await self._redis.get_cache(self._TOKEN_CACHE_KEY)
            if cached:
                return cached

        response = await self._client.post(
            "/oauth/access_token",
            data={
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
            },
        )
        if response.is_error:
            raise SendPulseClientError(
                f"Falha ao autenticar no SendPulse: {response.text[:300]}",
                status_code=response.status_code,
            )

        payload = response.json()
        access_token = payload.get("access_token")
        expires_in = int(payload.get("expires_in", 3600))
        if not access_token:
            raise SendPulseClientError("Resposta do SendPulse sem access_token")

        await self._redis.set_cache(
            self._TOKEN_CACHE_KEY,
            access_token,
            max(expires_in - 60, 60),
        )
        return access_token

    async def _get_auth_headers(self, *, force_refresh: bool = False) -> dict[str, str]:
        token = await self.get_access_token(force_refresh=force_refresh)
        return {"Authorization": f"Bearer {token}"}

    async def add_subscriber_to_list(
        self,
        *,
        list_id: str,
        email: str,
        name: str,
        variables: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await self._request_add_subscriber(
            list_id=list_id,
            email=email,
            name=name,
            variables=variables,
            retry_on_unauthorized=True,
        )

    async def _request_add_subscriber(
        self,
        *,
        list_id: str,
        email: str,
        name: str,
        variables: dict[str, Any] | None,
        retry_on_unauthorized: bool,
    ) -> dict[str, Any]:
        payload = {
            "emails": [
                {
                    "email": email,
                    "variables": {
                        "name": name,
                        **(variables or {}),
                    },
                }
            ]
        }
        response = await self._client.post(
            f"/addressbooks/{list_id}/emails",
            json=payload,
            headers=await self._get_auth_headers(force_refresh=not retry_on_unauthorized),
        )

        if (
            response.status_code == httpx.codes.UNAUTHORIZED
            and retry_on_unauthorized
            and not self.uses_static_token
        ):
            await self._redis.delete(self._TOKEN_CACHE_KEY)
            logger.info("sendpulse.token_refresh_retry")
            return await self._request_add_subscriber(
                list_id=list_id,
                email=email,
                name=name,
                variables=variables,
                retry_on_unauthorized=False,
            )

        if response.is_error:
            raise SendPulseClientError(
                f"Falha ao adicionar subscriber à lista {list_id}: {response.text[:300]}",
                status_code=response.status_code,
            )

        data = response.json()
        logger.info("sendpulse.subscriber_synced", list_id=list_id, email=email)
        return data
