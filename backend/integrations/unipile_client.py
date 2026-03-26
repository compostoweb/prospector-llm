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
_PROFILE_CACHE_TTL_EMPTY = 3600  # 1h for unresolved names
_PREVIEW_CACHE_TTL = 300  # 5min for message previews
_CHAT_LIST_CACHE_TTL = 120  # 2min for full conversation list


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
    headline: str | None = None
    location: str | None = None
    email: str | None = None
    connections_count: int | None = None
    is_premium: bool = False


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

    async def send_linkedin_dm_with_attachments(
        self,
        account_id: str,
        linkedin_profile_id: str,
        message: str,
        attachments: list[tuple[str, bytes, str]],
    ) -> SendResult:
        """
        Envia DM com texto + arquivos anexos.
        attachments: list of (filename, file_bytes, content_type)
        """
        data_fields: dict = {
            "account_id": account_id,
            "attendees_ids": f'["{linkedin_profile_id}"]',
        }
        if message:
            data_fields["text"] = message

        files = [
            ("attachments", (fname, fbytes, ctype))
            for fname, fbytes, ctype in attachments
        ]

        response = await self._client.post(
            "/chats/messages",
            data=data_fields,
            files=files,
            headers={"content-type": None},  # let httpx set multipart
        )
        response.raise_for_status()
        resp_data = response.json()
        msg_id: str = resp_data.get("id", "")
        logger.info(
            "unipile.linkedin_dm_attachment.sent",
            profile_id=linkedin_profile_id,
            message_id=msg_id,
            attachment_count=len(attachments),
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
                # Cache negative result to avoid repeated API calls
                await redis_client.set(
                    cache_key,
                    json.dumps({}),
                    ex=_PROFILE_CACHE_TTL_EMPTY,
                )
                return {}
            data = response.json()
            first = data.get("first_name", "")
            last = data.get("last_name", "")
            public_id = data.get("public_identifier", "")
            has_name = bool(first or last)
            # Extract contact email if available
            contact_info = data.get("contact_info") or {}
            emails_list = contact_info.get("emails") or []
            contact_email = emails_list[0] if emails_list else None

            profile = {
                "first_name": first,
                "last_name": last,
                "profile_picture_url": data.get("profile_picture_url"),
                "public_identifier": public_id,
                "headline": data.get("headline") or None,
                "location": data.get("location") or None,
                "email": contact_email,
                "connections_count": data.get("connections_count"),
                "is_premium": bool(data.get("is_premium")),
            }
            # Shorter TTL when name is empty so we retry sooner
            ttl = _PROFILE_CACHE_TTL if has_name else _PROFILE_CACHE_TTL_EMPTY
            await redis_client.set(
                cache_key,
                json.dumps(profile),
                ex=ttl,
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
        # Fallback: use LinkedIn username when name unavailable
        if not name and public_id:
            name = public_id
        profile_url = f"https://www.linkedin.com/in/{public_id}" if public_id else None

        return ChatAttendee(
            id=provider_id,
            name=name,
            profile_url=profile_url,
            profile_picture_url=profile.get("profile_picture_url"),
            headline=profile.get("headline"),
            location=profile.get("location"),
            email=profile.get("email"),
            connections_count=profile.get("connections_count"),
            is_premium=bool(profile.get("is_premium")),
        )

    async def _get_last_message_preview(
        self,
        chat_id: str,
    ) -> tuple[str | None, str | None]:
        """
        Busca texto + timestamp da última mensagem de um chat com cache Redis.
        Retorna (text, timestamp). Cache TTL: 5min.
        """
        from core.redis_client import redis_client

        cache_key = f"inbox:preview:{chat_id}"
        cached = await redis_client.get(cache_key)
        if cached:
            try:
                data = json.loads(cached)
                return data.get("text"), data.get("timestamp")
            except (json.JSONDecodeError, TypeError):
                pass

        try:
            response = await self._client.get(
                f"/chats/{chat_id}/messages",
                params={"limit": 1},
            )
            if response.status_code != 200:
                logger.debug(
                    "unipile.preview.status_error",
                    chat_id=chat_id,
                    status=response.status_code,
                )
                # Cache empty to avoid repeated failures
                await redis_client.set(
                    cache_key,
                    json.dumps({"text": None, "timestamp": None}),
                    ex=_PREVIEW_CACHE_TTL,
                )
                return None, None
            data = response.json()
            msgs = data.get("items", [])
            if not msgs:
                # Cache empty so we don't retry
                await redis_client.set(
                    cache_key,
                    json.dumps({"text": None, "timestamp": None}),
                    ex=_PREVIEW_CACHE_TTL,
                )
                return None, None
            msg = msgs[0]
            text = msg.get("text", "") or None
            ts = msg.get("timestamp", "") or None
            await redis_client.set(
                cache_key,
                json.dumps({"text": text, "timestamp": ts}),
                ex=_PREVIEW_CACHE_TTL,
            )
            return text, ts
        except Exception:
            logger.debug("unipile.preview.error", chat_id=chat_id)
            return None, None

    async def list_chats(
        self,
        account_id: str,
        cursor: str | None = None,
        limit: int = 50,
        unread_only: bool = False,
    ) -> dict:
        """
        Lista conversas LinkedIn.
        Retorna dict com 'items' (list[ChatSummary]) e 'cursor' (próxima página).

        Estratégia de cache em 3 níveis:
          1. Lista completa de chats: Redis 2min (evita repetir chamadas Unipile)
          2. Perfis de attendees: Redis 24h / 1h para perfis vazios
          3. Previews de mensagens: Redis 5min
        Filtros (unread_only) são aplicados APÓS o cache.
        """
        from core.redis_client import redis_client

        # ── Try response-level cache first ────────────────────────────
        cache_key = f"inbox:list:{account_id}:{cursor or 'start'}:{limit}"
        cached = await redis_client.get(cache_key)
        if cached:
            try:
                cached_data = json.loads(cached)
                items = [
                    ChatSummary(
                        chat_id=c["chat_id"],
                        attendees=[
                            ChatAttendee(
                                id=a["id"],
                                name=a["name"],
                                profile_url=a.get("profile_url"),
                                profile_picture_url=a.get("profile_picture_url"),
                            )
                            for a in c.get("attendees", [])
                        ],
                        last_message_text=c.get("last_message_text"),
                        last_message_at=c.get("last_message_at"),
                        unread_count=c.get("unread_count", 0),
                        account_id=account_id,
                    )
                    for c in cached_data.get("items", [])
                ]
                if unread_only:
                    items = [i for i in items if i.unread_count > 0]
                return {
                    "items": items[:limit],
                    "cursor": cached_data.get("cursor"),
                }
            except (json.JSONDecodeError, TypeError, KeyError):
                pass

        # ── Fetch from Unipile API ────────────────────────────────────
        _SKIP_CONTENT_TYPES = {"linkedin_offer", "sponsored", "linkedin_ad"}
        items: list[ChatSummary] = []
        seen_attendee_ids: set[str] = set()
        current_cursor = cursor
        max_api_calls = 3
        sem = asyncio.Semaphore(10)

        async def _resolve_with_sem(aid: str) -> ChatAttendee:
            async with sem:
                return await self._resolve_attendee(aid, account_id)

        for _ in range(max_api_calls):
            if len(items) >= limit:
                break

            fetch_limit = min(100, max(limit * 3, 50))
            params: dict = {"account_id": account_id, "limit": fetch_limit}
            if current_cursor:
                params["cursor"] = current_cursor

            response = await self._client.get("/chats", params=params)
            response.raise_for_status()
            data = response.json()

            raw_items = data.get("items", [])
            if not raw_items:
                current_cursor = None
                break

            # Filter out sponsored / read-only / offer chats
            filtered_items = [
                chat for chat in raw_items
                if chat.get("content_type", "") not in _SKIP_CONTENT_TYPES
                and not chat.get("read_only", 0)
            ]

            # Resolve profiles in parallel with semaphore
            attendee_ids = {
                chat.get("attendee_provider_id", "")
                for chat in filtered_items
                if chat.get("attendee_provider_id")
            } - seen_attendee_ids
            profiles: dict[str, ChatAttendee] = {}
            if attendee_ids:
                resolved = await asyncio.gather(
                    *(_resolve_with_sem(aid) for aid in attendee_ids),
                    return_exceptions=True,
                )
                for att in resolved:
                    if isinstance(att, ChatAttendee):
                        profiles[att.id] = att

            for chat in filtered_items:
                if len(items) >= limit:
                    break

                att_id = chat.get("attendee_provider_id", "")
                attendee = profiles.get(att_id)

                # Fallback: use display_name from chat if profile resolution failed
                if attendee and not attendee.name:
                    fallback_name = (
                        chat.get("display_name")
                        or chat.get("name")
                        or ""
                    )
                    if fallback_name:
                        attendee = ChatAttendee(
                            id=attendee.id,
                            name=fallback_name,
                            profile_url=attendee.profile_url,
                            profile_picture_url=attendee.profile_picture_url,
                        )
                elif not attendee and att_id:
                    fallback_name = (
                        chat.get("display_name")
                        or chat.get("name")
                        or ""
                    )
                    attendee = ChatAttendee(id=att_id, name=fallback_name)

                attendees = [attendee] if attendee else []

                # Deduplicate: skip if we already have a chat with same attendee
                if att_id:
                    if att_id in seen_attendee_ids:
                        continue
                    seen_attendee_ids.add(att_id)

                # Use chat-level timestamp (Unipile /chats doesn't include lastMessage)
                items.append(
                    ChatSummary(
                        chat_id=chat.get("id", ""),
                        attendees=attendees,
                        last_message_text=None,
                        last_message_at=chat.get("timestamp"),
                        unread_count=chat.get("unread_count", 0),
                        account_id=account_id,
                    )
                )

            current_cursor = data.get("cursor")
            if not current_cursor:
                break

        final_items = items[:limit]

        # Fetch message previews in parallel with semaphore
        async def _fill_preview(chat_summary: ChatSummary) -> None:
            async with sem:
                text, ts = await self._get_last_message_preview(chat_summary.chat_id)
                if text:
                    chat_summary.last_message_text = text
                if ts:
                    chat_summary.last_message_at = ts

        await asyncio.gather(
            *(_fill_preview(c) for c in final_items),
            return_exceptions=True,
        )

        # Sort newest first
        final_items.sort(
            key=lambda x: x.last_message_at or "",
            reverse=True,
        )

        # ── Cache full result for 2min ────────────────────────────────
        try:
            serializable = {
                "items": [
                    {
                        "chat_id": c.chat_id,
                        "attendees": [
                            {
                                "id": a.id,
                                "name": a.name,
                                "profile_url": a.profile_url,
                                "profile_picture_url": a.profile_picture_url,
                            }
                            for a in c.attendees
                        ],
                        "last_message_text": c.last_message_text,
                        "last_message_at": c.last_message_at,
                        "unread_count": c.unread_count,
                    }
                    for c in final_items
                ],
                "cursor": current_cursor,
            }
            await redis_client.set(
                cache_key,
                json.dumps(serializable),
                ex=_CHAT_LIST_CACHE_TTL,
            )
        except Exception:
            logger.debug("inbox.cache.write_error")

        # Apply unread filter after caching (cache stores ALL conversations)
        if unread_only:
            final_items = [i for i in final_items if i.unread_count > 0]

        return {
            "items": final_items[:limit],
            "cursor": current_cursor,
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

    async def sync_account(self, account_id: str) -> bool:
        """Dispara resync da conta Unipile e invalida caches de inbox."""
        from core.redis_client import redis_client

        try:
            response = await self._client.get(f"/accounts/{account_id}/sync")
            ok = response.status_code == 200
            if ok:
                # Invalidate all inbox list caches to force fresh fetch
                keys = await redis_client._redis.keys(f"inbox:list:{account_id}:*")
                if keys:
                    await redis_client._redis.delete(*keys)
                logger.info("unipile.account.sync_started", account_id=account_id)
            else:
                logger.warning(
                    "unipile.account.sync_failed",
                    account_id=account_id,
                    status=response.status_code,
                )
            return ok
        except Exception:
            logger.warning("unipile.account.sync_error", account_id=account_id)
            return False

    async def add_reaction(
        self,
        message_id: str,
        emoji: str,
    ) -> bool:
        """Adiciona reação emoji a uma mensagem de chat."""
        try:
            response = await self._client.put(
                f"/messages/{message_id}/reactions",
                json={"reaction": emoji},
            )
            response.raise_for_status()
            return True
        except httpx.HTTPError:
            logger.warning(
                "unipile.add_reaction.error",
                message_id=message_id,
                emoji=emoji,
            )
            return False

    async def remove_reaction(
        self,
        message_id: str,
        emoji: str,
    ) -> bool:
        """Remove reação emoji de uma mensagem de chat."""
        try:
            response = await self._client.delete(
                f"/messages/{message_id}/reactions",
                params={"reaction": emoji},
            )
            response.raise_for_status()
            return True
        except httpx.HTTPError:
            logger.warning(
                "unipile.remove_reaction.error",
                message_id=message_id,
                emoji=emoji,
            )
            return False

    async def __aenter__(self) -> "UnipileClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()


# Singleton para uso direto sem contexto
unipile_client = UnipileClient()
