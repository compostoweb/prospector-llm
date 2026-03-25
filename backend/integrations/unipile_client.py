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

from dataclasses import dataclass, field

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


@dataclass
class ChatAttendee:
    """Participante de um chat Unipile."""
    id: str
    name: str
    profile_url: str | None = None


@dataclass
class ChatSummary:
    """Resumo de uma conversa na listagem."""
    chat_id: str
    attendees: list[ChatAttendee] = field(default_factory=list)
    last_message_text: str | None = None
    last_message_at: str | None = None
    unread_count: int = 0
    account_id: str = ""


@dataclass
class ChatMessage:
    """Uma mensagem dentro de um chat."""
    id: str
    sender_id: str
    sender_name: str
    text: str
    timestamp: str
    is_own: bool = False
    attachments: list[dict] = field(default_factory=list)


@dataclass
class ChatDetail:
    """Detalhes de uma conversa."""
    chat_id: str
    attendees: list[ChatAttendee] = field(default_factory=list)
    account_id: str = ""


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

    async def get_relation_status(
        self,
        account_id: str,
        linkedin_profile_id: str,
    ) -> str | None:
        """
        Verifica o status da relação com um perfil LinkedIn.
        Retorna "CONNECTED" | "PENDING" | None.
        """
        params = {
            "account_id": account_id,
            "linkedin_profile_id": linkedin_profile_id,
        }
        try:
            response = await self._client.get("/linkedin/relations", params=params)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()
            return data.get("status") or None
        except httpx.HTTPError:
            logger.warning(
                "unipile.relation_status.error",
                profile_id=linkedin_profile_id,
            )
            return None

    # ── Chats (UniBox) ────────────────────────────────────────────────

    async def list_chats(
        self,
        account_id: str,
        cursor: str | None = None,
        limit: int = 20,
    ) -> dict:
        """
        Lista conversas LinkedIn.
        Retorna dict com 'items' (list[ChatSummary]) e 'cursor' (próxima página).
        """
        params: dict = {"account_id": account_id, "limit": limit}
        if cursor:
            params["cursor"] = cursor

        response = await self._client.get("/chats", params=params)
        response.raise_for_status()
        data = response.json()

        items: list[ChatSummary] = []
        for chat in data.get("items", []):
            attendees = [
                ChatAttendee(
                    id=att.get("id", ""),
                    name=att.get("name", ""),
                    profile_url=att.get("profile_url"),
                )
                for att in chat.get("attendees", [])
            ]
            items.append(
                ChatSummary(
                    chat_id=chat.get("id", ""),
                    attendees=attendees,
                    last_message_text=chat.get("last_message", {}).get("text"),
                    last_message_at=chat.get("last_message", {}).get("timestamp"),
                    unread_count=chat.get("unread_count", 0),
                    account_id=account_id,
                )
            )

        return {
            "items": items,
            "cursor": data.get("cursor"),
        }

    async def get_chat_messages(
        self,
        chat_id: str,
        cursor: str | None = None,
        limit: int = 30,
    ) -> dict:
        """
        Obtém mensagens de um chat específico.
        Retorna dict com 'items' (list[ChatMessage]) e 'cursor'.
        """
        params: dict = {"limit": limit}
        if cursor:
            params["cursor"] = cursor

        response = await self._client.get(f"/chats/{chat_id}/messages", params=params)
        response.raise_for_status()
        data = response.json()

        items: list[ChatMessage] = []
        for msg in data.get("items", []):
            items.append(
                ChatMessage(
                    id=msg.get("id", ""),
                    sender_id=msg.get("sender_id", ""),
                    sender_name=msg.get("sender_name", ""),
                    text=msg.get("text", ""),
                    timestamp=msg.get("timestamp", ""),
                    is_own=msg.get("is_own", False),
                    attachments=msg.get("attachments", []),
                )
            )

        return {
            "items": items,
            "cursor": data.get("cursor"),
        }

    async def get_chat(self, chat_id: str) -> ChatDetail | None:
        """Obtém detalhes de uma conversa."""
        try:
            response = await self._client.get(f"/chats/{chat_id}")
            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()
            attendees = [
                ChatAttendee(
                    id=att.get("id", ""),
                    name=att.get("name", ""),
                    profile_url=att.get("profile_url"),
                )
                for att in data.get("attendees", [])
            ]
            return ChatDetail(
                chat_id=data.get("id", ""),
                attendees=attendees,
                account_id=data.get("account_id", ""),
            )
        except httpx.HTTPError:
            logger.warning("unipile.get_chat.error", chat_id=chat_id)
            return None

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "UnipileClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()


# Singleton para uso direto sem contexto
unipile_client = UnipileClient()
