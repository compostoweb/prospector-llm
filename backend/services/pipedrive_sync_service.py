from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from html import escape

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.config import settings
from integrations.pipedrive_client import PipedriveClient
from models.enums import Intent, InteractionDirection
from models.interaction import Interaction
from models.lead import Lead
from models.tenant import TenantIntegration
from services.lead_management import preferred_lead_email

logger = structlog.get_logger()

SYNCABLE_INTENTS = {Intent.INTEREST, Intent.OBJECTION}


@dataclass(frozen=True, slots=True)
class PipedriveSyncResult:
    interaction_id: uuid.UUID
    status: str
    person_id: int | None = None
    deal_id: int | None = None
    error: str | None = None


async def sync_reply_to_pipedrive(
    *,
    db: AsyncSession,
    tenant_id: uuid.UUID,
    interaction_id: uuid.UUID,
) -> PipedriveSyncResult:
    interaction = await _load_interaction(db, tenant_id, interaction_id)
    if interaction is None:
        return PipedriveSyncResult(interaction_id=interaction_id, status="not_found")

    if interaction.pipedrive_deal_id and interaction.pipedrive_sync_status == "synced":
        return PipedriveSyncResult(
            interaction_id=interaction.id,
            status="synced",
            person_id=interaction.pipedrive_person_id,
            deal_id=interaction.pipedrive_deal_id,
        )

    if interaction.direction != InteractionDirection.INBOUND:
        await _set_sync_status(db, interaction, "skipped", "interaction_not_inbound")
        return PipedriveSyncResult(
            interaction_id=interaction.id, status="skipped", error="interaction_not_inbound"
        )

    if interaction.intent not in SYNCABLE_INTENTS:
        await _set_sync_status(db, interaction, "skipped", "intent_not_syncable")
        return PipedriveSyncResult(
            interaction_id=interaction.id, status="skipped", error="intent_not_syncable"
        )

    lead = await _load_lead(db, tenant_id, interaction.lead_id)
    if lead is None:
        await _set_sync_status(db, interaction, "failed", "lead_not_found")
        return PipedriveSyncResult(
            interaction_id=interaction.id, status="failed", error="lead_not_found"
        )

    integration = await _load_integration(db, tenant_id)
    token = (
        integration.pipedrive_api_token if integration else None
    ) or settings.PIPEDRIVE_API_TOKEN
    domain = (integration.pipedrive_domain if integration else None) or settings.PIPEDRIVE_DOMAIN
    if not token or not domain:
        await _set_sync_status(db, interaction, "skipped", "pipedrive_not_configured")
        return PipedriveSyncResult(
            interaction_id=interaction.id, status="skipped", error="pipedrive_not_configured"
        )

    stage_id = _resolve_stage_id(interaction.intent, integration)
    owner_id = (
        integration.pipedrive_owner_id if integration else None
    ) or settings.PIPEDRIVE_OWNER_ID

    interaction.pipedrive_sync_status = "syncing"
    interaction.pipedrive_sync_error = None
    await db.flush()

    async with PipedriveClient(token=token, domain=domain) as client:
        org_id = None
        if lead.company:
            org_id = await client.find_or_create_organization(lead.company)

        person_id = await client.find_or_create_person(
            name=_lead_display_name(lead),
            email=preferred_lead_email(lead),
            phone=lead.phone,
            linkedin_url=lead.linkedin_url,
            org_id=org_id,
        )
        if person_id is None:
            await _set_sync_status(db, interaction, "failed", "person_create_failed")
            return PipedriveSyncResult(
                interaction_id=interaction.id, status="failed", error="person_create_failed"
            )

        deal_id = await client.create_deal(
            title=_deal_title(lead, interaction.intent),
            person_id=person_id,
            stage_id=stage_id,
            owner_id=owner_id,
            org_id=org_id,
        )
        if deal_id is None:
            interaction.pipedrive_person_id = person_id
            await _set_sync_status(db, interaction, "failed", "deal_create_failed")
            return PipedriveSyncResult(
                interaction_id=interaction.id,
                status="failed",
                person_id=person_id,
                error="deal_create_failed",
            )

        await client.add_note(deal_id, _build_reply_note(lead, interaction))

    interaction.pipedrive_sync_status = "synced"
    interaction.pipedrive_person_id = person_id
    interaction.pipedrive_deal_id = deal_id
    interaction.pipedrive_synced_at = datetime.now(UTC)
    interaction.pipedrive_sync_error = None
    await db.commit()

    logger.info(
        "pipedrive.reply_synced",
        tenant_id=str(tenant_id),
        interaction_id=str(interaction.id),
        lead_id=str(lead.id),
        intent=interaction.intent.value if interaction.intent else None,
        person_id=person_id,
        deal_id=deal_id,
    )
    return PipedriveSyncResult(
        interaction_id=interaction.id,
        status="synced",
        person_id=person_id,
        deal_id=deal_id,
    )


