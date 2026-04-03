"""
integrations/email/unipile_provider.py

Implementação do EmailProvider usando a API Unipile (conta Gmail conectada).
Usa o UnipileClient existente como backend de transporte.
"""

from __future__ import annotations

import structlog

from integrations.email.base import EmailProvider, EmailSendResult

logger = structlog.get_logger()


class UnipileEmailProvider(EmailProvider):
    """
    Envia e-mails via Unipile usando uma conta Gmail conectada.
    Requer que o tenant tenha configurado o account_id Unipile do Gmail.
    """

    def __init__(self, account_id: str) -> None:
        self._account_id = account_id

    @property
    def provider_name(self) -> str:
        return "unipile_gmail"

    async def send(
        self,
        to_email: str,
        subject: str,
        body_html: str,
        from_name: str | None = None,
        reply_to: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> EmailSendResult:
        from integrations.unipile_client import unipile_client  # noqa: PLC0415

        try:
            result = await unipile_client.send_email(
                account_id=self._account_id,
                to_email=to_email,
                subject=subject,
                body_html=body_html,
            )
            return EmailSendResult(
                success=result.success,
                message_id=result.message_id,
                provider=self.provider_name,
            )
        except Exception as exc:
            logger.error(
                "email.unipile_provider.send_failed",
                to=to_email,
                error=str(exc),
            )
            return EmailSendResult(
                success=False,
                provider=self.provider_name,
                error=str(exc),
            )

    async def ping(self) -> bool:
        """Verifica se a conta Unipile está ativa (via list messages com limit=1)."""
        from integrations.unipile_client import unipile_client  # noqa: PLC0415

        try:
            # Tenta buscar 1 email para verificar se a conta existe
            result = await unipile_client.get_account_status(self._account_id)
            return result is not None
        except Exception:
            return False
