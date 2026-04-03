"""
services/content/linkedin_client.py

Cliente LinkedIn API para o modulo Content Hub.

Responsavel por publicar e agendar posts via UGC Posts endpoint
(Share on LinkedIn product).

Uso:
    client = LinkedInClient(access_token=token, person_urn="urn:li:person:XYZ")
    result = await client.create_post("Texto do post...")
    result = await client.schedule_post("Texto...", publish_timestamp_ms=1234567890000)
"""

from __future__ import annotations

import structlog
import httpx

logger = structlog.get_logger()

_LINKEDIN_API_BASE = "https://api.linkedin.com/v2"
_LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"


class LinkedInClientError(Exception):
    """Erro retornado pela LinkedIn API."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"LinkedIn API error {status_code}: {detail}")


class LinkedInClient:
    """
    Cliente httpx para a LinkedIn API (Share on LinkedIn product).

    Instanciar por request/task com o access_token do tenant.
    """

    def __init__(self, access_token: str, person_urn: str) -> None:
        self._person_urn = person_urn
        self._client = httpx.AsyncClient(
            base_url=_LINKEDIN_API_BASE,
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-Restli-Protocol-Version": "2.0.0",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    async def __aenter__(self) -> "LinkedInClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self._client.aclose()

    # ── Posts ─────────────────────────────────────────────────────────

    async def create_post(self, text: str) -> dict:
        """Publica post imediatamente (lifecycleState=PUBLISHED)."""
        payload = self.build_ugc_post_payload(
            person_urn=self._person_urn,
            text=text,
        )
        response = await self._client.post("/ugcPosts", json=payload)
        self._raise_for_status(response)
        logger.info("linkedin.post_published", person_urn=self._person_urn)
        return response.json()

    async def schedule_post(self, text: str, publish_timestamp_ms: int) -> dict:
        """
        Agenda post para publicacao futura (lifecycleState=DRAFT + scheduledPublishTime).

        publish_timestamp_ms: Unix timestamp em milissegundos.
        LinkedIn aceita agendamento de ate 6 meses no futuro.
        """
        payload = self.build_ugc_post_payload(
            person_urn=self._person_urn,
            text=text,
            scheduled_ms=publish_timestamp_ms,
        )
        response = await self._client.post("/ugcPosts", json=payload)
        self._raise_for_status(response)
        logger.info(
            "linkedin.post_scheduled",
            person_urn=self._person_urn,
            publish_at_ms=publish_timestamp_ms,
        )
        return response.json()

    async def cancel_scheduled_post(self, post_urn: str) -> bool:
        """
        Cancela um post agendado (DRAFT → DELETED).

        post_urn: urn:li:ugcPost:{id}
        Retorna True se cancelado com sucesso.
        """
        encoded_urn = post_urn.replace(":", "%3A")
        payload = {"patch": {"$set": {"lifecycleState": "DELETED"}}}
        response = await self._client.post(
            f"/ugcPosts/{encoded_urn}",
            json=payload,
            headers={"X-RestLi-Method": "PARTIAL_UPDATE"},
        )
        self._raise_for_status(response)
        logger.info("linkedin.post_cancelled", post_urn=post_urn)
        return True

    async def get_post(self, post_urn: str) -> dict:
        """Busca detalhes de um post UGC."""
        encoded_urn = post_urn.replace(":", "%3A")
        response = await self._client.get(f"/ugcPosts/{encoded_urn}")
        self._raise_for_status(response)
        return response.json()

    # ── OAuth helpers (sem instancia autenticada) ─────────────────────

    @staticmethod
    async def exchange_code_for_token(
        code: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
    ) -> dict:
        """
        Troca authorization_code por access_token + refresh_token.
        Retorna o JSON completo do token endpoint do LinkedIn.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                _LINKEDIN_TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if response.status_code != 200:
                raise LinkedInClientError(response.status_code, response.text)
            return response.json()

    @staticmethod
    async def get_profile(access_token: str) -> dict:
        """
        Busca dados basicos do perfil autenticado (r_liteprofile).
        Retorna: id (person_id), localizedFirstName, localizedLastName.
        """
        async with httpx.AsyncClient(
            base_url=_LINKEDIN_API_BASE,
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-Restli-Protocol-Version": "2.0.0",
            },
            timeout=15.0,
        ) as client:
            response = await client.get("/me")
            if response.status_code != 200:
                raise LinkedInClientError(response.status_code, response.text)
            return response.json()

    # ── Payload builder ───────────────────────────────────────────────

    @staticmethod
    def build_ugc_post_payload(
        person_urn: str,
        text: str,
        scheduled_ms: int | None = None,
    ) -> dict:
        """
        Monta o payload para POST /ugcPosts.

        Se scheduled_ms for fornecido, cria post agendado (DRAFT).
        Caso contrario, publica imediatamente (PUBLISHED).
        """
        lifecycle_state = "DRAFT" if scheduled_ms is not None else "PUBLISHED"

        payload: dict = {
            "author": person_urn,
            "lifecycleState": lifecycle_state,
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            },
        }

        if scheduled_ms is not None:
            payload["scheduledPublishTime"] = scheduled_ms

        return payload

    # ── Internal ──────────────────────────────────────────────────────

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        if response.status_code >= 400:
            raise LinkedInClientError(response.status_code, response.text)
