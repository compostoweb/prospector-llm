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
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC
from typing import Any

import httpx
import structlog

from core.config import settings

logger = structlog.get_logger()

_BASE_URL = settings.UNIPILE_BASE_URL
_TIMEOUT = 30.0
_OWN_PROFILE_TIMEOUT = httpx.Timeout(8.0, connect=8.0, read=8.0, write=8.0, pool=8.0)
_PROFILE_CACHE_TTL = 86400  # 24h
_PROFILE_CACHE_TTL_EMPTY = 3600  # 1h for unresolved names
_PREVIEW_CACHE_TTL = 300  # 5min for message previews
_CHAT_LIST_CACHE_TTL = 120  # 2min — alinhado com refetchInterval do frontend


class _LoopBoundAsyncClient:
    """Recria o AsyncClient por event loop para uso seguro em Celery."""

    def __init__(self, factory: Callable[[], httpx.AsyncClient]) -> None:
        self._factory = factory
        self._client: httpx.AsyncClient | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def _get_client(self) -> httpx.AsyncClient:
        loop = asyncio.get_running_loop()
        if self._client is None or self._loop is not loop:
            self._client = self._factory()
            self._loop = loop
        return self._client

    async def get(self, *args: Any, **kwargs: Any) -> httpx.Response:
        return await self._get_client().get(*args, **kwargs)

    async def post(self, *args: Any, **kwargs: Any) -> httpx.Response:
        return await self._get_client().post(*args, **kwargs)

    async def put(self, *args: Any, **kwargs: Any) -> httpx.Response:
        return await self._get_client().put(*args, **kwargs)

    async def patch(self, *args: Any, **kwargs: Any) -> httpx.Response:
        return await self._get_client().patch(*args, **kwargs)

    async def delete(self, *args: Any, **kwargs: Any) -> httpx.Response:
        return await self._get_client().delete(*args, **kwargs)

    async def aclose(self) -> None:
        client = self._client
        self._client = None
        self._loop = None
        if client is not None:
            await client.aclose()


