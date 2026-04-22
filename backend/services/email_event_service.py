from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.email_unsubscribe import EmailUnsubscribe
from models.enums import EmailProviderType
from models.interaction import Interaction
from models.lead import Lead

logger = structlog.get_logger()

_NDR_SENDERS = (
    "mailer-daemon@",
    "postmaster@",
    "mail-daemon@",
    "mailerdaemon@",
    "noreply@bounce",
    "bounce@",
    "no-reply@bounce",
)

_NDR_SUBJECTS = (
    "delivery status notification",
    "delivery failure",
    "mail delivery failed",
    "mail delivery failure",
    "undeliverable",
    "returned mail",
    "failure notice",
    "non-delivery report",
    "unable to deliver",
    "message not delivered",
    "entrega falhou",
    "mensagem não entregue",
)


@dataclass(frozen=True, slots=True)
class EmailProviderCapabilities:
    provider_type: str
    reply_detection_source: str
    bounce_detection_source: str
    open_tracking_source: str
    unsubscribe_source: str
    supports_delivery_confirmation: bool
    delivery_semantics: str
    observable_events: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ClassifiedInboundEmailEvent:
    kind: str
    matched_email: str | None = None
    bounce_type: str | None = None


@dataclass(frozen=True, slots=True)
class OutboundEmailDeliveryObservation:
    state: str
    confirmed: bool
    semantics: str
    observable_events: tuple[str, ...]


def normalize_email_address(value: str | None) -> str:
    return (value or "").strip().lower()


def get_email_provider_capabilities(
    provider_type: EmailProviderType | str | None,
) -> EmailProviderCapabilities:
    normalized = _normalize_provider_type(provider_type)

    if normalized == EmailProviderType.UNIPILE_GMAIL.value:
        return EmailProviderCapabilities(
            provider_type=normalized,
            reply_detection_source="unipile_webhook_mail_received",
            bounce_detection_source="unipile_webhook_mail_received_or_inbox_poll",
            open_tracking_source="tracking_pixel",
            unsubscribe_source="tracking_link",
            supports_delivery_confirmation=False,
            delivery_semantics="accepted_by_provider",
            observable_events=("reply", "bounce", "opened", "unsubscribe"),
        )

    if normalized == EmailProviderType.GOOGLE_OAUTH.value:
        return EmailProviderCapabilities(
            provider_type=normalized,
            reply_detection_source="gmail_history_poll",
            bounce_detection_source="gmail_history_poll",
            open_tracking_source="tracking_pixel",
            unsubscribe_source="tracking_link",
            supports_delivery_confirmation=False,
            delivery_semantics="accepted_by_gmail_api",
            observable_events=("reply", "bounce", "opened", "unsubscribe"),
        )

    if normalized == EmailProviderType.SMTP.value:
        return EmailProviderCapabilities(
            provider_type=normalized,
            reply_detection_source="imap_poll",
            bounce_detection_source="imap_poll",
            open_tracking_source="tracking_pixel",
            unsubscribe_source="tracking_link",
            supports_delivery_confirmation=False,
            delivery_semantics="accepted_by_smtp_server",
            observable_events=("reply", "bounce", "opened", "unsubscribe"),
        )

    return EmailProviderCapabilities(
        provider_type=normalized,
        reply_detection_source="unknown",
        bounce_detection_source="unknown",
        open_tracking_source="tracking_pixel",
        unsubscribe_source="tracking_link",
        supports_delivery_confirmation=False,
        delivery_semantics="accepted_for_delivery",
        observable_events=("reply", "bounce", "opened", "unsubscribe"),
    )


def build_outbound_email_delivery_observation(
    provider_type: EmailProviderType | str | None,
    *,
    success: bool,
) -> OutboundEmailDeliveryObservation:
    capabilities = get_email_provider_capabilities(provider_type)
    return OutboundEmailDeliveryObservation(
        state="accepted" if success else "failed",
        confirmed=False,
        semantics=capabilities.delivery_semantics,
        observable_events=capabilities.observable_events,
    )


