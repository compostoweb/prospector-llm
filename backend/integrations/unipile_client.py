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

import asyncio
import json
from dataclasses import dataclass, field

import httpx
import structlog

from core.config import settings

logger = structlog.get_logger()

_BASE_URL = settings.UNIPILE_BASE_URL
_TIMEOUT = 30.0
_PROFILE_CACHE_TTL = 86400  # 24h


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
    profile_picture_url: str | None = None


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

    async def _get_user_profile_cached(
        self,
        provider_id: str,
        account_id: str,
    ) -> dict:
        """
        Busca perfil de usuário Unipile com cache Redis.
        Retorna dict com first_name, last_name, profile_picture_url, public_identifier.
        """
        from core.redis_client import redis_client

        cache_key = f"unipile:profile:{provider_id}"
        cached = await redis_client.get(cache_key)
        if cached:
            try:
                return json.loads(cached)
            except (json.JSONDecodeError, TypeError):
                pass

        try:
            response = await self._client.get(
                f"/users/{provider_id}",
                params={"account_id": account_id},
            )
            if response.status_code != 200:
                logger.debug(
                    "unipile.user_profile.not_found",
                    provider_id=provider_id,
                    status=response.status_code,
                )
                return {}
            data = response.json()
            profile = {
                "first_name": data.get("first_name", ""),
                "last_name": data.get("last_name", ""),
                "profile_picture_url": data.get("profile_picture_url"),
                "public_identifier": data.get("public_identifier", ""),
            }
            await redis_client.set(
                cache_key,
                json.dumps(profile),
                ex=_PROFILE_CACHE_TTL,
            )
            return profile
        except Exception:
            logger.debug("unipile.user_profile.error", provider_id=provider_id)
            return {}

    async def _resolve_attendee(
        self,
        provider_id: str,
        account_id: str,
    ) -> ChatAttendee:
        """Resolve dados de um attendee via /users/{id}."""
        profile = await self._get_user_profile_cached(provider_id, account_id)
        first = profile.get("first_name", "")
        last = profile.get("last_name", "")
        name = f"{first} {last}".strip() if (first or last) else ""
        public_id = profile.get("public_identifier", "")
        profile_url = f"https://www.linkedin.com/in/{public_id}" if public_id else None

        return ChatAttendee(
            id=provider_id,
            name=name,
            profile_url=profile_url,
            profile_picture_url=profile.get("profile_picture_url"),
        )

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

        raw_items = data.get("items", [])

        # Collect unique attendee IDs and resolve profiles in parallel
        attendee_ids = {
            chat.get("attendee_provider_id", "")
            for chat in raw_items
            if chat.get("attendee_provider_id")
        }
        profiles: dict[str, ChatAttendee] = {}
        if attendee_ids:
            resolved = await asyncio.gather(
                *(self._resolve_attendee(aid, account_id) for aid in attendee_ids),
                return_exceptions=True,
            )
            for att in resolved:
                if isinstance(att, ChatAttendee):
                    profiles[att.id] = att

        items: list[ChatSummary] = []
        for chat in raw_items:
            att_id = chat.get("attendee_provider_id", "")
            attendee = profiles.get(att_id)
            attendees = [attendee] if attendee else (
                [ChatAttendee(id=att_id, name="")] if att_id else []
            )

            last_msg = chat.get("lastMessage") or chat.get("last_message") or {}
            items.append(
                ChatSummary(
                    chat_id=chat.get("id", ""),
                    attendees=attendees,
                    last_message_text=last_msg.get("text") if isinstance(last_msg, dict) else None,
                    last_message_at=last_msg.get("timestamp") if isinstance(last_msg, dict) else chat.get("timestamp"),
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

        raw_msgs = data.get("items", [])

        # Resolve sender names: collect unique sender_ids
        account_id = ""
        sender_ids: set[str] = set()
        for msg in raw_msgs:
            if not msg.get("account_id"):
                continue
            account_id = msg["account_id"]
            sid = msg.get("sender_id", "")
            if sid and not msg.get("is_sender", 0):
                sender_ids.add(sid)

        sender_names: dict[str, str] = {}
        if sender_ids and account_id:
            resolved = await asyncio.gather(
                *(self._get_user_profile_cached(sid, account_id) for sid in sender_ids),
                return_exceptions=True,
            )
            for sid, profile in zip(sender_ids, resolved):
                if isinstance(profile, dict):
                    first = profile.get("first_name", "")
                    last = profile.get("last_name", "")
                    sender_names[sid] = f"{first} {last}".strip() if (first or last) else ""

        items: list[ChatMessage] = []
        for msg in raw_msgs:
            sid = msg.get("sender_id", "")
            is_own = bool(msg.get("is_sender", 0))
            name = "Eu" if is_own else (sender_names.get(sid) or msg.get("sender_name", ""))

            items.append(
                ChatMessage(
                    id=msg.get("id", ""),
                    sender_id=sid,
                    sender_name=name,
                    text=msg.get("text", ""),
                    timestamp=msg.get("timestamp", ""),
                    is_own=is_own,
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

            account_id = data.get("account_id", "")
            att_provider_id = data.get("attendee_provider_id", "")

            attendees: list[ChatAttendee] = []
            if att_provider_id and account_id:
                attendee = await self._resolve_attendee(att_provider_id, account_id)
                attendees.append(attendee)
            elif att_provider_id:
                attendees.append(ChatAttendee(id=att_provider_id, name=""))

            return ChatDetail(
                chat_id=data.get("id", ""),
                attendees=attendees,
                account_id=account_id,
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