def enqueue_pipedrive_sync_for_reply(*, interaction_id: uuid.UUID, tenant_id: uuid.UUID) -> bool:
    try:
        from workers.pipedrive_sync import sync_reply_to_pipedrive_task

        sync_reply_to_pipedrive_task.apply_async(
            args=[str(interaction_id), str(tenant_id)],
            queue="dispatch",
        )
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "pipedrive.reply_sync_enqueue_failed",
            tenant_id=str(tenant_id),
            interaction_id=str(interaction_id),
            error=str(exc),
        )
        return False


async def _load_interaction(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    interaction_id: uuid.UUID,
) -> Interaction | None:
    result = await db.execute(
        select(Interaction).where(
            Interaction.id == interaction_id,
            Interaction.tenant_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()


async def _load_lead(db: AsyncSession, tenant_id: uuid.UUID, lead_id: uuid.UUID) -> Lead | None:
    result = await db.execute(
        select(Lead)
        .where(Lead.id == lead_id, Lead.tenant_id == tenant_id)
        .options(selectinload(Lead.emails))
    )
    return result.scalar_one_or_none()


async def _load_integration(db: AsyncSession, tenant_id: uuid.UUID) -> TenantIntegration | None:
    result = await db.execute(
        select(TenantIntegration).where(TenantIntegration.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def _set_sync_status(
    db: AsyncSession,
    interaction: Interaction,
    status: str,
    error: str | None,
) -> None:
    interaction.pipedrive_sync_status = status
    interaction.pipedrive_sync_error = error
    await db.commit()


def _resolve_stage_id(intent: Intent | None, integration: TenantIntegration | None) -> int | None:
    if intent == Intent.OBJECTION:
        return (
            integration.pipedrive_stage_objection if integration else None
        ) or settings.PIPEDRIVE_STAGE_OBJECTION
    return (
        integration.pipedrive_stage_interest if integration else None
    ) or settings.PIPEDRIVE_STAGE_INTEREST


def _lead_display_name(lead: Lead) -> str:
    return lead.name or preferred_lead_email(lead) or f"Lead {lead.id}"


def _deal_title(lead: Lead, intent: Intent | None) -> str:
    label = "Interesse" if intent == Intent.INTEREST else "Objeção"
    return f"{label} - {_lead_display_name(lead)}"


def _build_reply_note(lead: Lead, interaction: Interaction) -> str:
    fields = [
        ("Lead", _lead_display_name(lead)),
        ("Empresa", lead.company),
        ("Email", preferred_lead_email(lead)),
        ("LinkedIn", lead.linkedin_url),
        ("Canal", interaction.channel.value),
        ("Intent", interaction.intent.value if interaction.intent else None),
        ("Match", interaction.reply_match_source or interaction.reply_match_status),
        ("Resposta", interaction.content_text),
    ]
    return "<br>".join(
        f"<strong>{escape(label)}:</strong> {escape(str(value))}"
        for label, value in fields
        if value
    )
