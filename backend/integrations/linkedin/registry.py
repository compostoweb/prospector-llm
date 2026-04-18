"""
integrations/linkedin/registry.py

LinkedInRegistry — único ponto de acesso ao LinkedIn no sistema.
Resolve o provider correto a partir de uma LinkedInAccount (ou fallback global).

Uso:
    registry = LinkedInRegistry(settings=settings)
    provider = registry.get_provider(account)          # → LinkedInProvider
    result = await registry.send_connect(account, profile_id, message)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from integrations.linkedin.base import (
    LinkedInMessage,
    LinkedInProfile,
    LinkedInProvider,
    LinkedInSendResult,
)

if TYPE_CHECKING:
    from core.config import Settings
    from models.linkedin_account import LinkedInAccount

logger = structlog.get_logger()


class LinkedInRegistry:
    """
    Ponto único de acesso ao LinkedIn no sistema.

    Instancie uma vez por task/request e reutilize.
    Nunca importe UnipileClient ou NativeLinkedInProvider diretamente nos services.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _build_provider(self, account: LinkedInAccount) -> LinkedInProvider:
        """
        Constrói o provider correto para a conta.

        provider_type = "unipile" → UnipileLinkedInProvider
        provider_type = "native"  → NativeLinkedInProvider
        """
        if account.provider_type == "unipile":
            from integrations.linkedin.unipile_provider import (
                UnipileLinkedInProvider,  # noqa: PLC0415
            )
            from integrations.unipile_client import unipile_client  # noqa: PLC0415
            return UnipileLinkedInProvider(
                client=unipile_client,
                account_id=account.unipile_account_id or "",
            )

        if account.provider_type == "native":
            from integrations.linkedin.native_provider import (
                NativeLinkedInProvider,  # noqa: PLC0415
            )
            from services.linkedin_account_service import decrypt_credential  # noqa: PLC0415
            li_at = decrypt_credential(account.li_at_cookie or "", self._settings) if account.li_at_cookie else ""
            return NativeLinkedInProvider(
                li_at=li_at,
                linkedin_username=account.linkedin_username or "",
            )

        raise ValueError(f"provider_type desconhecido: {account.provider_type!r}")

    def _build_fallback_provider(self) -> LinkedInProvider:
        """
        Constrói provider usando configurações globais (Unipile default).
        Usado quando a cadência não tem linkedin_account_id configurado.
        """
        from integrations.linkedin.unipile_provider import UnipileLinkedInProvider  # noqa: PLC0415
        from integrations.unipile_client import unipile_client  # noqa: PLC0415
        return UnipileLinkedInProvider(
            client=unipile_client,
            account_id=self._settings.UNIPILE_ACCOUNT_ID_LINKEDIN or "",
        )

    # ── Delegates com account explícito ──────────────────────────────

    async def send_connect(
        self,
        account: LinkedInAccount,
        linkedin_profile_id: str,
        message: str,
    ) -> LinkedInSendResult:
        return await self._build_provider(account).send_connect(linkedin_profile_id, message)

    async def send_dm(
        self,
        account: LinkedInAccount,
        linkedin_profile_id: str,
        message: str,
    ) -> LinkedInSendResult:
        return await self._build_provider(account).send_dm(linkedin_profile_id, message)

    async def send_voice_note(
        self,
        account: LinkedInAccount,
        linkedin_profile_id: str,
        audio_url: str,
    ) -> LinkedInSendResult:
        return await self._build_provider(account).send_voice_note(linkedin_profile_id, audio_url)

    async def send_dm_with_attachments(
        self,
        account: LinkedInAccount,
        linkedin_profile_id: str,
        message: str,
        attachments: list[tuple[str, bytes, str]],
    ) -> LinkedInSendResult:
        return await self._build_provider(account).send_dm_with_attachments(
            linkedin_profile_id, message, attachments
        )

    async def send_inmail(
        self,
        account: LinkedInAccount,
        linkedin_profile_id: str,
        subject: str,
        body: str,
    ) -> LinkedInSendResult:
        return await self._build_provider(account).send_inmail(linkedin_profile_id, subject, body)

    async def react_to_latest_post(
        self,
        account: LinkedInAccount,
        linkedin_profile_id: str,
        reaction: str = "LIKE",
    ) -> LinkedInSendResult:
        return await self._build_provider(account).react_to_latest_post(linkedin_profile_id, reaction)

    async def comment_on_latest_post(
        self,
        account: LinkedInAccount,
        linkedin_profile_id: str,
        comment: str,
    ) -> LinkedInSendResult:
        return await self._build_provider(account).comment_on_latest_post(linkedin_profile_id, comment)

    async def get_profile(
        self,
        account: LinkedInAccount,
        linkedin_url: str,
    ) -> LinkedInProfile | None:
        return await self._build_provider(account).get_profile(linkedin_url)

    async def get_lead_posts(
        self,
        account: LinkedInAccount,
        linkedin_profile_id: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        return await self._build_provider(account).get_lead_posts(linkedin_profile_id, limit)

    async def get_relation_status(
        self,
        account: LinkedInAccount,
        linkedin_profile_id: str,
    ) -> str | None:
        return await self._build_provider(account).get_relation_status(linkedin_profile_id)

    async def list_conversations(
        self,
        account: LinkedInAccount,
        cursor: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        return await self._build_provider(account).list_conversations(cursor=cursor, limit=limit)

    async def get_messages(
        self,
        account: LinkedInAccount,
        conversation_id: str,
        limit: int = 50,
        cursor: str | None = None,
    ) -> list[LinkedInMessage]:
        return await self._build_provider(account).get_messages(conversation_id, limit, cursor)

    async def ping(self, account: LinkedInAccount) -> bool:
        return await self._build_provider(account).ping()

    # ── Fallback global (sem LinkedInAccount) ─────────────────────────

    async def send_connect_global(
        self,
        linkedin_profile_id: str,
        message: str,
        account_id_override: str | None = None,
    ) -> LinkedInSendResult:
        """Usa o provider Unipile global (backwards-compat)."""
        from integrations.linkedin.unipile_provider import UnipileLinkedInProvider  # noqa: PLC0415
        from integrations.unipile_client import unipile_client  # noqa: PLC0415
        prov = UnipileLinkedInProvider(
            client=unipile_client,
            account_id=account_id_override or self._settings.UNIPILE_ACCOUNT_ID_LINKEDIN or "",
        )
        return await prov.send_connect(linkedin_profile_id, message)

    async def send_dm_global(
        self,
        linkedin_profile_id: str,
        message: str,
        account_id_override: str | None = None,
    ) -> LinkedInSendResult:
        from integrations.linkedin.unipile_provider import UnipileLinkedInProvider  # noqa: PLC0415
        from integrations.unipile_client import unipile_client  # noqa: PLC0415
        prov = UnipileLinkedInProvider(
            client=unipile_client,
            account_id=account_id_override or self._settings.UNIPILE_ACCOUNT_ID_LINKEDIN or "",
        )
        return await prov.send_dm(linkedin_profile_id, message)

    async def send_voice_note_global(
        self,
        linkedin_profile_id: str,
        audio_url: str,
        account_id_override: str | None = None,
    ) -> LinkedInSendResult:
        from integrations.linkedin.unipile_provider import UnipileLinkedInProvider  # noqa: PLC0415
        from integrations.unipile_client import unipile_client  # noqa: PLC0415
        prov = UnipileLinkedInProvider(
            client=unipile_client,
            account_id=account_id_override or self._settings.UNIPILE_ACCOUNT_ID_LINKEDIN or "",
        )
        return await prov.send_voice_note(linkedin_profile_id, audio_url)

    async def react_global(
        self,
        linkedin_profile_id: str,
        reaction: str = "LIKE",
        account_id_override: str | None = None,
    ) -> LinkedInSendResult:
        from integrations.linkedin.unipile_provider import UnipileLinkedInProvider  # noqa: PLC0415
        from integrations.unipile_client import unipile_client  # noqa: PLC0415
        prov = UnipileLinkedInProvider(
            client=unipile_client,
            account_id=account_id_override or self._settings.UNIPILE_ACCOUNT_ID_LINKEDIN or "",
        )
        return await prov.react_to_latest_post(linkedin_profile_id, reaction)

    async def comment_global(
        self,
        linkedin_profile_id: str,
        comment: str,
        account_id_override: str | None = None,
    ) -> LinkedInSendResult:
        from integrations.linkedin.unipile_provider import UnipileLinkedInProvider  # noqa: PLC0415
        from integrations.unipile_client import unipile_client  # noqa: PLC0415

        prov = UnipileLinkedInProvider(
            client=unipile_client,
            account_id=account_id_override or self._settings.UNIPILE_ACCOUNT_ID_LINKEDIN or "",
        )
        return await prov.comment_on_latest_post(linkedin_profile_id, comment)

    async def send_inmail_global(
        self,
        linkedin_profile_id: str,
        subject: str,
        body: str,
        account_id_override: str | None = None,
    ) -> LinkedInSendResult:
        from integrations.linkedin.unipile_provider import UnipileLinkedInProvider  # noqa: PLC0415
        from integrations.unipile_client import unipile_client  # noqa: PLC0415

        prov = UnipileLinkedInProvider(
            client=unipile_client,
            account_id=account_id_override or self._settings.UNIPILE_ACCOUNT_ID_LINKEDIN or "",
        )
        return await prov.send_inmail(linkedin_profile_id, subject, body)

    async def get_lead_posts_global(
        self,
        linkedin_profile_id: str,
        limit: int = 5,
        account_id_override: str | None = None,
    ) -> list[dict[str, Any]]:
        from integrations.linkedin.unipile_provider import UnipileLinkedInProvider  # noqa: PLC0415
        from integrations.unipile_client import unipile_client  # noqa: PLC0415

        prov = UnipileLinkedInProvider(
            client=unipile_client,
            account_id=account_id_override or self._settings.UNIPILE_ACCOUNT_ID_LINKEDIN or "",
        )
        return await prov.get_lead_posts(linkedin_profile_id, limit)
