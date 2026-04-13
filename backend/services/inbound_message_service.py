from __future__ import annotations

import uuid
from dataclasses import dataclass

import structlog
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from integrations.llm import LLMRegistry
from models.cadence_step import CadenceStep
from models.email_account import EmailAccount
from models.enums import Channel, Intent, InteractionDirection, LeadStatus, StepStatus
from models.interaction import Interaction
from models.lead import Lead
from models.lead_email import LeadEmail
from models.linkedin_account import LinkedInAccount
from models.tenant import Tenant, TenantIntegration
from services.llm_config import resolve_tenant_llm_config
from services.reply_parser import ReplyParser

logger = structlog.get_logger()

_LINKEDIN_ACCOUNT_TYPE = "LINKEDIN"
_EMAIL_ACCOUNT_TYPE = "GMAIL"


@dataclass(frozen=True, slots=True)
class UnipileAccountContext:
    tenant_id: uuid.UUID
    channel: Channel


@dataclass(frozen=True, slots=True)
class InboundReplyResult:
    intent: Intent
    classification: dict


async def resolve_unipile_account_context(
    account_id: str,
    db: AsyncSession,
    *,
    account_type: str | None = None,
    sender_id: str | None = None,
) -> UnipileAccountContext | None:
    normalized_account_id = (account_id or "").strip()
    normalized_account_type = _normalize_unipile_account_type(account_type)
    matches: set[tuple[uuid.UUID, Channel]] = set()

    if normalized_account_id:
        matches.update(await _load_unipile_account_matches(normalized_account_id, db))

        if not matches:
            global_channel = _channel_for_global_unipile_account(normalized_account_id)
            if global_channel is not None:
                tenant_id = await _resolve_single_active_tenant_id(db)
                if tenant_id is not None:
                    matches.add((tenant_id, global_channel))

    if not matches:
        inferred_channel = _infer_channel(normalized_account_type, sender_id)
        tenant_id = await _resolve_single_active_tenant_id(db)
        if tenant_id is not None and inferred_channel is not None:
            return UnipileAccountContext(tenant_id=tenant_id, channel=inferred_channel)
        return None

    filtered_matches = _filter_matches(matches, normalized_account_type, sender_id)
    if len(filtered_matches) == 1:
        tenant_id, channel = next(iter(filtered_matches))
        return UnipileAccountContext(tenant_id=tenant_id, channel=channel)

    tenant_ids = {tenant_id for tenant_id, _ in filtered_matches}
    channels = sorted(channel.value for _, channel in filtered_matches)
    logger.error(
        "inbound.unipile.account_ambiguous",
        account_id=normalized_account_id or None,
        account_type=normalized_account_type or None,
        sender_id=sender_id or None,
        tenant_count=len(tenant_ids),
        channels=channels,
    )
    return None


