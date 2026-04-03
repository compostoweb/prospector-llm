"""
integrations/email/base.py

Contrato base para todos os provedores de e-mail.
Cada provedor implementa esta interface — o restante do sistema
nunca importa clientes diretamente, só usa EmailProvider via EmailRegistry.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class EmailSendResult:
    """Resultado normalizado de qualquer provedor de e-mail."""
    success: bool
    message_id: str | None = None
    provider: str = ""
    error: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


class EmailProvider(ABC):
    """Interface base para provedores de envio de e-mail."""

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @abstractmethod
    async def send(
        self,
        to_email: str,
        subject: str,
        body_html: str,
        from_name: str | None = None,
        reply_to: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> EmailSendResult:
        """
        Envia um e-mail.

        Args:
            to_email: Destinatário.
            subject: Assunto.
            body_html: Corpo em HTML.
            from_name: Nome do remetente (opcional, usa padrão da conta).
            reply_to: Reply-To override (opcional).
            headers: Headers extras como X-Warmup-Campaign (opcional).
        """
        ...

    @abstractmethod
    async def ping(self) -> bool:
        """Verifica se a conta consegue enviar (sem enviar e-mail)."""
        ...
