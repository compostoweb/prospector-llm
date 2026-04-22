from __future__ import annotations

import re
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
from services.message_quality import normalize_email_subject
from services.reply_matching import reply_candidate_step_channels
from services.reply_parser import ReplyParser

logger = structlog.get_logger()

_LINKEDIN_ACCOUNT_TYPE = "LINKEDIN"
_EMAIL_ACCOUNT_TYPE = "GMAIL"
_EMAIL_REPLY_SUBJECT_PREFIX_RE = re.compile(
    r"^(?:(?:re|fw|fwd|aw|res)\s*:\s*)+",
    re.IGNORECASE,
)


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
    resolution = await _resolve_fallback_step_for_reply(
        lead_id=lead_id,
        tenant_id=tenant_id,
        channel=channel,
        db=db,
    )
    return resolution.step


async def pause_remaining_cadence_steps_after_reply(
    *,
    db: AsyncSession,
    tenant_id: uuid.UUID,
    lead_id: uuid.UUID,
    cadence_id: uuid.UUID,
    replied_step_id: uuid.UUID,
) -> int:
    result = await db.execute(
        select(CadenceStep).where(
            CadenceStep.tenant_id == tenant_id,
            CadenceStep.lead_id == lead_id,
            CadenceStep.cadence_id == cadence_id,
            CadenceStep.id != replied_step_id,
            CadenceStep.status.in_((StepStatus.PENDING, StepStatus.DISPATCHING)),
        )
    )
    remaining_steps = list(result.scalars().all())
    for remaining_step in remaining_steps:
        remaining_step.status = StepStatus.SKIPPED
    return len(remaining_steps)


