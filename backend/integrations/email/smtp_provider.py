"""
integrations/email/smtp_provider.py

Implementação EmailProvider via SMTP direto (aiosmtplib).
Suporta SMTP plano, SMTPS (SSL) e STARTTLS.

Dependência: aiosmtplib
"""

from __future__ import annotations

import email as email_lib

import structlog

from integrations.email.base import EmailProvider, EmailSendResult

logger = structlog.get_logger()


class SMTPEmailProvider(EmailProvider):
    """
    Envia e-mails via SMTP usando aiosmtplib (assíncrono).
    Suporta SSL/TLS e STARTTLS.
    """

    def __init__(
        self,
        email_address: str,
        smtp_host: str,
        smtp_port: int,
        smtp_username: str,
        smtp_password: str,
        smtp_use_tls: bool = True,
    ) -> None:
        self._email_address = email_address
        self._host = smtp_host
        self._port = smtp_port
        self._username = smtp_username
        self._password = smtp_password
        self._use_tls = smtp_use_tls

    @property
    def provider_name(self) -> str:
        return "smtp"

    def _build_message(
        self,
        to_email: str,
        subject: str,
        body_html: str,
        from_name: str | None = None,
        reply_to: str | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> email_lib.message.EmailMessage:
        msg = email_lib.message.EmailMessage()
        sender = f"{from_name} <{self._email_address}>" if from_name else self._email_address
        msg["From"] = sender
        msg["To"] = to_email
        msg["Subject"] = subject
        if reply_to:
            msg["Reply-To"] = reply_to
        if extra_headers:
            for k, v in extra_headers.items():
                msg[k] = v
        msg.set_content(body_html, subtype="html", charset="utf-8")
        return msg

    async def send(
        self,
        to_email: str,
        subject: str,
        body_html: str,
        from_name: str | None = None,
        reply_to: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> EmailSendResult:
        try:
            import aiosmtplib  # noqa: PLC0415

            msg = self._build_message(to_email, subject, body_html, from_name, reply_to, headers)

            await aiosmtplib.send(
                msg,
                hostname=self._host,
                port=self._port,
                username=self._username,
                password=self._password,
                use_tls=self._use_tls,
                start_tls=not self._use_tls and self._port == 587,
                timeout=30,
            )

            logger.info("email.smtp_provider.sent", to=to_email, host=self._host, port=self._port)
            return EmailSendResult(
                success=True,
                provider=self.provider_name,
            )
        except Exception as exc:
            logger.error(
                "email.smtp_provider.send_failed",
                to=to_email,
                host=self._host,
                port=self._port,
                error=str(exc),
            )
            return EmailSendResult(
                success=False,
                provider=self.provider_name,
                error=str(exc),
            )

    async def ping(self) -> bool:
        """Verifica conectividade SMTP com EHLO sem enviar e-mail."""
        try:
            import aiosmtplib  # noqa: PLC0415

            client = aiosmtplib.SMTP(
                hostname=self._host,
                port=self._port,
                use_tls=self._use_tls,
                timeout=10,
            )
            async with client:
                await client.login(self._username, self._password)
            return True
        except Exception:
            return False