def classify_inbound_email_event(
    *,
    from_email: str,
    subject: str,
    body: str,
) -> ClassifiedInboundEmailEvent:
    if not body.strip():
        return ClassifiedInboundEmailEvent(kind="ignored")

    if _is_ndr_message(from_email=from_email, subject=subject, body=body):
        return ClassifiedInboundEmailEvent(
            kind="bounce",
            matched_email=_extract_bounced_email(body),
            bounce_type="hard",
        )

    return ClassifiedInboundEmailEvent(kind="reply")


async def mark_email_opened(
    db: AsyncSession,
    interaction_id: uuid.UUID,
) -> Interaction | None:
    result = await db.execute(select(Interaction).where(Interaction.id == interaction_id))
    interaction = result.scalar_one_or_none()
    if interaction is None:
        return None

    if interaction.opened:
        return interaction

    interaction.opened = True
    interaction.opened_at = datetime.now(UTC)
    await db.commit()
    logger.info(
        "email.opened",
        interaction_id=str(interaction_id),
        lead_id=str(interaction.lead_id),
    )
    return interaction


async def record_email_unsubscribe(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    email: str,
) -> bool:
    normalized_email = normalize_email_address(email)
    if not normalized_email:
        return False

    existing = await db.execute(
        select(EmailUnsubscribe).where(
            EmailUnsubscribe.tenant_id == tenant_id,
            EmailUnsubscribe.email == normalized_email,
        )
    )
    if existing.scalar_one_or_none() is not None:
        return False

    db.add(
        EmailUnsubscribe(
            tenant_id=tenant_id,
            email=normalized_email,
        )
    )
    await db.commit()
    logger.info("email.unsubscribed", tenant_id=str(tenant_id), email=normalized_email)
    return True


async def record_email_bounce(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    bounced_email: str,
    *,
    source: str,
    bounce_type: str = "hard",
) -> Lead | None:
    normalized_email = normalize_email_address(bounced_email)
    if not normalized_email:
        return None

    from services.inbound_message_service import find_lead_by_email

    lead = await find_lead_by_email(normalized_email, tenant_id, db)
    if lead is None:
        logger.info(
            "email.bounce.lead_not_found",
            tenant_id=str(tenant_id),
            bounced_email=normalized_email,
            source=source,
        )
        return None

    if lead.email_bounced_at is None:
        lead.email_bounced_at = datetime.now(UTC)
        lead.email_bounce_type = bounce_type
        await db.commit()
        logger.info(
            "email.bounce.recorded",
            lead_id=str(lead.id),
            bounced_email=normalized_email,
            bounce_type=bounce_type,
            source=source,
        )

    return lead


def _normalize_provider_type(provider_type: EmailProviderType | str | None) -> str:
    if isinstance(provider_type, EmailProviderType):
        return provider_type.value
    return str(provider_type or "").strip().lower()


def _is_ndr_message(from_email: str, subject: str, body: str) -> bool:
    sender = normalize_email_address(from_email)
    if any(sender.startswith(prefix) for prefix in _NDR_SENDERS):
        return True

    subject_lc = subject.strip().lower()
    if any(keyword in subject_lc for keyword in _NDR_SUBJECTS):
        return True

    body_lc = body.lower()
    if "content-type: message/delivery-status" in body_lc:
        return True

    return False


def _extract_bounced_email(body: str) -> str | None:
    patterns = [
        r"final-recipient:\s*rfc822;\s*([^\s\r\n]+)",
        r"x-failed-recipients?:\s*([^\s\r\n,]+)",
        r"original-recipient:\s*rfc822;\s*([^\s\r\n]+)",
        r"(?:nao foi entregue para|não foi entregue para|not delivered to|message wasn't delivered to|couldn't be delivered to|delivery to)\s*<?([^\s<>\r\n]+@[^\s<>\r\n]+)>?",
    ]
    body_lc = body.lower()
    for pattern in patterns:
        match = re.search(pattern, body_lc)
        if match:
            addr = match.group(1).strip().strip("<>")
            if "@" in addr:
                return addr

    fallback_candidates = re.findall(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z0-9-]{2,63}", body_lc)
    for candidate in fallback_candidates:
        normalized = candidate.strip().strip("<>")
        if any(normalized.startswith(prefix) for prefix in _NDR_SENDERS):
            continue
        return normalized
    return None