async def process_inbound_reply(
    *,
    db: AsyncSession,
    registry: LLMRegistry,
    tenant_id: uuid.UUID,
    lead: Lead,
    channel: Channel,
    reply_text: str,
    external_message_id: str | None,
    reply_to_message_ids: list[str] | None = None,
    provider_thread_id: str | None = None,
    inbound_subject: str | None = None,
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

    reply_resolution = await resolve_replied_step_for_inbound_message(
        db=db,
        tenant_id=tenant_id,
        lead_id=lead.id,
        channel=channel,
        reply_to_message_ids=reply_to_message_ids or [],
        provider_thread_id=provider_thread_id,
        inbound_subject=inbound_subject,
    )
    replied_step = reply_resolution.step

    interaction = Interaction(
        tenant_id=tenant_id,
        lead_id=lead.id,
        cadence_step_id=replied_step.id if replied_step is not None else None,
        channel=channel,
        direction=InteractionDirection.INBOUND,
        content_text=reply_text,
        intent=intent,
        unipile_message_id=external_message_id,
        provider_thread_id=provider_thread_id,
        reply_match_status=reply_resolution.match_status,
        reply_match_source=reply_resolution.matched_via,
        reply_match_sent_cadence_count=(
            reply_resolution.sent_cadence_count if reply_resolution.sent_cadence_count > 0 else None
        ),
    )
    db.add(interaction)

    paused_steps = 0
    if replied_step is not None:
        paused_steps = await pause_remaining_cadence_steps_after_reply(
            db=db,
            tenant_id=tenant_id,
            lead_id=lead.id,
            cadence_id=replied_step.cadence_id,
            replied_step_id=replied_step.id,
        )

    if replied_step is not None and intent == Intent.INTEREST:
        lead.status = LeadStatus.CONVERTED
    elif replied_step is not None and intent == Intent.NOT_INTERESTED:
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

    if reply_resolution.ambiguous:
        await broadcast_event(
            str(tenant_id),
            {
                "type": "inbound.reply_ambiguous",
                "lead_id": str(lead.id),
                "lead_name": lead.name,
                "channel": channel.value,
                "sent_cadence_count": reply_resolution.sent_cadence_count,
            },
        )

    logger.info(
        "inbound.reply.processed",
        lead_id=str(lead.id),
        tenant_id=str(tenant_id),
        channel=channel.value,
        intent=intent.value,
        paused_steps=paused_steps,
        matched_step_id=str(replied_step.id) if replied_step is not None else None,
        reply_match_status=reply_resolution.match_status,
        reply_match_source=reply_resolution.matched_via,
        confidence=classification.get("confidence"),
        summary=classification.get("summary"),
    )
    return InboundReplyResult(intent=intent, classification=classification)


@dataclass(frozen=True, slots=True)
class RepliedStepResolution:
    step: CadenceStep | None
    ambiguous: bool = False
    sent_cadence_count: int = 0
    match_status: str = "unmatched"
    matched_via: str | None = None


async def resolve_replied_step_for_inbound_message(
    *,
    db: AsyncSession,
    tenant_id: uuid.UUID,
    lead_id: uuid.UUID,
    channel: Channel,
    reply_to_message_ids: list[str],
    provider_thread_id: str | None,
    inbound_subject: str | None = None,
) -> RepliedStepResolution:
    matched_step, matched_via = await _resolve_step_from_outbound_interaction(
        db=db,
        tenant_id=tenant_id,
        lead_id=lead_id,
        channel=channel,
        reply_to_message_ids=reply_to_message_ids,
        provider_thread_id=provider_thread_id,
    )
    if matched_step is not None:
        if matched_step.status == StepStatus.SENT:
            matched_step.status = StepStatus.REPLIED
        return RepliedStepResolution(
            step=matched_step,
            match_status="matched",
            matched_via=matched_via,
        )

    subject_resolution = await _resolve_email_step_from_subject(
        db=db,
        tenant_id=tenant_id,
        lead_id=lead_id,
        channel=channel,
        inbound_subject=inbound_subject,
    )
    if subject_resolution is not None:
        if (
            subject_resolution.step is not None
            and subject_resolution.step.status == StepStatus.SENT
        ):
            subject_resolution.step.status = StepStatus.REPLIED
        return subject_resolution

    return await _resolve_fallback_step_for_reply(
        lead_id=lead_id,
        tenant_id=tenant_id,
        channel=channel,
        db=db,
    )


async def _resolve_step_from_outbound_interaction(
    *,
    db: AsyncSession,
    tenant_id: uuid.UUID,
    lead_id: uuid.UUID,
    channel: Channel,
    reply_to_message_ids: list[str],
    provider_thread_id: str | None,
) -> tuple[CadenceStep | None, str | None]:
    step_channels = _step_channels_for_inbound_channel(channel)
    normalized_email_message_ids = [
        _normalize_email_message_id(value) for value in reply_to_message_ids
    ]
    normalized_email_message_ids = [value for value in normalized_email_message_ids if value]
    email_message_lookup_ids = list(
        dict.fromkeys(
            [value.strip().lower() for value in reply_to_message_ids if value and value.strip()]
            + normalized_email_message_ids
            + [f"<{value}>" for value in normalized_email_message_ids]
        )
    )
    raw_message_ids = [value.strip() for value in reply_to_message_ids if value and value.strip()]

    if email_message_lookup_ids:
        result = await db.execute(
            select(Interaction)
            .where(
                Interaction.tenant_id == tenant_id,
                Interaction.lead_id == lead_id,
                Interaction.direction == InteractionDirection.OUTBOUND,
                Interaction.channel.in_(step_channels),
                Interaction.cadence_step_id.is_not(None),
                func.lower(Interaction.email_message_id).in_(email_message_lookup_ids),
            )
            .order_by(Interaction.created_at.desc())
            .limit(1)
        )
        interaction = result.scalar_one_or_none()
        if interaction is not None and interaction.cadence_step_id is not None:
            return (
                await _load_step_by_id(db, interaction.cadence_step_id, tenant_id, lead_id),
                "email_message_id",
            )

    if raw_message_ids:
        result = await db.execute(
            select(Interaction)
            .where(
                Interaction.tenant_id == tenant_id,
                Interaction.lead_id == lead_id,
                Interaction.direction == InteractionDirection.OUTBOUND,
                Interaction.channel.in_(step_channels),
                Interaction.cadence_step_id.is_not(None),
                Interaction.unipile_message_id.in_(raw_message_ids),
            )
            .order_by(Interaction.created_at.desc())
            .limit(1)
        )
        interaction = result.scalar_one_or_none()
        if interaction is not None and interaction.cadence_step_id is not None:
            return (
                await _load_step_by_id(db, interaction.cadence_step_id, tenant_id, lead_id),
                "unipile_message_id",
            )

    normalized_thread_id = (provider_thread_id or "").strip()
    if normalized_thread_id:
        result = await db.execute(
            select(Interaction)
            .where(
                Interaction.tenant_id == tenant_id,
                Interaction.lead_id == lead_id,
                Interaction.direction == InteractionDirection.OUTBOUND,
                Interaction.channel.in_(step_channels),
                Interaction.cadence_step_id.is_not(None),
                Interaction.provider_thread_id == normalized_thread_id,
            )
            .order_by(Interaction.created_at.desc())
            .limit(1)
        )
        interaction = result.scalar_one_or_none()
        if interaction is not None and interaction.cadence_step_id is not None:
            return (
                await _load_step_by_id(db, interaction.cadence_step_id, tenant_id, lead_id),
                "provider_thread_id",
            )

    return None, None


async def _resolve_email_step_from_subject(
    *,
    db: AsyncSession,
    tenant_id: uuid.UUID,
    lead_id: uuid.UUID,
    channel: Channel,
    inbound_subject: str | None,
) -> RepliedStepResolution | None:
    if channel != Channel.EMAIL:
        return None

    normalized_subject = _normalize_email_subject_for_matching(inbound_subject)
    if not normalized_subject:
        return None

    result = await db.execute(
        select(CadenceStep)
        .where(
            CadenceStep.lead_id == lead_id,
            CadenceStep.tenant_id == tenant_id,
            CadenceStep.channel == Channel.EMAIL,
            CadenceStep.status == StepStatus.SENT,
        )
        .order_by(CadenceStep.sent_at.desc().nulls_last(), CadenceStep.scheduled_at.desc())
    )
    subject_matches = [
        step
        for step in result.scalars().all()
        if _normalize_email_subject_for_matching(step.subject_used or step.composed_subject)
        == normalized_subject
    ]
    if not subject_matches:
        return None

    if len(subject_matches) == 1:
        return RepliedStepResolution(
            step=subject_matches[0],
            match_status="matched",
            matched_via="email_subject",
        )

    cadence_ids = {step.cadence_id for step in subject_matches}
    if len(cadence_ids) > 1:
        logger.warning(
            "inbound.reply.subject_ambiguous",
            tenant_id=str(tenant_id),
            lead_id=str(lead_id),
            subject_match_count=len(subject_matches),
            sent_cadence_count=len(cadence_ids),
        )
        return RepliedStepResolution(
            step=None,
            ambiguous=True,
            sent_cadence_count=len(cadence_ids),
            match_status="ambiguous",
        )

    logger.info(
        "inbound.reply.subject_non_unique",
        tenant_id=str(tenant_id),
        lead_id=str(lead_id),
        subject_match_count=len(subject_matches),
    )
    return None


async def _load_step_by_id(
    db: AsyncSession,
    cadence_step_id: uuid.UUID,
    tenant_id: uuid.UUID,
    lead_id: uuid.UUID,
) -> CadenceStep | None:
    result = await db.execute(
        select(CadenceStep).where(
            CadenceStep.id == cadence_step_id,
            CadenceStep.tenant_id == tenant_id,
            CadenceStep.lead_id == lead_id,
        )
    )
    return result.scalar_one_or_none()


async def _resolve_fallback_step_for_reply(
    *,
    lead_id: uuid.UUID,
    tenant_id: uuid.UUID,
    channel: Channel,
    db: AsyncSession,
) -> RepliedStepResolution:
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
    )
    sent_steps = list(result.scalars().all())
    if not sent_steps:
        return RepliedStepResolution(step=None, match_status="unmatched")

    cadence_ids = {step.cadence_id for step in sent_steps}
    if len(cadence_ids) > 1:
        logger.warning(
            "inbound.reply.cadence_ambiguous",
            tenant_id=str(tenant_id),
            lead_id=str(lead_id),
            channel=channel.value,
            sent_cadence_count=len(cadence_ids),
        )
        return RepliedStepResolution(
            step=None,
            ambiguous=True,
            sent_cadence_count=len(cadence_ids),
            match_status="ambiguous",
        )

    if channel == Channel.EMAIL:
        logger.info(
            "inbound.reply.email_requires_reference",
            tenant_id=str(tenant_id),
            lead_id=str(lead_id),
            sent_cadence_count=len(cadence_ids),
        )
        return RepliedStepResolution(step=None, match_status="unmatched")

    latest_step = sent_steps[0]
    latest_step.status = StepStatus.REPLIED
    return RepliedStepResolution(
        step=latest_step,
        match_status="matched",
        matched_via="fallback_single_cadence",
    )


def _normalize_email_message_id(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    if normalized.startswith("<") and normalized.endswith(">"):
        normalized = normalized[1:-1].strip()
    return normalized


def _normalize_email_subject_for_matching(subject: str | None) -> str:
    normalized = normalize_email_subject(subject or "")
    if not normalized:
        return ""

    while True:
        stripped = _EMAIL_REPLY_SUBJECT_PREFIX_RE.sub("", normalized).strip()
        if stripped == normalized:
            break
        normalized = stripped

    return normalize_email_subject(normalized)


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
    return reply_candidate_step_channels(channel)