async def find_lead_by_sender(
    sender_id: str,
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> Lead | None:
    if not sender_id:
        return None

    sender_normalized = sender_id.strip()
    if not sender_normalized:
        return None

    if "@" in sender_normalized:
        return await find_lead_by_email(sender_normalized, tenant_id, db)

    result = await db.execute(
        select(Lead).where(
            Lead.tenant_id == tenant_id,
            Lead.linkedin_profile_id == sender_normalized,
        )
    )
    return result.scalar_one_or_none()


async def find_lead_by_email(
    email: str,
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> Lead | None:
    normalized_email = email.strip().lower()
    if not normalized_email:
        return None

    result = await db.execute(
        select(Lead).where(
            Lead.tenant_id == tenant_id,
            or_(
                func.lower(Lead.email_corporate) == normalized_email,
                func.lower(Lead.email_personal) == normalized_email,
            ),
        )
    )
    lead = result.scalar_one_or_none()
    if lead is not None:
        return lead

    result = await db.execute(
        select(Lead)
        .join(LeadEmail, LeadEmail.lead_id == Lead.id)
        .where(
            Lead.tenant_id == tenant_id,
            func.lower(LeadEmail.email) == normalized_email,
        )
        .limit(1)
    )
    return result.scalar_one_or_none()


async def mark_latest_step_replied(
    lead_id: uuid.UUID,
    tenant_id: uuid.UUID,
    channel: Channel,
    db: AsyncSession,
) -> CadenceStep | None:
    step_channels = _step_channels_for_inbound_channel(channel)
    result = await db.execute(
        select(CadenceStep)
        .where(
            CadenceStep.lead_id == lead_id,
            CadenceStep.tenant_id == tenant_id,
            CadenceStep.channel.in_(step_channels),
            CadenceStep.status == StepStatus.SENT,
        )
        .order_by(CadenceStep.sent_at.desc().nulls_last(), CadenceStep.scheduled_at.desc())
        .limit(1)
    )
    latest_step = result.scalar_one_or_none()
    if latest_step is not None:
        latest_step.status = StepStatus.REPLIED
    return latest_step


async def process_inbound_reply(
    *,
    db: AsyncSession,
    registry: LLMRegistry,
    tenant_id: uuid.UUID,
    lead: Lead,
    channel: Channel,
    reply_text: str,
    external_message_id: str | None,
) -> InboundReplyResult:
    llm_config = await resolve_tenant_llm_config(db, lead.tenant_id)
    parser = ReplyParser(
        registry=registry,
        provider=llm_config.provider,
        model=llm_config.model,
    )
    classification = await parser.classify(
        reply_text=reply_text,
        lead_name=lead.name,
        tenant_id=str(lead.tenant_id),
        lead_id=str(lead.id),
        channel=channel.value,
    )

    intent_str = str(classification.get("intent") or Intent.NEUTRAL.value).upper()
    try:
        intent = Intent[intent_str]
    except KeyError:
        intent = Intent.NEUTRAL

    interaction = Interaction(
        tenant_id=tenant_id,
        lead_id=lead.id,
        channel=channel,
        direction=InteractionDirection.INBOUND,
        content_text=reply_text,
        intent=intent,
        unipile_message_id=external_message_id,
    )
    db.add(interaction)

    await mark_latest_step_replied(
        lead_id=lead.id,
        tenant_id=tenant_id,
        channel=channel,
        db=db,
    )

    if intent == Intent.INTEREST:
        lead.status = LeadStatus.CONVERTED
    elif intent == Intent.NOT_INTERESTED:
        lead.status = LeadStatus.ARCHIVED

    await db.commit()

    if intent in (Intent.INTEREST, Intent.OBJECTION):
        from services.notification import send_reply_notification

        await send_reply_notification(
            lead=lead,
            intent=intent.value,
            reply_text=reply_text,
            tenant_id=tenant_id,
            db=db,
        )

    from api.routes.ws import broadcast_event

    await broadcast_event(
        str(tenant_id),
        {
            "type": "new_message",
            "lead_id": str(lead.id),
            "lead_name": lead.name,
            "channel": channel.value,
            "intent": intent.value,
            "text_preview": reply_text[:100],
        },
    )

    logger.info(
        "inbound.reply.processed",
        lead_id=str(lead.id),
        tenant_id=str(tenant_id),
        channel=channel.value,
        intent=intent.value,
        confidence=classification.get("confidence"),
        summary=classification.get("summary"),
    )
    return InboundReplyResult(intent=intent, classification=classification)


async def _load_unipile_account_matches(
    account_id: str,
    db: AsyncSession,
) -> set[tuple[uuid.UUID, Channel]]:
    linkedin_rows = await db.execute(
        select(LinkedInAccount.tenant_id).where(
            LinkedInAccount.unipile_account_id == account_id,
            LinkedInAccount.provider_type == "unipile",
        )
    )
    email_rows = await db.execute(
        select(EmailAccount.tenant_id).where(
            EmailAccount.unipile_account_id == account_id,
            EmailAccount.provider_type == "unipile_gmail",
        )
    )
    integration_rows = await db.execute(
        select(
            TenantIntegration.tenant_id,
            TenantIntegration.unipile_linkedin_account_id,
            TenantIntegration.unipile_gmail_account_id,
        ).where(
            or_(
                TenantIntegration.unipile_linkedin_account_id == account_id,
                TenantIntegration.unipile_gmail_account_id == account_id,
            )
        )
    )

    matches: set[tuple[uuid.UUID, Channel]] = {
        (tenant_id, Channel.LINKEDIN_DM) for tenant_id in linkedin_rows.scalars().all()
    }
    matches.update((tenant_id, Channel.EMAIL) for tenant_id in email_rows.scalars().all())

    for tenant_id, linkedin_account_id, gmail_account_id in integration_rows.all():
        if linkedin_account_id == account_id:
            matches.add((tenant_id, Channel.LINKEDIN_DM))
        if gmail_account_id == account_id:
            matches.add((tenant_id, Channel.EMAIL))

    return matches


async def _resolve_single_active_tenant_id(db: AsyncSession) -> uuid.UUID | None:
    result = await db.execute(
        select(Tenant.id)
        .where(Tenant.is_active.is_(True))
        .order_by(Tenant.created_at.asc())
        .limit(2)
    )
    tenant_ids = result.scalars().all()
    if len(tenant_ids) == 1:
        return tenant_ids[0]
    return None


def _normalize_unipile_account_type(account_type: str | None) -> str | None:
    normalized = (account_type or "").strip().upper()
    return normalized or None


def _channel_for_global_unipile_account(account_id: str) -> Channel | None:
    from core.config import settings

    if account_id and account_id == (settings.UNIPILE_ACCOUNT_ID_GMAIL or ""):
        return Channel.EMAIL
    if account_id and account_id == (settings.UNIPILE_ACCOUNT_ID_LINKEDIN or ""):
        return Channel.LINKEDIN_DM
    return None


def _infer_channel(account_type: str | None, sender_id: str | None) -> Channel | None:
    if account_type == _EMAIL_ACCOUNT_TYPE:
        return Channel.EMAIL
    if account_type == _LINKEDIN_ACCOUNT_TYPE:
        return Channel.LINKEDIN_DM
    if sender_id and "@" in sender_id:
        return Channel.EMAIL
    if sender_id:
        return Channel.LINKEDIN_DM
    return None


def _filter_matches(
    matches: set[tuple[uuid.UUID, Channel]],
    account_type: str | None,
    sender_id: str | None,
) -> set[tuple[uuid.UUID, Channel]]:
    expected_channel = _infer_channel(account_type, sender_id)
    if expected_channel is None:
        return matches
    filtered = {match for match in matches if match[1] == expected_channel}
    return filtered or matches


def _step_channels_for_inbound_channel(channel: Channel) -> tuple[Channel, ...]:
    if channel == Channel.LINKEDIN_DM:
        return (Channel.LINKEDIN_DM, Channel.LINKEDIN_CONNECT)
    return (channel,)
