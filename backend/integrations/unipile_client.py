"""
integrations/unipile_client.py

Cliente HTTP assíncrono para a Unipile API.

Responsabilidades:
  - Enviar mensagens LinkedIn (connect request + DM texto + DM voice note)
  - Enviar emails via Gmail
  - Buscar perfil LinkedIn por URL (para obter linkedin_profile_id)
  - Expor tipos de resposta tipados

Base URL: https://api2.unipile.com:13246/api/v1
Auth:     X-API-KEY header

Documentação: https://developer.unipile.com
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx
import structlog

from core.config import settings

logger = structlog.get_logger()

_BASE_URL = settings.UNIPILE_BASE_URL
_TIMEOUT = 30.0


@dataclass
class SendResult:
    """Resultado de um envio via Unipile."""
    message_id: str
    success: bool


@dataclass
class LinkedInProfile:
    """Dados básicos de perfil LinkedIn retornados pela Unipile."""
    profile_id: str
    name: str
    headline: str | None
    company: str | None


class UnipileClient:
    """
    Wrapper sobre a Unipile REST API.
    Instanciar uma vez e reusar (httpx.AsyncClient é reutilizável).
    """

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=_BASE_URL,
            headers={
                "X-API-KEY": settings.UNIPILE_API_KEY or "",
                "accept": "application/json",
                "content-type": "application/json",
            },
            timeout=_TIMEOUT,
        )

    # ── LinkedIn ──────────────────────────────────────────────────────

    async def send_linkedin_connect(
        self,
        account_id: str,
        linkedin_profile_id: str,
        message: str,
    ) -> SendResult:
        """Envia um connection request com nota personalizada."""
        payload = {
            "account_id": account_id,
            "linkedin_profile_id": linkedin_profile_id,
            "message": message,
        }
        response = await self._client.post("/linkedin/invitations", json=payload)
        response.raise_for_status()
        data = response.json()
        msg_id: str = data.get("id", "")
        logger.info(
            "unipile.linkedin_connect.sent",
            profile_id=linkedin_profile_id,
            message_id=msg_id,
        )
        return SendResult(message_id=msg_id, success=True)

    async def send_linkedin_dm(
        self,
        account_id: str,
        linkedin_profile_id: str,
        message: str,
    ) -> SendResult:
        """Envia uma DM de texto para um contato LinkedIn."""
        payload = {
            "account_id": account_id,
            "attendees_ids": [linkedin_profile_id],
            "text": message,
        }
        response = await self._client.post("/chats/messages", json=payload)
        response.raise_for_status()
        data = response.json()
        msg_id: str = data.get("id", "")
        logger.info(
            "unipile.linkedin_dm.sent",
            profile_id=linkedin_profile_id,
            message_id=msg_id,
        )
        return SendResult(message_id=msg_id, success=True)

    async def send_linkedin_voice_note(
        self,
        account_id: str,
        linkedin_profile_id: str,
        audio_url: str,
    ) -> SendResult:
        """
        Envia uma voice note MP3 pré-gerada para um contato LinkedIn.
        O audio_url deve ser acessível publicamente (ex: S3 ou URL pública).
        """
        payload = {
            "account_id": account_id,
            "attendees_ids": [linkedin_profile_id],
            "audio_url": audio_url,
        }
        response = await self._client.post("/chats/messages/audio", json=payload)
        response.raise_for_status()
        data = response.json()
        msg_id: str = data.get("id", "")
        logger.info(
            "unipile.linkedin_voice.sent",
            profile_id=linkedin_profile_id,
            message_id=msg_id,
        )
        return SendResult(message_id=msg_id, success=True)

    # ── Email (Gmail via Unipile) ─────────────────────────────────────

    async def send_email(
        self,
        account_id: str,
        to_email: str,
        subject: str,
        body_html: str,
        reply_to_message_id: str | None = None,
    ) -> SendResult:
        """Envia um email via conta Gmail conectada na Unipile."""
        payload: dict = {
            "account_id": account_id,
            "to": [{"email": to_email}],
            "subject": subject,
            "body": body_html,
        }
        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id

        response = await self._client.post("/emails", json=payload)
        response.raise_for_status()
        data = response.json()
        msg_id: str = data.get("id", "")
        logger.info(
            "unipile.email.sent",
            to=to_email,
            message_id=msg_id,
        )
        return SendResult(message_id=msg_id, success=True)

    # ── Perfil LinkedIn ───────────────────────────────────────────────

    async def get_linkedin_profile(
        self,
        account_id: str,
        linkedin_url: str,
    ) -> LinkedInProfile | None:
        """
        Busca dados básicos de um perfil LinkedIn por URL.
        Retorna None se o perfil não for encontrado.
        """
        params = {"account_id": account_id, "url": linkedin_url}
        response = await self._client.get("/linkedin/profiles", params=params)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()
        return LinkedInProfile(
            profile_id=data.get("public_id", ""),
            name=data.get("name", ""),
            headline=data.get("headline"),
            company=data.get("current_company"),
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "UnipileClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()


# Singleton para uso direto sem contexto
unipile_client = UnipileClient()
