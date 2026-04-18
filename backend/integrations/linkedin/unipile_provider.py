"""
integrations/linkedin/unipile_provider.py

Implementação do LinkedInProvider usando a Unipile API.
Wraps os métodos existentes do UnipileClient mantendo backwards compatibility.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from integrations.linkedin.base import (
    LinkedInConversation,
    LinkedInMessage,
    LinkedInProfile,
    LinkedInProvider,
    LinkedInSendResult,
)

if TYPE_CHECKING:
    from integrations.unipile_client import UnipileClient

logger = structlog.get_logger()


class UnipileLinkedInProvider(LinkedInProvider):
    """
    Provider LinkedIn baseado na Unipile API.

    Wraps o UnipileClient existente adaptando a interface genérica LinkedInProvider.
    O account_id (ID da conta LinkedIn no Unipile) é passado no construtor.
    """

    def __init__(self, client: UnipileClient, account_id: str) -> None:
        self._client = client
        self._account_id = account_id

    @property
    def provider_name(self) -> str:
        return "unipile"

    # ── Outbound ──────────────────────────────────────────────────────

    async def send_connect(
        self,
        linkedin_profile_id: str,
        message: str,
    ) -> LinkedInSendResult:
        try:
            result = await self._client.send_linkedin_connect(
                account_id=self._account_id,
                linkedin_profile_id=linkedin_profile_id,
                message=message,
            )
            return LinkedInSendResult(
                success=result.success,
                message_id=result.message_id,
                provider=self.provider_name,
            )
        except Exception as exc:
            logger.error("unipile_provider.connect.error", error=str(exc))
            return LinkedInSendResult(success=False, provider=self.provider_name, error=str(exc))

    async def send_dm(
        self,
        linkedin_profile_id: str,
        message: str,
    ) -> LinkedInSendResult:
        try:
            result = await self._client.send_linkedin_dm(
                account_id=self._account_id,
                linkedin_profile_id=linkedin_profile_id,
                message=message,
            )
            return LinkedInSendResult(
                success=result.success,
                message_id=result.message_id,
                provider=self.provider_name,
            )
        except Exception as exc:
            logger.error("unipile_provider.dm.error", error=str(exc))
            return LinkedInSendResult(success=False, provider=self.provider_name, error=str(exc))

    async def send_voice_note(
        self,
        linkedin_profile_id: str,
        audio_url: str,
    ) -> LinkedInSendResult:
        try:
            result = await self._client.send_linkedin_voice_note(
                account_id=self._account_id,
                linkedin_profile_id=linkedin_profile_id,
                audio_url=audio_url,
            )
            return LinkedInSendResult(
                success=result.success,
                message_id=result.message_id,
                provider=self.provider_name,
            )
        except Exception as exc:
            logger.error("unipile_provider.voice.error", error=str(exc))
            return LinkedInSendResult(success=False, provider=self.provider_name, error=str(exc))

    async def send_dm_with_attachments(
        self,
        linkedin_profile_id: str,
        message: str,
        attachments: list[tuple[str, bytes, str]],
    ) -> LinkedInSendResult:
        try:
            result = await self._client.send_linkedin_dm_with_attachments(
                account_id=self._account_id,
                linkedin_profile_id=linkedin_profile_id,
                message=message,
                attachments=attachments,
            )
            return LinkedInSendResult(
                success=result.success,
                message_id=result.message_id,
                provider=self.provider_name,
            )
        except Exception as exc:
            logger.error("unipile_provider.attachment.error", error=str(exc))
            return LinkedInSendResult(success=False, provider=self.provider_name, error=str(exc))

    async def send_inmail(
        self,
        linkedin_profile_id: str,
        subject: str,
        body: str,
    ) -> LinkedInSendResult:
        try:
            result = await self._client.send_linkedin_inmail(
                account_id=self._account_id,
                linkedin_profile_id=linkedin_profile_id,
                subject=subject,
                message=body,
            )
            return LinkedInSendResult(
                success=result.success,
                message_id=result.message_id,
                provider=self.provider_name,
            )
        except Exception as exc:
            logger.error("unipile_provider.inmail.error", error=str(exc))
            return LinkedInSendResult(success=False, provider=self.provider_name, error=str(exc))

    # ── Posts ─────────────────────────────────────────────────────────

    async def react_to_latest_post(
        self,
        linkedin_profile_id: str,
        reaction: str = "LIKE",
    ) -> LinkedInSendResult:
        try:
            reacted = await self._client.react_to_latest_post(
                account_id=self._account_id,
                provider_id=linkedin_profile_id,
                emoji=reaction,
            )
            return LinkedInSendResult(
                success=reacted,
                provider=self.provider_name,
                error=None if reacted else "Nenhum post recente elegível para reação.",
            )
        except Exception as exc:
            logger.error("unipile_provider.react.error", error=str(exc))
            return LinkedInSendResult(success=False, provider=self.provider_name, error=str(exc))

    async def comment_on_latest_post(
        self,
        linkedin_profile_id: str,
        comment: str,
    ) -> LinkedInSendResult:
        try:
            commented = await self._client.comment_on_latest_post(
                account_id=self._account_id,
                provider_id=linkedin_profile_id,
                comment_text=comment,
            )
            return LinkedInSendResult(
                success=commented,
                provider=self.provider_name,
                error=None if commented else "Nenhum post recente elegível para comentário.",
            )
        except Exception as exc:
            logger.error("unipile_provider.comment.error", error=str(exc))
            return LinkedInSendResult(success=False, provider=self.provider_name, error=str(exc))

    async def get_lead_posts(
        self,
        linkedin_profile_id: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        try:
            return await self._client.get_lead_posts(
                account_id=self._account_id,
                provider_id=linkedin_profile_id,
                limit=limit,
            )
        except Exception as exc:
            logger.error("unipile_provider.get_posts.error", error=str(exc))
            return []

    # ── Perfil e relação ──────────────────────────────────────────────

    async def get_profile(
        self,
        linkedin_url: str,
    ) -> LinkedInProfile | None:
        try:
            result = await self._client.get_linkedin_profile(
                account_id=self._account_id,
                linkedin_url=linkedin_url,
            )
            if result is None:
                return None
            return LinkedInProfile(
                profile_id=result.profile_id,
                name=result.name,
                headline=result.headline,
                company=result.company,
            )
        except Exception as exc:
            logger.error("unipile_provider.get_profile.error", error=str(exc))
            return None

    async def get_relation_status(
        self,
        linkedin_profile_id: str,
    ) -> str | None:
        return await self._client.get_relation_status(
            account_id=self._account_id,
            linkedin_profile_id=linkedin_profile_id,
        )

    # ── Inbox ─────────────────────────────────────────────────────────

    async def list_conversations(
        self,
        cursor: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """
        Adapta o list_chats do UnipileClient para a interface LinkedInProvider.
        Converte ChatSummary → LinkedInConversation.
        """
        raw = await self._client.list_chats(
            account_id=self._account_id,
            cursor=cursor,
            limit=limit,
        )
        items: list[LinkedInConversation] = []
        for chat in raw.get("items", []):
            from integrations.unipile_client import ChatSummary  # noqa: PLC0415
            if isinstance(chat, ChatSummary):
                first_attendee = chat.attendees[0] if chat.attendees else None
                items.append(
                    LinkedInConversation(
                        conversation_id=chat.chat_id,
                        attendee_id=first_attendee.id if first_attendee else "",
                        attendee_name=first_attendee.name if first_attendee else "",
                        attendee_profile_url=first_attendee.profile_url if first_attendee else None,
                        attendee_picture_url=first_attendee.profile_picture_url if first_attendee else None,
                        last_message_text=chat.last_message_text,
                        last_message_at=chat.last_message_at,
                        unread_count=chat.unread_count,
                        account_id=self._account_id,
                    )
                )
        return {"items": items, "cursor": raw.get("cursor")}

    async def get_messages(
        self,
        conversation_id: str,
        limit: int = 50,
        cursor: str | None = None,
    ) -> list[LinkedInMessage]:
        raw_msgs = await self._client.get_chat_messages(
            chat_id=conversation_id,
            limit=limit,
            cursor=cursor,
        )
        from integrations.unipile_client import ChatMessage  # noqa: PLC0415
        result: list[LinkedInMessage] = []
        for m in raw_msgs:
            if isinstance(m, ChatMessage):
                result.append(
                    LinkedInMessage(
                        id=m.id,
                        sender_id=m.sender_id,
                        sender_name=m.sender_name,
                        text=m.text,
                        timestamp=m.timestamp,
                        is_own=m.is_own,
                        attachments=m.attachments,
                    )
                )
        return result

    async def add_reaction(
        self,
        message_id: str,
        emoji: str,
    ) -> bool:
        return await self._client.add_reaction(message_id=message_id, emoji=emoji)

    async def remove_reaction(
        self,
        message_id: str,
    ) -> bool:
        return await self._client.remove_reaction(message_id=message_id, emoji="👍")

    # ── Busca ─────────────────────────────────────────────────────────

    async def search_profiles(
        self,
        query: str,
        limit: int = 20,
        filters: dict[str, Any] | None = None,
    ) -> list[LinkedInProfile]:
        try:
            raw = await self._client.search_linkedin_profiles(
                account_id=self._account_id,
                keywords=query,
                limit=limit,
                filters=filters or {},
            )
            return [
                LinkedInProfile(
                    profile_id=p.get("profile_id", ""),
                    name=p.get("name", ""),
                    headline=p.get("headline"),
                    company=p.get("company"),
                    profile_url=p.get("profile_url"),
                    location=p.get("location"),
                )
                for p in raw
            ]
        except Exception as exc:
            logger.error("unipile_provider.search.error", error=str(exc))
            return []

    # ── Saúde ─────────────────────────────────────────────────────────

    async def ping(self) -> bool:
        """Verifica conta via sync endpoint."""
        try:
            from integrations.unipile_client import unipile_client  # noqa: PLC0415
            response = await unipile_client._client.get(
                f"/accounts/{self._account_id}"
            )
            return response.status_code == 200
        except Exception:
            return False
