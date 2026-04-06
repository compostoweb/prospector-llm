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

import asyncio

import httpx
import structlog

logger = structlog.get_logger()

_LINKEDIN_API_BASE = "https://api.linkedin.com/v2"
_LINKEDIN_REST_BASE = "https://api.linkedin.com/rest"
_LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
_LINKEDIN_VERSION = "202602"  # Linkedin-Version header para Videos API
_VIDEO_CHUNK_SIZE = 4 * 1024 * 1024  # 4 MB por chunk


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

    async def __aenter__(self) -> LinkedInClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self._client.aclose()

    # ── Posts ─────────────────────────────────────────────────────────

    async def create_post(
        self,
        text: str,
        media_urn: str | None = None,
        media_category: str = "NONE",
    ) -> dict:
        """Publica post imediatamente (lifecycleState=PUBLISHED)."""
        payload = self.build_ugc_post_payload(
            person_urn=self._person_urn,
            text=text,
            media_urn=media_urn,
            media_category=media_category,
        )
        response = await self._client.post("/ugcPosts", json=payload)
        self._raise_for_status(response)
        logger.info("linkedin.post_published", person_urn=self._person_urn)
        return response.json()

    async def schedule_post(
        self,
        text: str,
        publish_timestamp_ms: int,
        media_urn: str | None = None,
        media_category: str = "NONE",
    ) -> dict:
        """
        Agenda post para publicacao futura (lifecycleState=DRAFT + scheduledPublishTime).

        publish_timestamp_ms: Unix timestamp em milissegundos.
        LinkedIn aceita agendamento de ate 6 meses no futuro.
        """
        payload = self.build_ugc_post_payload(
            person_urn=self._person_urn,
            text=text,
            scheduled_ms=publish_timestamp_ms,
            media_urn=media_urn,
            media_category=media_category,
        )
        response = await self._client.post("/ugcPosts", json=payload)
        self._raise_for_status(response)
        logger.info(
            "linkedin.post_scheduled",
            person_urn=self._person_urn,
            publish_at_ms=publish_timestamp_ms,
        )
        return response.json()

    # ── Upload de mídia ───────────────────────────────────────────────

    async def upload_image(self, image_bytes: bytes) -> str:
        """
        Faz upload de imagem via Vector Assets API.

        Retorna urn:li:digitalmediaAsset:XXX
        """
        # 1. Register upload
        register_payload = {
            "registerUploadRequest": {
                "owner": self._person_urn,
                "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                "serviceRelationships": [
                    {
                        "relationshipType": "OWNER",
                        "identifier": "urn:li:userGeneratedContent",
                    }
                ],
            }
        }
        reg_response = await self._client.post(
            "/assets?action=registerUpload",
            json=register_payload,
        )
        self._raise_for_status(reg_response)
        reg_data = reg_response.json()

        upload_url: str = reg_data["value"]["uploadMechanism"][
            "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
        ]["uploadUrl"]
        asset_urn: str = reg_data["value"]["asset"]

        # 2. PUT imagem binária
        async with httpx.AsyncClient(timeout=60.0) as raw_client:
            put_response = await raw_client.put(
                upload_url,
                content=image_bytes,
                headers={"Content-Type": "application/octet-stream"},
            )
        if put_response.status_code not in (200, 201):
            raise LinkedInClientError(put_response.status_code, put_response.text)

        logger.info("linkedin.image_uploaded", asset_urn=asset_urn)
        return asset_urn

    async def upload_video(self, video_bytes: bytes) -> str:
        """
        Faz upload de vídeo via Videos API (nova, substituição do Assets API).

        Retorna urn:li:video:XXX
        """
        file_size = len(video_bytes)

        # 1. Initialize upload
        async with httpx.AsyncClient(
            base_url=_LINKEDIN_REST_BASE,
            headers={
                "Authorization": self._client.headers["Authorization"],
                "Linkedin-Version": _LINKEDIN_VERSION,
                "X-Restli-Protocol-Version": "2.0.0",
                "Content-Type": "application/json",
            },
            timeout=60.0,
        ) as rest_client:
            init_response = await rest_client.post(
                "/videos?action=initializeUpload",
                json={
                    "initializeUploadRequest": {
                        "owner": self._person_urn,
                        "fileSizeBytes": file_size,
                        "uploadCaptions": False,
                        "uploadThumbnail": False,
                    }
                },
            )
            self._raise_for_status(init_response)
            init_data = init_response.json()["value"]

            video_urn: str = init_data["video"]
            upload_token: str = init_data.get("uploadToken", "")
            upload_instructions: list[dict] = init_data["uploadInstructions"]

            # 2. PUT cada parte (chunks de 4 MB)
            etags: list[str] = []
            async with httpx.AsyncClient(timeout=300.0) as raw_client:
                for instruction in upload_instructions:
                    first_byte: int = instruction["firstByte"]
                    last_byte: int = instruction["lastByte"]
                    chunk = video_bytes[first_byte : last_byte + 1]
                    put_resp = await raw_client.put(
                        instruction["uploadUrl"],
                        content=chunk,
                        headers={"Content-Type": "application/octet-stream"},
                    )
                    if put_resp.status_code not in (200, 201):
                        raise LinkedInClientError(put_resp.status_code, put_resp.text)
                    etag = put_resp.headers.get("ETag", put_resp.headers.get("etag", ""))
                    etags.append(etag.strip('"'))

            # 3. Finalize upload
            final_response = await rest_client.post(
                "/videos?action=finalizeUpload",
                json={
                    "finalizeUploadRequest": {
                        "video": video_urn,
                        "uploadToken": upload_token,
                        "uploadedPartIds": etags,
                    }
                },
            )
            self._raise_for_status(final_response)

            # 4. Poll até AVAILABLE (timeout 90s)
            encoded_urn = video_urn.replace(":", "%3A")
            for _ in range(18):  # 18 * 5s = 90s
                await asyncio.sleep(5)
                poll_resp = await rest_client.get(f"/videos/{encoded_urn}")
                if poll_resp.status_code == 200:
                    video_status = poll_resp.json().get("status", "")
                    if video_status == "AVAILABLE":
                        break
                    if video_status == "PROCESSING_FAILED":
                        raise LinkedInClientError(0, f"Video processing failed: {poll_resp.text}")
            else:
                logger.warning("linkedin.video_poll_timeout", video_urn=video_urn)

        logger.info("linkedin.video_uploaded", video_urn=video_urn)
        return video_urn

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

    async def delete_published_post(self, post_urn: str) -> bool:
        """
        Deleta um post ja publicado (lifecycleState=PUBLISHED) do LinkedIn.

        post_urn: urn:li:ugcPost:{id}
        Retorna True se deletado com sucesso (HTTP 204).
        Requer scope w_member_social.
        """
        encoded_urn = post_urn.replace(":", "%3A")
        response = await self._client.delete(f"/ugcPosts/{encoded_urn}")
        self._raise_for_status(response)
        logger.info("linkedin.post_deleted", post_urn=post_urn)
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
        Busca dados basicos do perfil autenticado via OpenID Connect userinfo.
        Retorna: sub (person_id), given_name, family_name, name, email.

        Compativel com scopes: openid profile email.
        """
        async with httpx.AsyncClient(
            base_url=_LINKEDIN_API_BASE,
            headers={
                "Authorization": f"Bearer {access_token}",
            },
            timeout=15.0,
        ) as client:
            response = await client.get("/userinfo")
            if response.status_code != 200:
                raise LinkedInClientError(response.status_code, response.text)
            return response.json()

    # ── Payload builder ───────────────────────────────────────────────

    @staticmethod
    def build_ugc_post_payload(
        person_urn: str,
        text: str,
        scheduled_ms: int | None = None,
        media_urn: str | None = None,
        media_category: str = "NONE",
    ) -> dict:
        """
        Monta o payload para POST /ugcPosts.

        Se scheduled_ms for fornecido, cria post agendado (DRAFT).
        Caso contrario, publica imediatamente (PUBLISHED).
        Se media_urn fornecido, adiciona media[] ao shareContent.
        """
        lifecycle_state = "DRAFT" if scheduled_ms is not None else "PUBLISHED"

        share_content: dict = {
            "shareCommentary": {"text": text},
            "shareMediaCategory": media_category if media_urn else "NONE",
        }

        if media_urn:
            share_content["media"] = [
                {
                    "status": "READY",
                    "media": media_urn,
                }
            ]

        payload: dict = {
            "author": person_urn,
            "lifecycleState": lifecycle_state,
            "specificContent": {
                "com.linkedin.ugc.ShareContent": share_content,
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }

        if scheduled_ms is not None:
            payload["scheduledPublishTime"] = scheduled_ms

        return payload

    # ── Internal ──────────────────────────────────────────────────────

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        if response.status_code >= 400:
            raise LinkedInClientError(response.status_code, response.text)
