from __future__ import annotations

import uuid
from dataclasses import dataclass

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from integrations.email import EmailRegistry
from integrations.unipile_client import unipile_client
from models.cadence import Cadence
from models.email_account import EmailAccount
from models.tenant import TenantIntegration
from services.email_account_service import resolve_outbound_email_account
from services.message_quality import normalize_email_subject, plain_text_email_to_html

logger = structlog.get_logger()


@dataclass
class EmailTestSendResult:
    to_email: str
    subject: str
    provider_type: str
    body_is_html: bool


def _append_signature(body_html: str, signature_html: str | None) -> str:
    if not signature_html or not signature_html.strip():
        return body_html

    signature_block = f'\n<div style="margin-top:24px;">{signature_html}</div>'
    lower_html = body_html.lower()
    if "</body>" in lower_html:
        index = lower_html.rfind("</body>")
        return body_html[:index] + signature_block + body_html[index:]
    return body_html + signature_block


async def send_test_email(
    *,
    db: AsyncSession,
    cadence: Cadence,
    tenant_id: uuid.UUID,
    to_email: str,
    subject: str,
    body: str,
    body_is_html: bool,
) -> EmailTestSendResult:
    normalized_to = to_email.strip().lower()
    normalized_subject = normalize_email_subject(subject)

    if not normalized_to:
        raise ValueError("to_email é obrigatório para enviar teste.")
    if not normalized_subject:
        raise ValueError("O assunto do teste não pode ficar vazio.")
    if not body or not body.strip():
        raise ValueError("O corpo do teste não pode ficar vazio.")

    rendered_body_html = body if body_is_html else plain_text_email_to_html(body)

    if cadence.email_account_id:
        account_result = await db.execute(
            select(EmailAccount).where(
                EmailAccount.id == cadence.email_account_id,
                EmailAccount.tenant_id == tenant_id,
                EmailAccount.is_active.is_(True),
            )
        )
        email_account = account_result.scalar_one_or_none()
        if email_account is None:
            raise ValueError("Conta de e-mail da cadência não encontrada ou inativa.")

        outbound_account = await resolve_outbound_email_account(db, email_account)
        signature_html = (
            getattr(outbound_account, "email_signature", None)
            or getattr(email_account, "email_signature", None)
        )
        rendered_body_html = _append_signature(rendered_body_html, signature_html)

        registry = EmailRegistry(settings=settings)
        await registry.send(
            account=outbound_account,
            to_email=normalized_to,
            subject=normalized_subject,
            body_html=rendered_body_html,
            from_name=outbound_account.from_name or outbound_account.display_name,
        )
        provider_type = getattr(outbound_account.provider_type, "value", outbound_account.provider_type)
        logger.info(
            "test_email.sent",
            cadence_id=str(cadence.id),
            tenant_id=str(tenant_id),
            to_email=normalized_to,
            provider_type=str(provider_type),
            source="email_account",
        )
        return EmailTestSendResult(
            to_email=normalized_to,
            subject=normalized_subject,
            provider_type=str(provider_type),
            body_is_html=body_is_html,
        )

    integration_result = await db.execute(
        select(TenantIntegration).where(TenantIntegration.tenant_id == tenant_id)
    )
    integration = integration_result.scalar_one_or_none()
    gmail_account_id = (
        (integration and integration.unipile_gmail_account_id)
        or settings.UNIPILE_ACCOUNT_ID_GMAIL
        or ""
    )
    if not gmail_account_id:
        raise ValueError("Nenhuma conta de e-mail configurada para enviar teste.")

    await unipile_client.send_email(
        account_id=gmail_account_id,
        to_email=normalized_to,
        subject=normalized_subject,
        body_html=rendered_body_html,
    )
    logger.info(
        "test_email.sent",
        cadence_id=str(cadence.id),
        tenant_id=str(tenant_id),
        to_email=normalized_to,
        provider_type="unipile_gmail",
        source="tenant_integration",
    )
    return EmailTestSendResult(
        to_email=normalized_to,
        subject=normalized_subject,
        provider_type="unipile_gmail",
        body_is_html=body_is_html,
    )