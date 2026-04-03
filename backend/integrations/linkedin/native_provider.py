"""
integrations/linkedin/native_provider.py

NativeLinkedInProvider — implementação via API Voyager do LinkedIn.

Usa o cookie li_at para autenticar na API interna do LinkedIn.
Não depende de nenhum serviço terceiro — comunicação direta via httpx.

Capacidades:
  - send_connect   → invite/invite endpoint da Voyager
  - send_dm        → messaging/conversations/events
  - send_voice_note → 3 passos: metadata → PUT → events (subtype VOICE_NOTE)
  - get_profile    → miniProfile via public identifier
  - list_conversations → messaging/conversations
  - get_messages   → messaging/conversations/{id}/events
  - ping           → /voyager/api/me
"""

from __future__ import annotations

import asyncio
import mimetypes
from typing import Any

import httpx
import structlog

from integrations.linkedin.base import (
    LinkedInConversation,
    LinkedInMessage,
    LinkedInProfile,
    LinkedInProvider,
    LinkedInSendResult,
)

logger = structlog.get_logger()

_VOYAGER_BASE = "https://www.linkedin.com/voyager/api"
_DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)


def _build_headers(li_at: str, csrf: str = "ajax:0") -> dict[str, str]:
    return {
        "Cookie": f"li_at={li_at}; JSESSIONID={csrf}",
        "Csrf-Token": csrf,
        "User-Agent": _DEFAULT_UA,
        "X-Li-Lang": "pt_BR",
        "X-RestLi-Protocol-Version": "2.0.0",
        "X-Li-Track": '{"clientVersion":"1.13.19006"}',
        "Accept": "application/json",
    }


