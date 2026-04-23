from __future__ import annotations

from sqlalchemy import and_, or_

from models.enums import Channel, InteractionDirection
from models.interaction import Interaction

LOW_CONFIDENCE_EMAIL_REPLY_SOURCE = "fallback_single_cadence"
MANUAL_REVIEW_REPLY_SOURCE = "manual_review"


def reply_candidate_step_channels(channel: Channel) -> tuple[Channel, ...]:
    if channel == Channel.LINKEDIN_DM:
        return (Channel.LINKEDIN_DM, Channel.LINKEDIN_CONNECT)
    return (channel,)


def reliable_reply_interaction_condition():
    return and_(
        Interaction.direction == InteractionDirection.INBOUND,
        or_(
            Interaction.cadence_step_id.is_not(None),
            Interaction.manual_task_id.is_not(None),
        ),
        or_(
            Interaction.channel != Channel.EMAIL,
            Interaction.reply_match_source.is_(None),
            Interaction.reply_match_source != LOW_CONFIDENCE_EMAIL_REPLY_SOURCE,
        ),
    )


def is_low_confidence_email_reply_interaction(interaction: Interaction) -> bool:
    return (
        interaction.direction == InteractionDirection.INBOUND
        and interaction.channel == Channel.EMAIL
        and interaction.reply_match_source == LOW_CONFIDENCE_EMAIL_REPLY_SOURCE
    )


def is_reliable_reply_interaction(interaction: Interaction) -> bool:
    return (
        interaction.direction == InteractionDirection.INBOUND
        and (
            interaction.cadence_step_id is not None
            or interaction.manual_task_id is not None
        )
        and not is_low_confidence_email_reply_interaction(interaction)
    )


def pending_reply_audit_interaction_condition():
    return and_(
        Interaction.direction == InteractionDirection.INBOUND,
        Interaction.reply_reviewed_at.is_(None),
        or_(
            Interaction.reply_match_status.in_(["ambiguous", "unmatched"]),
            and_(
                Interaction.channel == Channel.EMAIL,
                Interaction.reply_match_source == LOW_CONFIDENCE_EMAIL_REPLY_SOURCE,
            ),
        ),
    )


def is_pending_reply_audit_interaction(interaction: Interaction) -> bool:
    return (
        interaction.direction == InteractionDirection.INBOUND
        and interaction.reply_reviewed_at is None
        and (
            interaction.reply_match_status in {"ambiguous", "unmatched"}
            or is_low_confidence_email_reply_interaction(interaction)
        )
    )
