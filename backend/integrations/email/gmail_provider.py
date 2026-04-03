"""
integrations/email/gmail_provider.py

Implementação EmailProvider via Gmail API direta (Google OAuth2).
Usa refresh_token armazenado na EmailAccount para obter access_token just-in-time.

Dependências: google-auth, google-auth-httplib2, google-api-python-client
"""

from __future__ import annotations

import base64
import email as email_lib
import structlog

from integrations.email.base import EmailProvider, EmailSendResult

logger = structlog.get_logger()


class GmailDirectProvider(EmailProvider):
    """
    Envia e-mails via Gmail API usando refresh_token OAuth2.
    O token de acesso é obtido automaticamente (just-in-time) a cada envio.
    """

    def __init__(
        self,
        email_address: str,
        refresh_token: str,
        client_id: str,
        client_secret: str,
    ) -> None:
        self._email_address = email_address
        self._refresh_token = refresh_token
        self._client_id = client_id
        self._client_secret = client_secret

    @property
    def provider_name(self) -> str:
        return "google_oauth"

    def _build_credentials(self):  # type: ignore[return]
        """Cria credenciais Google a partir do refresh_token."""
        from google.oauth2.credentials import Credentials  # noqa: PLC0415

        return Credentials(
            token=None,
            refresh_token=self._refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self._client_id,
            client_secret=self._client_secret,
            scopes=["https://www.googleapis.com/auth/gmail.send"],
        )

    def _build_message(
        self,
        to_email: str,
        subject: str,
        body_html: str,
        from_name: str | None = None,
        reply_to: str | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, str]:
        """Constrói o objeto de mensagem no formato esperado pela Gmail API."""
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
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        return {"raw": raw}

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
            import asyncio  # noqa: PLC0415
            from google.auth.transport.requests import Request  # noqa: PLC0415
            from googleapiclient.discovery import build  # noqa: PLC0415

            creds = self._build_credentials()

            # Refresh síncrono (roda em executor para não bloquear)
            def _refresh_and_build():
                if not creds.valid:
                    creds.refresh(Request())
                service = build("gmail", "v1", credentials=creds, cache_discovery=False)
                message = self._build_message(to_email, subject, body_html, from_name, reply_to, headers)
                result = service.users().messages().send(userId="me", body=message).execute()
                return result

            result = await asyncio.get_event_loop().run_in_executor(None, _refresh_and_build)

            logger.info(
                "email.gmail_provider.sent",
                to=to_email,
                message_id=result.get("id"),
            )
            return EmailSendResult(
                success=True,
                message_id=result.get("id"),
                provider=self.provider_name,
                raw=result,
            )
        except Exception as exc:
            logger.error(
                "email.gmail_provider.send_failed",
                to=to_email,
                error=str(exc),
            )
            return EmailSendResult(
                success=False,
                provider=self.provider_name,
                error=str(exc),
            )

    async def ping(self) -> bool:
        """Verifica se as credenciais Google são válidas obtendo o perfil Gmail."""
        try:
            import asyncio  # noqa: PLC0415
            from google.auth.transport.requests import Request  # noqa: PLC0415
            from googleapiclient.discovery import build  # noqa: PLC0415

            creds = self._build_credentials()

            def _check():
                creds.refresh(Request())
                service = build("gmail", "v1", credentials=creds, cache_discovery=False)
                profile = service.users().getProfile(userId="me").execute()
                return bool(profile.get("emailAddress"))

            return await asyncio.get_event_loop().run_in_executor(None, _check)
        except Exception:
            return False
