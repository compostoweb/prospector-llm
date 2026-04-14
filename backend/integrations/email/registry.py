"""
integrations/email/registry.py

EmailRegistry — único ponto de acesso para envio de e-mails no sistema.

Recebe um EmailAccount (modelo SQLAlchemy) e devolve o provider correto
baseado em EmailAccount.provider_type.

Uso:
    registry = EmailRegistry(settings=settings)
    result = await registry.send(account, to_email, subject, body_html)
"""

from __future__ import annotations

import structlog

from integrations.email.base import EmailProvider, EmailSendResult

logger = structlog.get_logger()


class EmailRegistry:
    """
    Ponto central de envio de e-mails.
    Resolve o provider correto baseado em EmailAccount.provider_type.
    """

    def __init__(self, settings) -> None:  # type: ignore[type-arg]
        self._settings = settings

    def _build_provider(self, account) -> EmailProvider:  # type: ignore[return]
        """Constrói o EmailProvider correto para a conta."""
        from models.enums import EmailProviderType  # noqa: PLC0415

        provider_type = account.provider_type

        if provider_type == EmailProviderType.UNIPILE_GMAIL:
            from integrations.email.unipile_provider import UnipileEmailProvider  # noqa: PLC0415

            return UnipileEmailProvider(account_id=account.unipile_account_id or "")

        if provider_type == EmailProviderType.GOOGLE_OAUTH:
            from integrations.email.gmail_provider import GmailDirectProvider  # noqa: PLC0415
            from services.email_account_service import decrypt_credential  # noqa: PLC0415

            refresh_token = (
                decrypt_credential(account.google_refresh_token, self._settings)
                if account.google_refresh_token
                else ""
            )
            return GmailDirectProvider(
                email_address=account.email_address,
                refresh_token=refresh_token,
                client_id=self._settings.GOOGLE_CLIENT_ID_EMAIL or "",
                client_secret=self._settings.GOOGLE_CLIENT_SECRET_EMAIL or "",
            )

        if provider_type == EmailProviderType.SMTP:
            from integrations.email.smtp_provider import SMTPEmailProvider  # noqa: PLC0415
            from services.email_account_service import decrypt_credential  # noqa: PLC0415

            smtp_password = (
                decrypt_credential(account.smtp_password, self._settings)
                if account.smtp_password
                else ""
            )
            return SMTPEmailProvider(
                email_address=account.email_address,
                smtp_host=account.smtp_host or "",
                smtp_port=account.smtp_port or 587,
                smtp_username=account.smtp_username or "",
                smtp_password=smtp_password,
                smtp_use_tls=account.smtp_use_tls,
            )

        raise ValueError(f"Provider de e-mail não suportado: {provider_type}")

    async def send(
        self,
        account,  # EmailAccount model instance
        to_email: str,
        subject: str,
        body_html: str,
        from_name: str | None = None,
        reply_to: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> EmailSendResult:
        """
        Envia um e-mail usando a conta e provider corretos.
        O registry resolve internamente qual SDK/protocolo usar.
        """
        provider = self._build_provider(account)
        logger.debug(
            "email.registry.send",
            provider=provider.provider_name,
            account_id=str(getattr(account, "id", "")),
            to=to_email,
        )
        return await provider.send(
            to_email=to_email,
            subject=subject,
            body_html=body_html,
            from_name=from_name,
            reply_to=reply_to,
            headers=headers,
        )

    async def ping(self, account) -> bool:
        """Verifica se a conta consegue enviar."""
        provider = self._build_provider(account)
        return await provider.ping()