class UnipileNonRetryableError(Exception):
    """Erro permanente da Unipile (400, 401, 403) — NÃO deve ser retentado."""


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
    company: str | None = None
    location: str | None = None
    email: str | None = None
    connections_count: int | None = None
    shared_connections_count: int | None = None
    is_premium: bool = False
    websites: list[str] = field(default_factory=list)


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
        self._client = _LoopBoundAsyncClient(
            lambda: httpx.AsyncClient(
                base_url=_BASE_URL,
                headers={
                    "X-API-KEY": settings.UNIPILE_API_KEY or "",
                    "accept": "application/json",
                    "content-type": "application/json",
                },
                timeout=_TIMEOUT,
            )
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

        if 400 <= response.status_code < 500:
            body_text = response.text[:500]
            logger.error(
                "unipile.linkedin_connect.client_error",
                status=response.status_code,
                profile_id=linkedin_profile_id,
                response_body=body_text,
            )
            raise UnipileNonRetryableError(f"Unipile {response.status_code}: {body_text}")

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

        if 400 <= response.status_code < 500:
            body_text = response.text[:500]
            logger.error(
                "unipile.linkedin_dm.client_error",
                status=response.status_code,
                profile_id=linkedin_profile_id,
                response_body=body_text,
            )
            raise UnipileNonRetryableError(f"Unipile {response.status_code}: {body_text}")

        response.raise_for_status()
        data = response.json()
        msg_id: str = data.get("id", "")
        logger.info(
            "unipile.linkedin_dm.sent",
            profile_id=linkedin_profile_id,
            message_id=msg_id,
        )
        return SendResult(message_id=msg_id, success=True)

    async def invalidate_inbox_cache(self, account_id: str, chat_id: str | None = None) -> None:
        from core.redis_client import redis_client

        if not account_id:
            return

        list_keys = await redis_client.keys(f"inbox:list:{account_id}:*")
        if list_keys:
            await redis_client.delete_many(*list_keys)

        if chat_id:
            await redis_client.delete(f"inbox:preview:{chat_id}")

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

        files = [("attachments", (fname, fbytes, ctype)) for fname, fbytes, ctype in attachments]

        response = await self._client.post(
            "/chats/messages",
            data=data_fields,
            files=files,
            headers={"content-type": None},  # type: ignore[arg-type]  # let httpx set multipart
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

        if 400 <= response.status_code < 500:
            body_text = response.text[:500]
            logger.error(
                "unipile.linkedin_voice.client_error",
                status=response.status_code,
                profile_id=linkedin_profile_id,
                response_body=body_text,
            )
            raise UnipileNonRetryableError(f"Unipile {response.status_code}: {body_text}")

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
            "to": [{"identifier": to_email}],
            "subject": subject,
            "body": body_html,
        }
        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id

        response = await self._client.post("/emails", json=payload)

        if 400 <= response.status_code < 500:
            body_text = response.text[:500]
            logger.error(
                "unipile.email.client_error",
                status=response.status_code,
                to=to_email,
                account_id=account_id,
                response_body=body_text,
            )
            raise UnipileNonRetryableError(f"Unipile {response.status_code}: {body_text}")

        response.raise_for_status()
        data = response.json()
        msg_id: str = data.get("id") or data.get("provider_id") or data.get("tracking_id") or ""
        logger.info(
            "unipile.email.sent",
            to=to_email,
            message_id=msg_id,
        )
        return SendResult(message_id=msg_id, success=True)

    # ── Webhooks ──────────────────────────────────────────────────────

    async def list_webhooks(self, limit: int = 250) -> list[dict[str, Any]]:
        """Lista os webhooks existentes na workspace Unipile."""
        response = await self._client.get("/webhooks", params={"limit": limit})

        if 400 <= response.status_code < 500:
            body_text = response.text[:500]
            logger.error(
                "unipile.webhooks.list_client_error",
                status=response.status_code,
                response_body=body_text,
            )
            raise UnipileNonRetryableError(f"Unipile {response.status_code}: {body_text}")

        response.raise_for_status()
        data = response.json()
        items = data.get("items", [])
        if not isinstance(items, list):
            logger.warning(
                "unipile.webhooks.list_invalid_payload", payload_type=type(items).__name__
            )
            return []
        return [item for item in items if isinstance(item, dict)]

    async def ensure_webhook(
        self,
        request_url: str,
        secret: str,
        source: str,
        events: list[str] | None = None,
        name: str | None = None,
    ) -> dict[str, Any]:
        """Garante que existe um webhook ativo para a URL e source informados."""
        existing_webhooks = await self.list_webhooks()
        for webhook in existing_webhooks:
            if webhook.get("request_url") != request_url:
                continue
            if webhook.get("source") != source:
                continue
            if webhook.get("enabled") is False:
                continue

            webhook_id = webhook.get("id") or webhook.get("webhook_id")
            logger.info(
                "unipile.webhook.already_registered",
                request_url=request_url,
                webhook_id=webhook_id,
                source=source,
            )
            return {
                "created": False,
                "already_exists": True,
                "webhook_id": str(webhook_id) if webhook_id else None,
            }

        payload = {
            "name": name or f"prospector-{source}-webhook",
            "request_url": request_url,
            "source": source,
            "format": "json",
            "enabled": True,
            "headers": [
                {"key": "Content-Type", "value": "application/json"},
                {"key": "Unipile-Auth", "value": secret},
            ],
        }
        if events:
            payload["events"] = events
        response = await self._client.post("/webhooks", json=payload)

        if 400 <= response.status_code < 500:
            body_text = response.text[:500]
            logger.error(
                "unipile.webhook.create_client_error",
                status=response.status_code,
                request_url=request_url,
                source=source,
                response_body=body_text,
            )
            raise UnipileNonRetryableError(f"Unipile {response.status_code}: {body_text}")

        response.raise_for_status()
        data = response.json()
        webhook_id = data.get("webhook_id") or data.get("id")
        logger.info(
            "unipile.webhook.registered",
            request_url=request_url,
            webhook_id=webhook_id,
            source=source,
            event_count=len(events or []),
        )
        return {
            "created": True,
            "already_exists": False,
            "webhook_id": str(webhook_id) if webhook_id else None,
        }

    async def get_webhooks_by_url(self, request_url: str) -> list[dict[str, Any]]:
        """Retorna todos os webhooks cadastrados para a URL informada."""
        existing_webhooks = await self.list_webhooks()
        return [
            webhook for webhook in existing_webhooks if webhook.get("request_url") == request_url
        ]

    async def get_account_status(self, account_id: str) -> dict[str, Any] | None:
        """Busca os detalhes de uma conta Unipile pelo account_id."""
        response = await self._client.get(f"/accounts/{account_id}")

        if response.status_code == 404:
            return None
        if 400 <= response.status_code < 500:
            body_text = response.text[:500]
            logger.error(
                "unipile.account_status.client_error",
                account_id=account_id,
                status=response.status_code,
                response_body=body_text,
            )
            raise UnipileNonRetryableError(f"Unipile {response.status_code}: {body_text}")

        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, dict) else None

    # ── Perfil LinkedIn ───────────────────────────────────────────────

    async def get_linkedin_profile(
        self,
        account_id: str,
        linkedin_url: str,
    ) -> LinkedInProfile | None:
        """
        Busca dados básicos de um perfil LinkedIn por URL pública.

        Endpoint: GET /users/{public_identifier}?account_id=...
        O `identifier` é o slug do LinkedIn extraído da URL, ex:
          https://www.linkedin.com/in/pedrofsoares/ → pedrofsoares

        Retorna None se o perfil não for encontrado ou se o identifier
        não puder ser extraído da URL.
        """
        import re as _re

        m = _re.search(r"/in/([a-zA-Z0-9_%-]+)", linkedin_url)
        if not m:
            logger.warning(
                "unipile.get_profile.bad_url",
                url=linkedin_url,
            )
            return None
        identifier = m.group(1).rstrip("/")

        params = {
            "account_id": account_id,
            "linkedin_sections": "experience",
        }
        response = await self._client.get(f"/users/{identifier}", params=params)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()

        # Monta nome completo
        first = data.get("first_name") or ""
        last = data.get("last_name") or ""
        full_name = f"{first} {last}".strip() or data.get("public_identifier", "")

        # Empresa atual = primeiro item de work_experience
        company: str | None = None
        experiences = data.get("work_experience") or []
        if experiences and isinstance(experiences, list):
            exp = experiences[0]
            if isinstance(exp, dict):
                company = exp.get("company") or exp.get("company_name") or None

        return LinkedInProfile(
            profile_id=data.get("provider_id") or data.get("public_identifier", ""),
            name=full_name,
            headline=data.get("headline"),
            company=company,
        )

    async def fetch_profile_company(
        self,
        account_id: str,
        provider_id: str,
    ) -> str | None:
        """
        Retorna o nome da empresa atual de um perfil LinkedIn via experience section.
        Usa GET /users/{provider_id}?linkedin_sections=experience.
        """
        try:
            r = await self._client.get(
                f"/users/{provider_id}",
                params={"account_id": account_id, "linkedin_sections": "experience"},
            )
            if r.status_code != 200:
                return None
            data = r.json()
            exp = data.get("work_experience") or []
            if isinstance(exp, list) and exp:
                first = exp[0]
                if isinstance(first, dict):
                    return first.get("company") or first.get("company_name") or None
            return None
        except Exception:
            return None

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
                "company": (data.get("work_experience") or [{}])[0].get("company")
                if isinstance(data.get("work_experience"), list) and data.get("work_experience")
                else None,
                "location": data.get("location") or None,
                "email": contact_email,
                "connections_count": data.get("connections_count"),
                "shared_connections_count": data.get("shared_connections_count"),
                "is_premium": bool(data.get("is_premium")),
                "websites": data.get("websites") or [],
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
            company=profile.get("company"),
            location=profile.get("location"),
            email=profile.get("email"),
            connections_count=profile.get("connections_count"),
            shared_connections_count=profile.get("shared_connections_count"),
            is_premium=bool(profile.get("is_premium")),
            websites=profile.get("websites") or [],
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
                cached_items = [
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
                    cached_items = [i for i in cached_items if i.unread_count > 0]
                return {
                    "items": cached_items[:limit],
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
                chat
                for chat in raw_items
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
                    fallback_name = chat.get("display_name") or chat.get("name") or ""
                    if fallback_name:
                        attendee = ChatAttendee(
                            id=attendee.id,
                            name=fallback_name,
                            profile_url=attendee.profile_url,
                            profile_picture_url=attendee.profile_picture_url,
                        )
                elif not attendee and att_id:
                    fallback_name = chat.get("display_name") or chat.get("name") or ""
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
        try:
            response = await self._client.get(f"/accounts/{account_id}/sync")
            ok = response.status_code == 200
            if ok:
                await self.invalidate_inbox_cache(account_id)
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

    async def mark_chat_as_read(self, chat_id: str) -> bool:
        """Marca um chat como lido via Unipile (propaga para o LinkedIn)."""
        try:
            response = await self._client.patch(
                f"/chats/{chat_id}",
                json={"action": "setReadStatus", "value": True},
            )
            response.raise_for_status()
            return True
        except httpx.HTTPError:
            logger.warning("unipile.mark_read.error", chat_id=chat_id)
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

    async def __aenter__(self) -> UnipileClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    # ── Own Profile ───────────────────────────────────────────────────

    async def get_own_profile(self, account_id: str) -> dict:
        """
        Busca perfil do dono da conta via GET /users/me.
        Retorna dict com provider_id, public_identifier, first_name, etc.
        Raises RuntimeError com detalhes se falhar.
        """
        try:
            response = await self._client.get(
                "/users/me",
                params={"account_id": account_id},
                timeout=_OWN_PROFILE_TIMEOUT,
            )
        except Exception as exc:
            logger.error(
                "unipile.own_profile.connection_error",
                account_id=account_id,
                error=str(exc),
            )
            raise RuntimeError(
                f"Falha de conexao com Unipile: {type(exc).__name__}: {exc}"
            ) from exc

        if response.status_code != 200:
            body = response.text[:500]
            logger.warning(
                "unipile.own_profile.error",
                account_id=account_id,
                status=response.status_code,
                body=body,
            )
            raise RuntimeError(f"Unipile GET /users/me retornou {response.status_code}: {body}")
        return response.json()

    # ── Own Posts with Metrics (Content Hub Analytics) ─────────────────

    async def get_own_posts_with_metrics(
        self,
        account_id: str,
        identifier: str,
        limit: int = 50,
    ) -> list[dict]:
        """
        Busca posts do usuario com metricas completas via Unipile.
        GET /users/{identifier}/posts

        Retorna lista de dicts com: id, social_id, text, date,
        reaction_counter, comment_counter, repost_counter,
        impressions_counter, share_url, etc.

        Diferente de get_lead_posts: nao usa cache, retorna todas as metricas,
        e busca mais posts (ate 100).
        """
        all_posts: list[dict] = []
        cursor: str | None = None

        while len(all_posts) < limit:
            batch_limit = min(limit - len(all_posts), 100)
            params: dict[str, str | int] = {
                "account_id": account_id,
                "limit": batch_limit,
            }
            if cursor:
                params["cursor"] = cursor

            try:
                response = await self._client.get(
                    f"/users/{identifier}/posts",
                    params=params,
                )
            except Exception as exc:
                logger.error(
                    "unipile.own_posts.connection_error",
                    identifier=identifier,
                    error=str(exc),
                )
                raise RuntimeError(
                    f"Falha de conexao com Unipile: {type(exc).__name__}: {exc}"
                ) from exc

            if response.status_code != 200:
                body = response.text[:500]
                logger.warning(
                    "unipile.own_posts.error",
                    identifier=identifier,
                    status=response.status_code,
                    body=body,
                )
                raise RuntimeError(
                    f"Unipile GET /users/{identifier}/posts retornou {response.status_code}: {body}"
                )
            data = response.json()
            items = data.get("items", [])
            if not items:
                break
            all_posts.extend(items)
            cursor = data.get("cursor")
            if not cursor:
                break

        return all_posts[:limit]

    # ── LinkedIn Posts ────────────────────────────────────────────────

    _POSTS_CACHE_TTL = 14400  # 4h
    _POST_RECENT_DAYS = 7

    async def get_lead_posts(
        self,
        account_id: str,
        provider_id: str,
        limit: int = 3,
    ) -> list[dict]:
        """
        Busca posts recentes do lead no LinkedIn.
        Retorna lista de dicts com: post_id, content, published_at.
        Cache Redis 4h por provider_id.
        """
        from core.redis_client import redis_client

        cache_key = f"unipile:posts:{provider_id}"
        cached = await redis_client.get(cache_key)
        if cached:
            try:
                return json.loads(cached)[:limit]
            except (json.JSONDecodeError, TypeError):
                pass

        try:
            response = await self._client.get(
                "/linkedin/posts",
                params={"account_id": account_id, "user_id": provider_id, "limit": limit},
            )
            if response.status_code != 200:
                logger.debug(
                    "unipile.posts.not_found",
                    provider_id=provider_id,
                    status=response.status_code,
                )
                return []
            data = response.json()
            posts_raw = data.get("items", data if isinstance(data, list) else [])
            posts = [
                {
                    "post_id": p.get("id", ""),
                    "content": (p.get("text") or p.get("content") or "")[:500],
                    "published_at": p.get("published_at") or p.get("created_at") or "",
                }
                for p in posts_raw
                if (p.get("text") or p.get("content"))
            ]
            await redis_client.set(cache_key, json.dumps(posts), ex=self._POSTS_CACHE_TTL)
            return posts[:limit]
        except Exception:
            logger.debug("unipile.posts.error", provider_id=provider_id)
            return []

    async def react_to_latest_post(
        self,
        account_id: str,
        provider_id: str,
        emoji: str = "LIKE",
    ) -> bool:
        """
        Reage ao post mais recente do lead (≤7 dias).
        Retorna True se reagiu, False se não há post recente ou houve erro.
        """
        from datetime import datetime, timedelta

        posts = await self.get_lead_posts(account_id, provider_id, limit=1)
        if not posts:
            logger.info("unipile.react.no_posts", provider_id=provider_id)
            return False

        post = posts[0]
        post_id = post.get("post_id", "")
        published_at = post.get("published_at", "")

        # Verifica se o post é recente (≤7 dias)
        if published_at:
            try:
                pub_dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                cutoff = datetime.now(tz=UTC) - timedelta(days=self._POST_RECENT_DAYS)
                if pub_dt < cutoff:
                    logger.info(
                        "unipile.react.post_too_old",
                        provider_id=provider_id,
                        published_at=published_at,
                    )
                    return False
            except (ValueError, TypeError):
                pass  # data inválida — tenta reagir mesmo assim

        if not post_id:
            return False

        try:
            response = await self._client.put(
                f"/linkedin/posts/{post_id}/reactions",
                json={"account_id": account_id, "reaction": emoji},
            )
            response.raise_for_status()
            logger.info(
                "unipile.react.sent",
                provider_id=provider_id,
                post_id=post_id,
                emoji=emoji,
            )
            return True
        except httpx.HTTPError:
            logger.warning("unipile.react.error", provider_id=provider_id, post_id=post_id)
            return False

    async def comment_on_latest_post(
        self,
        account_id: str,
        provider_id: str,
        comment_text: str,
    ) -> bool:
        """
        Comenta no post mais recente do lead (≤7 dias).
        Retorna True se comentou, False se não há post recente ou houve erro.
        """
        from datetime import datetime, timedelta

        posts = await self.get_lead_posts(account_id, provider_id, limit=1)
        if not posts:
            logger.info("unipile.comment.no_posts", provider_id=provider_id)
            return False

        post = posts[0]
        post_id = post.get("post_id", "")
        published_at = post.get("published_at", "")

        if published_at:
            try:
                pub_dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                cutoff = datetime.now(tz=UTC) - timedelta(days=self._POST_RECENT_DAYS)
                if pub_dt < cutoff:
                    logger.info(
                        "unipile.comment.post_too_old",
                        provider_id=provider_id,
                        published_at=published_at,
                    )
                    return False
            except (ValueError, TypeError):
                pass

        if not post_id:
            return False

        try:
            response = await self._client.post(
                f"/linkedin/posts/{post_id}/comments",
                json={"account_id": account_id, "text": comment_text},
            )
            response.raise_for_status()
            logger.info(
                "unipile.comment.sent",
                provider_id=provider_id,
                post_id=post_id,
            )
            return True
        except httpx.HTTPError:
            logger.warning("unipile.comment.error", provider_id=provider_id, post_id=post_id)
            return False

    async def send_linkedin_inmail(
        self,
        account_id: str,
        linkedin_profile_id: str,
        subject: str,
        message: str,
    ) -> SendResult:
        """
        Envia InMail para um perfil LinkedIn (para não-conexões).
        Requer conta com LinkedIn Premium / Sales Navigator.
        """
        payload = {
            "account_id": account_id,
            "attendees_ids": [linkedin_profile_id],
            "text": message,
            "subject": subject,
            "inmail": True,
        }
        response = await self._client.post("/chats/messages", json=payload)
        response.raise_for_status()
        data = response.json()
        msg_id: str = data.get("id", "")
        logger.info(
            "unipile.inmail.sent",
            profile_id=linkedin_profile_id,
            message_id=msg_id,
        )
        return SendResult(message_id=msg_id, success=True)

    async def search_linkedin_params(
        self,
        account_id: str,
        param_type: str,
        query: str,
    ) -> dict:
        """
        Faz lookup de IDs de parâmetros para busca LinkedIn (LOCATION, INDUSTRY, etc.).
        Retorna {"items": [{"id": "...", "title": "..."}]}.
        """
        try:
            response = await self._client.get(
                "/linkedin/search/parameters",
                params={"account_id": account_id, "type": param_type, "keywords": query},
            )
            response.raise_for_status()
            data = response.json()
            items = data.get("items", [])
            return {
                "items": [
                    {"id": item.get("id", ""), "title": item.get("title", "")} for item in items
                ]
            }
        except Exception as exc:
            logger.warning(
                "unipile.search_params.error",
                param_type=param_type,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            return {"items": []}

    def _parse_linkedin_items(self, raw_items: list[dict]) -> list[dict]:
        """Normaliza itens brutos do Unipile para o formato interno."""
        nd_map = {
            "DISTANCE_1": 1,
            "DISTANCE_2": 2,
            "DISTANCE_3PLUS": 3,
            "DISTANCE_3": 3,
            "OUT_OF_NETWORK": 3,
        }
        items: list[dict] = []
        for p in raw_items:
            public_identifier = p.get("public_identifier") or p.get("public_id") or ""
            nd = nd_map.get(p.get("network_distance", ""))
            items.append(
                {
                    "provider_id": p.get("id") or p.get("public_id") or "",
                    "name": p.get("name")
                    or (f"{p.get('first_name', '')} {p.get('last_name', '')}".strip()),
                    "headline": p.get("headline") or p.get("title") or None,
                    "company": p.get("company") or p.get("current_company") or None,
                    "industry": p.get("industry") or None,
                    "location": p.get("location") or None,
                    "profile_url": (
                        p.get("public_profile_url")
                        or p.get("profile_url")
                        or (
                            f"https://www.linkedin.com/in/{public_identifier}"
                            if public_identifier
                            else None
                        )
                    ),
                    "profile_picture_url": p.get("profile_picture_url") or None,
                    "network_distance": nd,
                }
            )
        return items

    async def _fetch_linkedin_page(
        self,
        account_id: str,
        body: dict,
        page_size: int,
        cursor: str | None = None,
    ) -> dict:
        """Faz uma única chamada ao Unipile /linkedin/search."""
        query_params: dict = {"account_id": account_id, "limit": page_size}
        if cursor:
            query_params["cursor"] = cursor

        response = await self._client.post("/linkedin/search", params=query_params, json=body)
        response.raise_for_status()
        data = response.json()
        raw_items = data.get("items", data if isinstance(data, list) else [])
        return {
            "items": self._parse_linkedin_items(raw_items),
            "cursor": data.get("cursor") or data.get("next_cursor"),
        }

    async def search_linkedin_profiles(
        self,
        account_id: str,
        keywords: str,
        titles: list[str] | None = None,
        companies: list[str] | None = None,
        company_ids: list[str] | None = None,
        location_ids: list[str] | None = None,
        industry_ids: list[str] | None = None,
        network_distance: list[int] | None = None,
        limit: int = 25,
        cursor: str | None = None,
    ) -> dict:
        """
        Busca perfis LinkedIn via Unipile Classic People Search.
        Auto-pagina até atingir ``limit`` quando ``cursor`` não é fornecido.
        Se ``cursor`` é fornecido (ex.: "Carregar mais"), faz apenas 1 fetch.
        """
        PAGE_SIZE = 25  # Unipile pode reduzir (Classic ≈ 10)
        MAX_PAGES = 20  # segurança anti-loop infinito

        body: dict = {
            "api": "classic",
            "category": "people",
            "keywords": keywords,
        }
        if location_ids:
            body["location"] = location_ids
        if industry_ids:
            body["industry"] = industry_ids
        if network_distance:
            body["network_distance"] = network_distance
        # Filtro nativo por IDs de empresa (mais preciso que advanced_keywords)
        if company_ids:
            body["company"] = company_ids

        advanced: dict = {}
        if titles:
            advanced["title"] = " OR ".join(titles)
        if companies:
            advanced["company"] = " OR ".join(companies)
        if advanced:
            body["advanced_keywords"] = advanced

        try:
            # Com cursor fornecido → fetch único (ex.: "Carregar mais")
            if cursor:
                return await self._fetch_linkedin_page(
                    account_id=account_id,
                    body=body,
                    page_size=min(limit, PAGE_SIZE),
                    cursor=cursor,
                )

            # Sem cursor → auto-paginação até atingir limit
            all_items: list[dict] = []
            current_cursor: str | None = None

            for page_num in range(MAX_PAGES):
                remaining = limit - len(all_items)
                if remaining <= 0:
                    break

                page = await self._fetch_linkedin_page(
                    account_id=account_id,
                    body=body,
                    page_size=min(remaining, PAGE_SIZE),
                    cursor=current_cursor,
                )

                page_items = page.get("items", [])
                all_items.extend(page_items)
                current_cursor = page.get("cursor")

                logger.debug(
                    "unipile.search.page",
                    page=page_num + 1,
                    fetched=len(page_items),
                    total=len(all_items),
                    target=limit,
                )

                if not current_cursor or not page_items:
                    break

                # Pequena pausa entre páginas para não estourar rate-limit
                if len(all_items) < limit:
                    await asyncio.sleep(0.3)

            return {
                "items": all_items[:limit],
                "cursor": current_cursor,
            }
        except httpx.HTTPError as exc:
            logger.warning(
                "unipile.search.error",
                keywords=keywords,
                error=str(exc),
            )
            return {"items": [], "cursor": None}


# Singleton para uso direto sem contexto
unipile_client = UnipileClient()
