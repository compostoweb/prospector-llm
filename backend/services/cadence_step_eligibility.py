from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from integrations.linkedin.registry import LinkedInRegistry
from models.cadence import Cadence
from models.cadence_step import CadenceStep
from models.email_account import EmailAccount
from models.enums import Channel
from models.lead import Lead
from models.linkedin_account import LinkedInAccount
from models.tenant import TenantIntegration


@dataclass(frozen=True)
class StepEligibilityResult:
    dispatchable: bool
    reason: str | None = None


async def evaluate_step_eligibility(
    db: AsyncSession,
    cadence: Cadence,
    step: CadenceStep,
    lead: Lead,
    integration: TenantIntegration | None,
) -> StepEligibilityResult:
    if step.channel == Channel.EMAIL:
        if not (lead.email_corporate or lead.email_personal):
            return StepEligibilityResult(dispatchable=False, reason="no_email")
        if cadence.email_account_id:
            result = await db.execute(
                select(EmailAccount).where(EmailAccount.id == cadence.email_account_id)
            )
            email_account = result.scalar_one_or_none()
            if email_account is None:
                return StepEligibilityResult(dispatchable=False, reason="email_account_not_found")
        elif not (
            (integration and integration.unipile_gmail_account_id)
            or settings.UNIPILE_ACCOUNT_ID_GMAIL
        ):
            return StepEligibilityResult(dispatchable=False, reason="no_email_account")
        return StepEligibilityResult(dispatchable=True)

    if step.channel in {
        Channel.LINKEDIN_CONNECT,
        Channel.LINKEDIN_DM,
        Channel.LINKEDIN_POST_REACTION,
        Channel.LINKEDIN_POST_COMMENT,
        Channel.LINKEDIN_INMAIL,
    }:
        if not lead.linkedin_profile_id:
            return StepEligibilityResult(dispatchable=False, reason="no_linkedin_profile_id")

        provider = await resolve_linkedin_delivery_provider(db, cadence, integration)
        if provider is None:
            return StepEligibilityResult(dispatchable=False, reason="no_linkedin_account")

        if step.channel in {Channel.LINKEDIN_POST_REACTION, Channel.LINKEDIN_POST_COMMENT}:
            has_post = await _has_recent_post(provider, lead.linkedin_profile_id)
            if not has_post:
                return StepEligibilityResult(dispatchable=False, reason="no_recent_post")

    return StepEligibilityResult(dispatchable=True)


@dataclass(frozen=True)
class LinkedInDeliveryProvider:
    registry: LinkedInRegistry
    account: LinkedInAccount | None = None
    fallback_account_id: str | None = None

    async def get_lead_posts(self, linkedin_profile_id: str, limit: int = 1) -> list[dict]:
        if self.account is not None:
            return await self.registry.get_lead_posts(self.account, linkedin_profile_id, limit)
        return await self.registry.get_lead_posts_global(
            linkedin_profile_id,
            limit=limit,
            account_id_override=self.fallback_account_id,
        )


async def resolve_linkedin_delivery_provider(
    db: AsyncSession,
    cadence: Cadence,
    integration: TenantIntegration | None,
) -> LinkedInDeliveryProvider | None:
    registry = LinkedInRegistry(settings=settings)
    if cadence.linkedin_account_id:
        result = await db.execute(
            select(LinkedInAccount).where(LinkedInAccount.id == cadence.linkedin_account_id)
        )
        account = result.scalar_one_or_none()
        if account is None or not account.is_active:
            return None
        return LinkedInDeliveryProvider(registry=registry, account=account)

    fallback_account_id = (
        (integration and integration.unipile_linkedin_account_id)
        or settings.UNIPILE_ACCOUNT_ID_LINKEDIN
        or ""
    )
    if not fallback_account_id:
        return None
    return LinkedInDeliveryProvider(
        registry=registry,
        fallback_account_id=fallback_account_id,
    )


async def _has_recent_post(provider: LinkedInDeliveryProvider, linkedin_profile_id: str) -> bool:
    posts = await provider.get_lead_posts(linkedin_profile_id, limit=1)
    return bool(posts)