class NativeLinkedInProvider(LinkedInProvider):
    """
    Acessa a API Voyager interna do LinkedIn directamente via cookie li_at.

    O cookie é descriptografado antes de ser passado ao construtor —
    a responsabilidade de decriptar é da camada de serviço.
    """

    def __init__(self, li_at: str) -> None:
        self._li_at = li_at
        # CSRF token extraído do cookie JSESSIONID quando disponível.
        # Valor padrão funciona para maioria das operações GET e algumas POST.
        self._csrf = "ajax:0"

    @property
    def provider_name(self) -> str:
        return "native"

    def _client(self, extra_headers: dict[str, str] | None = None) -> httpx.AsyncClient:
        headers = _build_headers(self._li_at, self._csrf)
        if extra_headers:
            headers.update(extra_headers)
        return httpx.AsyncClient(
            base_url=_VOYAGER_BASE,
            headers=headers,
            timeout=30.0,
            follow_redirects=True,
        )

    # ── Ping ──────────────────────────────────────────────────────────

    async def ping(self) -> bool:
        async with self._client() as c:
            resp = await c.get("/me")
            return resp.status_code == 200

    # ── Perfil ────────────────────────────────────────────────────────

    async def get_profile(self, linkedin_url: str) -> LinkedInProfile | None:
        """
        Resolve URL do LinkedIn → dados do perfil via miniProfile.
        Aceita URL completa ou apenas o slug (ex: "joao-silva-123").
        """
        slug = _extract_slug(linkedin_url)
        async with self._client() as c:
            resp = await c.get(
                "/identity/profiles",
                params={"q": "memberIdentity", "memberIdentity": slug},
            )
            if resp.status_code != 200:
                logger.warning(
                    "native.get_profile.error",
                    slug=slug,
                    status=resp.status_code,
                )
                return None
            data = resp.json()
            elements = data.get("elements", [])
            if not elements:
                return None
            el = elements[0]
            mini = el.get("miniProfile", {})
            return LinkedInProfile(
                profile_id=mini.get("entityUrn", "").split(":")[-1],
                name=f"{mini.get('firstName', '')} {mini.get('lastName', '')}".strip(),
                headline=mini.get("occupation"),
                profile_url=f"https://www.linkedin.com/in/{slug}",
                profile_picture_url=_extract_picture(mini),
            )

    async def get_relation_status(self, linkedin_profile_id: str) -> str | None:
        """Retorna "CONNECTED" | "PENDING" | None."""
        async with self._client() as c:
            resp = await c.get(
                f"/identity/profiles/{linkedin_profile_id}/networkinfo",
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            dist = data.get("distance", {}).get("value", "")
            if dist == "DISTANCE_1":
                return "CONNECTED"
            if dist == "DISTANCE_0":
                return "CONNECTED"
            invitation = data.get("sentAt")
            if invitation:
                return "PENDING"
            return None

    # ── Send Connect ──────────────────────────────────────────────────

    async def send_connect(
        self,
        linkedin_profile_id: str,
        message: str,
    ) -> LinkedInSendResult:
        """
        Envia pedido de conexão via POST /growth/normInvitations.
        profile_id deve ser o ID numérico ou "urn:li:fsd_profile:{id}".
        """
        urn = _ensure_urn(linkedin_profile_id)
        payload = {
            "inviteeProfileUrn": urn,
            "customMessage": message,
        }
        async with self._client({"Content-Type": "application/json"}) as c:
            resp = await c.post("/growth/normInvitations", json=payload)
            if resp.status_code in (200, 201):
                data = resp.json()
                return LinkedInSendResult(
                    success=True,
                    message_id=str(data.get("invitationId", "")),
                    provider=self.provider_name,
                )
            return LinkedInSendResult(
                success=False,
                provider=self.provider_name,
                error=f"HTTP {resp.status_code}: {resp.text[:200]}",
            )

    # ── Send DM ───────────────────────────────────────────────────────

    async def send_dm(
        self,
        linkedin_profile_id: str,
        message: str,
    ) -> LinkedInSendResult:
        """Envia DM de texto para um perfil já conectado."""
        urn = _ensure_urn(linkedin_profile_id)
        payload = {
            "keyVersion": "LEGACY_INBOX",
            "conversationCreate": {
                "eventCreate": {
                    "value": {
                        "com.linkedin.voyager.messaging.create.MessageCreate": {
                            "attributedBody": {
                                "text": message,
                                "attributes": [],
                            },
                            "attachments": [],
                        }
                    }
                },
                "recipients": [urn],
                "subtype": "MEMBER_TO_MEMBER",
            },
        }
        async with self._client({"Content-Type": "application/json"}) as c:
            resp = await c.post("/messaging/conversations", json=payload)
            if resp.status_code in (200, 201):
                data = resp.json()
                conv_id = data.get("value", {}).get("entityUrn", "")
                return LinkedInSendResult(
                    success=True,
                    message_id=conv_id,
                    provider=self.provider_name,
                )
            return LinkedInSendResult(
                success=False,
                provider=self.provider_name,
                error=f"HTTP {resp.status_code}: {resp.text[:200]}",
            )

    # ── Send Voice Note ───────────────────────────────────────────────

    async def send_voice_note(
        self,
        linkedin_profile_id: str,
        audio_url: str,
    ) -> LinkedInSendResult:
        """
        Envia voice note via 3 passos da Voyager API:
          1. POST /voyagerMediaUploadMetadata → upload URL
          2. PUT {upload_url} com o arquivo de áudio
          3. POST /messaging/conversations/{id}/events com subtype VOICE_NOTE
        """
        urn = _ensure_urn(linkedin_profile_id)

        # ── Passo 1: baixar o áudio do URL ────────────────────────────
        try:
            async with httpx.AsyncClient(timeout=60.0) as dl:
                audio_resp = await dl.get(audio_url)
                audio_resp.raise_for_status()
                audio_bytes = audio_resp.content
                content_type = audio_resp.headers.get("content-type", "audio/mpeg")
                filename = audio_url.split("/")[-1].split("?")[0] or "voice_note.mp3"
        except Exception as exc:
            return LinkedInSendResult(
                success=False,
                provider=self.provider_name,
                error=f"Falha ao baixar áudio: {exc}",
            )

        # ── Passo 2: solicitar upload URL da Voyager ──────────────────
        async with self._client({"Content-Type": "application/json"}) as c:
            meta_payload = {
                "mediaUploadType": "MESSAGING_VOICE_NOTE",
                "fileSizeBytes": len(audio_bytes),
                "mediaContentType": content_type,
            }
            meta_resp = await c.post("/voyagerMediaUploadMetadata", json=meta_payload)
            if meta_resp.status_code not in (200, 201):
                return LinkedInSendResult(
                    success=False,
                    provider=self.provider_name,
                    error=f"Falha ao obter upload URL: HTTP {meta_resp.status_code}",
                )
            meta_data = meta_resp.json()
            upload_url: str = meta_data.get("value", {}).get("singleUploadUrl", "")
            media_urn: str = meta_data.get("value", {}).get("urn", "")

            if not upload_url or not media_urn:
                return LinkedInSendResult(
                    success=False,
                    provider=self.provider_name,
                    error="Resposta de metadata sem upload_url ou urn.",
                )

            # ── Passo 3: PUT do arquivo ───────────────────────────────
            # Upload sem autenticação LinkedIn (URL pré-assinada)
            async with httpx.AsyncClient(timeout=60.0) as uploader:
                put_resp = await uploader.put(
                    upload_url,
                    content=audio_bytes,
                    headers={"Content-Type": content_type},
                )
                if put_resp.status_code not in (200, 201):
                    return LinkedInSendResult(
                        success=False,
                        provider=self.provider_name,
                        error=f"Falha no PUT do áudio: HTTP {put_resp.status_code}",
                    )

            # ── Passo 4: criar conversa com evento VOICE_NOTE ─────────
            event_payload = {
                "keyVersion": "LEGACY_INBOX",
                "conversationCreate": {
                    "eventCreate": {
                        "value": {
                            "com.linkedin.voyager.messaging.create.MessageCreate": {
                                "attributedBody": {"text": "", "attributes": []},
                                "attachments": [],
                                "audios": [{"urn": media_urn}],
                            }
                        }
                    },
                    "recipients": [urn],
                    "subtype": "MEMBER_TO_MEMBER",
                },
            }
            event_resp = await c.post("/messaging/conversations", json=event_payload)
            if event_resp.status_code in (200, 201):
                data = event_resp.json()
                conv_id = data.get("value", {}).get("entityUrn", "")
                return LinkedInSendResult(
                    success=True,
                    message_id=conv_id,
                    provider=self.provider_name,
                )
            return LinkedInSendResult(
                success=False,
                provider=self.provider_name,
                error=f"Falha ao criar evento voice note: HTTP {event_resp.status_code}: {event_resp.text[:200]}",
            )

    # ── Send DM with attachments ──────────────────────────────────────

    async def send_dm_with_attachments(
        self,
        linkedin_profile_id: str,
        message: str,
        attachments: list[tuple[str, bytes, str]],
    ) -> LinkedInSendResult:
        """
        Envia DM com texto + arquivos.
        attachments: list of (filename, file_bytes, content_type)
        Para simplificar o MVP, envia apenas o texto se houver anexos.
        """
        logger.warning(
            "native.send_dm_with_attachments.fallback",
            note="Attachments não suportados no provider nativo. Enviando texto simples.",
            profile_id=linkedin_profile_id,
        )
        return await self.send_dm(linkedin_profile_id, message)

    # ── InMail ────────────────────────────────────────────────────────

    async def send_inmail(
        self,
        linkedin_profile_id: str,
        subject: str,
        body: str,
    ) -> LinkedInSendResult:
        """
        InMail via Voyager API.
        Usa o mesmo endpoint de DM mas com subtype INMAIL.
        Note: requer conta Premium no LinkedIn.
        """
        urn = _ensure_urn(linkedin_profile_id)
        payload = {
            "keyVersion": "LEGACY_INBOX",
            "conversationCreate": {
                "eventCreate": {
                    "value": {
                        "com.linkedin.voyager.messaging.create.MessageCreate": {
                            "attributedBody": {
                                "text": f"{subject}\n\n{body}",
                                "attributes": [],
                            },
                            "attachments": [],
                        }
                    }
                },
                "recipients": [urn],
                "subtype": "INMAIL",
            },
        }
        async with self._client({"Content-Type": "application/json"}) as c:
            resp = await c.post("/messaging/conversations", json=payload)
            if resp.status_code in (200, 201):
                return LinkedInSendResult(
                    success=True,
                    message_id=str(resp.json().get("value", {}).get("entityUrn", "")),
                    provider=self.provider_name,
                )
            return LinkedInSendResult(
                success=False,
                provider=self.provider_name,
                error=f"HTTP {resp.status_code}: {resp.text[:200]}",
            )

    # ── Posts ─────────────────────────────────────────────────────────

    async def react_to_latest_post(
        self,
        linkedin_profile_id: str,
        reaction: str = "LIKE",
    ) -> LinkedInSendResult:
        """Busca o post mais recente do perfil e reage."""
        posts = await self.get_lead_posts(linkedin_profile_id, limit=1)
        if not posts:
            return LinkedInSendResult(
                success=False,
                provider=self.provider_name,
                error="Nenhum post encontrado para reagir.",
            )
        post_urn = posts[0].get("urn", "")
        async with self._client({"Content-Type": "application/json"}) as c:
            payload = {"reactionType": reaction, "entityUrn": post_urn}
            resp = await c.post("/socialActions/reactions", json=payload)
            return LinkedInSendResult(
                success=resp.status_code in (200, 201),
                provider=self.provider_name,
                error=None if resp.status_code in (200, 201) else f"HTTP {resp.status_code}",
            )

    async def comment_on_latest_post(
        self,
        linkedin_profile_id: str,
        comment: str,
    ) -> LinkedInSendResult:
        """Busca o post mais recente do perfil e comenta."""
        posts = await self.get_lead_posts(linkedin_profile_id, limit=1)
        if not posts:
            return LinkedInSendResult(
                success=False,
                provider=self.provider_name,
                error="Nenhum post encontrado para comentar.",
            )
        post_urn = posts[0].get("urn", "")
        async with self._client({"Content-Type": "application/json"}) as c:
            payload = {
                "actor": f"urn:li:person:{linkedin_profile_id}",
                "message": {"text": comment},
                "object": post_urn,
            }
            resp = await c.post("/socialActions/comments", json=payload)
            return LinkedInSendResult(
                success=resp.status_code in (200, 201),
                provider=self.provider_name,
                error=None if resp.status_code in (200, 201) else f"HTTP {resp.status_code}",
            )

    async def get_lead_posts(
        self,
        linkedin_profile_id: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Retorna posts recentes do lead."""
        urn_encoded = f"urn%3Ali%3Afsd_profile%3A{linkedin_profile_id}"
        async with self._client() as c:
            resp = await c.get(
                "/feed/updatesV2",
                params={
                    "q": "memberShareFeed",
                    "moduleKey": "member-share",
                    "includeLongTermHistory": "true",
                    "profileUrn": f"urn:li:fsd_profile:{linkedin_profile_id}",
                    "count": str(limit),
                },
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            elements = data.get("elements", [])
            return [
                {
                    "urn": el.get("updateMetadata", {}).get("urn", ""),
                    "text": (
                        el.get("value", {})
                        .get("com.linkedin.voyager.feed.render.UpdateV2", {})
                        .get("commentary", {})
                        .get("text", {})
                        .get("text", "")
                    ),
                }
                for el in elements
            ]

    # ── Inbox ─────────────────────────────────────────────────────────

    async def list_conversations(
        self,
        cursor: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Lista conversas do inbox, com paginação por cursor."""
        params: dict[str, Any] = {
            "keyVersion": "LEGACY_INBOX",
            "q": "sortedInbox",
            "count": str(limit),
        }
        if cursor:
            params["createdBefore"] = cursor

        async with self._client() as c:
            resp = await c.get("/messaging/conversations", params=params)
            if resp.status_code != 200:
                return {"items": [], "cursor": None}

            data = resp.json()
            conversations = []
            for el in data.get("elements", []):
                conv_urn = el.get("entityUrn", "")
                receipt = el.get("lastActivityAt")
                participants = el.get("participants", [])
                attendee: dict[str, Any] = (
                    participants[0] if participants else {}
                )
                mini = (
                    attendee.get("com.linkedin.voyager.messaging.MessagingMember", {})
                    .get("miniProfile", {})
                )
                name = f"{mini.get('firstName', '')} {mini.get('lastName', '')}".strip()
                last_event = el.get("events", [{}])[0] if el.get("events") else {}
                last_text = (
                    last_event.get("eventContent", {})
                    .get("com.linkedin.voyager.messaging.event.MessageEvent", {})
                    .get("attributedBody", {})
                    .get("text", "")
                )
                conversations.append(
                    LinkedInConversation(
                        conversation_id=conv_urn,
                        attendee_id=mini.get("entityUrn", "").split(":")[-1],
                        attendee_name=name,
                        last_message_text=last_text,
                        last_message_at=str(receipt) if receipt else None,
                        unread_count=el.get("unreadCount", 0),
                    )
                )

            next_cursor = None
            paging = data.get("paging", {})
            if paging.get("start", 0) + paging.get("count", 0) < paging.get("total", 0):
                next_cursor = str(
                    data.get("elements", [{}])[-1].get("lastActivityAt", "")
                )

            return {"items": conversations, "cursor": next_cursor}

    async def get_messages(
        self,
        conversation_id: str,
        limit: int = 50,
        cursor: str | None = None,
    ) -> list[LinkedInMessage]:
        """Retorna mensagens de uma conversa."""
        # conversation_id pode ser urn ou ID curto
        conv_id = _extract_conversation_id(conversation_id)
        params: dict[str, Any] = {"count": str(limit)}
        if cursor:
            params["createdBefore"] = cursor

        async with self._client() as c:
            resp = await c.get(
                f"/messaging/conversations/{conv_id}/events",
                params=params,
            )
            if resp.status_code != 200:
                return []

            messages = []
            for el in resp.json().get("elements", []):
                event_urn = el.get("entityUrn", "")
                sender = el.get("from", {}).get(
                    "com.linkedin.voyager.messaging.MessagingMember", {}
                )
                mini = sender.get("miniProfile", {})
                sender_id = mini.get("entityUrn", "").split(":")[-1]
                sender_name = f"{mini.get('firstName', '')} {mini.get('lastName', '')}".strip()
                body = (
                    el.get("eventContent", {})
                    .get("com.linkedin.voyager.messaging.event.MessageEvent", {})
                    .get("attributedBody", {})
                    .get("text", "")
                )
                audios = (
                    el.get("eventContent", {})
                    .get("com.linkedin.voyager.messaging.event.MessageEvent", {})
                    .get("audios", [])
                )
                messages.append(
                    LinkedInMessage(
                        id=event_urn,
                        sender_id=sender_id,
                        sender_name=sender_name,
                        text=body,
                        timestamp=str(el.get("createdAt", "")),
                        is_voice_note=bool(audios),
                    )
                )
            return messages

    async def add_reaction(self, message_id: str, emoji: str) -> bool:
        async with self._client({"Content-Type": "application/json"}) as c:
            resp = await c.post(
                "/messaging/reactionSummaries",
                json={"reactionType": emoji, "eventUrn": message_id},
            )
            return resp.status_code in (200, 201)

    async def remove_reaction(self, message_id: str) -> bool:
        async with self._client() as c:
            resp = await c.delete(
                "/messaging/reactionSummaries",
                params={"eventUrn": message_id},
            )
            return resp.status_code in (200, 204)

    # ── Busca ─────────────────────────────────────────────────────────

    async def search_profiles(
        self,
        query: str,
        limit: int = 20,
        filters: dict[str, Any] | None = None,
    ) -> list[LinkedInProfile]:
        """Busca perfis via typeahead da Voyager."""
        async with self._client() as c:
            resp = await c.get(
                "/search/hits",
                params={
                    "q": "typeahead",
                    "query": query,
                    "origin": "OTHER",
                    "count": str(limit),
                    "filters": "List(resultType->PEOPLE)",
                },
            )
            if resp.status_code != 200:
                return []
            profiles = []
            for el in resp.json().get("elements", []):
                target = el.get("hitInfo", {}).get(
                    "com.linkedin.voyager.search.SearchProfile", {}
                )
                mini = target.get("miniProfile", {})
                profiles.append(
                    LinkedInProfile(
                        profile_id=mini.get("entityUrn", "").split(":")[-1],
                        name=f"{mini.get('firstName', '')} {mini.get('lastName', '')}".strip(),
                        headline=mini.get("occupation"),
                        profile_picture_url=_extract_picture(mini),
                    )
                )
            return profiles


# ── Helpers ───────────────────────────────────────────────────────────


def _extract_slug(linkedin_url: str) -> str:
    """Extrai o slug da URL do LinkedIn ou retorna o valor se já for slug."""
    url = linkedin_url.rstrip("/")
    if "/in/" in url:
        return url.split("/in/")[-1].split("/")[0].split("?")[0]
    return url


def _ensure_urn(profile_id: str) -> str:
    """Garante que o profile_id está no formato urn:li:fsd_profile:{id}."""
    if profile_id.startswith("urn:"):
        return profile_id
    return f"urn:li:fsd_profile:{profile_id}"


def _extract_conversation_id(conversation_id: str) -> str:
    """Extrai o ID curto de uma conversa do URN ou retorna como está."""
    if ":" in conversation_id:
        return conversation_id.split(":")[-1]
    return conversation_id


def _extract_picture(mini: dict[str, Any]) -> str | None:
    """Extrai a URL da foto de perfil do miniProfile."""
    try:
        artifacts = (
            mini.get("picture", {})
            .get("com.linkedin.common.VectorImage", {})
            .get("artifacts", [])
        )
        if artifacts:
            root = (
                mini.get("picture", {})
                .get("com.linkedin.common.VectorImage", {})
                .get("rootUrl", "")
            )
            return root + artifacts[-1].get("fileIdentifyingUrlPathSegment", "")
    except Exception:
        pass
    return None
