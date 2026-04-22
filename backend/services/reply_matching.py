from __future__ import annotations

from sqlalchemy import and_, or_

from models.enums import Channel, InteractionDirection
from models.interaction import Interaction

LOW_CONFIDENCE_EMAIL_REPLY_SOURCE = "fallback_single_cadence"


def reliable_reply_interaction_condition():
    return and_(
        Interaction.direction == InteractionDirection.INBOUND,
        Interaction.cadence_step_id.is_not(None),
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
        and interaction.cadence_step_id is not None
        and not is_low_confidence_email_reply_interaction(interaction)
    )
