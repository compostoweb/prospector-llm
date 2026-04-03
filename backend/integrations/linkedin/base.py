"""
integrations/linkedin/base.py

Contrato base para todos os provedores de LinkedIn.
Cada provedor implementa esta interface — o restante do sistema
nunca importa clientes diretamente, só usa LinkedInProvider via LinkedInRegistry.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LinkedInSendResult:
    """Resultado normalizado de qualquer operação de envio LinkedIn."""
    success: bool
    message_id: str | None = None
    provider: str = ""
    error: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class LinkedInProfile:
    """Dados básicos de um perfil LinkedIn."""
    profile_id: str
    name: str
    headline: str | None = None
    company: str | None = None
    profile_url: str | None = None
    profile_picture_url: str | None = None
    location: str | None = None
    email: str | None = None
    connections_count: int | None = None
    is_premium: bool = False


@dataclass
class LinkedInConversation:
    """Resumo de uma conversa LinkedIn."""
    conversation_id: str
    attendee_id: str       # linkedin_profile_id do interlocutor
    attendee_name: str
    attendee_profile_url: str | None = None
    attendee_picture_url: str | None = None
    last_message_text: str | None = None
    last_message_at: str | None = None
    unread_count: int = 0
    account_id: str = ""


@dataclass
class LinkedInMessage:
    """Uma mensagem em uma conversa LinkedIn."""
    id: str
    sender_id: str
    sender_name: str
    text: str
    timestamp: str
    is_own: bool = False
    is_voice_note: bool = False
    attachments: list[dict[str, Any]] = field(default_factory=list)


class LinkedInProvider(ABC):
    """
    Interface base para provedores de LinkedIn.

    Implementações:
      - UnipileLinkedInProvider  — usa a API REST da Unipile
      - NativeLinkedInProvider   — usa a API Voyager do LinkedIn via cookie li_at
    """

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    # ── Outbound ──────────────────────────────────────────────────────

    @abstractmethod
    async def send_connect(
        self,
        linkedin_profile_id: str,
        message: str,
    ) -> LinkedInSendResult:
        """Envia um pedido de conexão com nota personalizada."""
        ...

    @abstractmethod
    async def send_dm(
        self,
        linkedin_profile_id: str,
        message: str,
    ) -> LinkedInSendResult:
        """Envia uma DM de texto."""
        ...

    @abstractmethod
    async def send_voice_note(
        self,
        linkedin_profile_id: str,
        audio_url: str,
    ) -> LinkedInSendResult:
        """
        Envia uma voice note.
        audio_url deve ser uma URL pública acessível (ex: S3).
        """
        ...

    @abstractmethod
    async def send_dm_with_attachments(
        self,
        linkedin_profile_id: str,
        message: str,
        attachments: list[tuple[str, bytes, str]],
    ) -> LinkedInSendResult:
        """
        Envia DM com texto + arquivos.
        attachments: list of (filename, file_bytes, content_type)
        """
        ...

    @abstractmethod
    async def send_inmail(
        self,
        linkedin_profile_id: str,
        subject: str,
        body: str,
    ) -> LinkedInSendResult:
        """Envia InMail (requer conta Premium)."""
        ...

    # ── Posts ─────────────────────────────────────────────────────────

    @abstractmethod
    async def react_to_latest_post(
        self,
        linkedin_profile_id: str,
        reaction: str = "LIKE",
    ) -> LinkedInSendResult:
        """Reage ao post mais recente do perfil."""
        ...

    @abstractmethod
    async def comment_on_latest_post(
        self,
        linkedin_profile_id: str,
        comment: str,
    ) -> LinkedInSendResult:
        """Comenta no post mais recente do perfil."""
        ...

    @abstractmethod
    async def get_lead_posts(
        self,
        linkedin_profile_id: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Retorna posts recentes do lead."""
        ...

    # ── Perfil e relação ──────────────────────────────────────────────

    @abstractmethod
    async def get_profile(
        self,
        linkedin_url: str,
    ) -> LinkedInProfile | None:
        """Resolve URL do LinkedIn → dados do perfil."""
        ...

    @abstractmethod
    async def get_relation_status(
        self,
        linkedin_profile_id: str,
    ) -> str | None:
        """
        Verifica status da relação.
        Retorna "CONNECTED" | "PENDING" | None.
        """
        ...

    # ── Inbox ─────────────────────────────────────────────────────────

    @abstractmethod
    async def list_conversations(
        self,
        cursor: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """
        Lista conversas.
        Retorna dict com 'items' (list[LinkedInConversation]) e 'cursor'.
        """
        ...

    @abstractmethod
    async def get_messages(
        self,
        conversation_id: str,
        limit: int = 50,
        cursor: str | None = None,
    ) -> list[LinkedInMessage]:
        """Retorna histórico de mensagens de uma conversa."""
        ...

    @abstractmethod
    async def add_reaction(
        self,
        message_id: str,
        emoji: str,
    ) -> bool:
        """Adiciona reação a uma mensagem."""
        ...

    @abstractmethod
    async def remove_reaction(
        self,
        message_id: str,
    ) -> bool:
        """Remove reação de uma mensagem."""
        ...

    # ── Busca ─────────────────────────────────────────────────────────

    @abstractmethod
    async def search_profiles(
        self,
        query: str,
        limit: int = 20,
        filters: dict[str, Any] | None = None,
    ) -> list[LinkedInProfile]:
        """Busca perfis por palavra-chave e filtros."""
        ...

    # ── Saúde ─────────────────────────────────────────────────────────

    @abstractmethod
    async def ping(self) -> bool:
        """Verifica se a conta está ativa e autenticada."""
        ...
