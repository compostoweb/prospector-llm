"""
services/linkedin_search_service.py

Busca perfis no LinkedIn via Unipile e importa como leads.
Ponto de entrada: search_and_import()
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any, cast

import structlog
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from integrations.unipile_client import unipile_client
from models.enums import LeadSource, LeadStatus
from models.lead import Lead
from models.lead_list import lead_list_members

if TYPE_CHECKING:
    pass

logger = structlog.get_logger()


async def search_linkedin_profiles(
    *,
    account_id: str,
    keywords: str,
    titles: list[str] | None = None,
    companies: list[str] | None = None,
    location_ids: list[str] | None = None,
    industry_ids: list[str] | None = None,
    network_distance: list[int] | None = None,
    limit: int = 25,
    cursor: str | None = None,
) -> dict[str, Any]:
    """
    Busca perfis LinkedIn via Unipile.
    Retorna {"items": [...], "cursor": str | None}.
    Não persiste — apenas consulta.
    """
    client = cast(Any, unipile_client)
    return cast(
        dict[str, Any],
        await client.search_linkedin_profiles(
            account_id=account_id,
            keywords=keywords,
            titles=titles,
            companies=companies,
            location_ids=location_ids,
            industry_ids=industry_ids,
            network_distance=network_distance,
            limit=limit,
            cursor=cursor,
        ),
    )


async def import_linkedin_profiles(
    *,
    profiles: list[dict[str, object]],
    tenant_id: uuid.UUID,
    list_id: uuid.UUID | None = None,
    db: AsyncSession,
) -> dict[str, Any]:
    """
    Importa uma lista de perfis LinkedIn como leads.

    Regras de deduplicação:
    - Se o `provider_id` (public_id do LinkedIn) já existe no tenant → skip
    - Se não existe → cria novo lead com source=LINKEDIN_SEARCH

    Retorna {"created": int, "skipped": int, "lead_ids": list[str]}.
    """
    created = 0
    skipped = 0
    lead_ids: list[str] = []

    for profile in profiles:
        provider_id = cast(str, profile.get("provider_id") or "")
        if not provider_id:
            skipped += 1
            continue

        # Deduplicação por linkedin_profile_id no tenant
        existing = await db.execute(
            select(Lead).where(
                Lead.tenant_id == tenant_id,
                Lead.linkedin_profile_id == provider_id,
            )
        )
        if existing.scalar_one_or_none():
            skipped += 1
            continue

        profile_url = cast(str | None, profile.get("profile_url"))

        lead = Lead(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            name=cast(str, profile.get("name") or provider_id),
            job_title=cast(str | None, profile.get("headline")),
            company=cast(str | None, profile.get("company")),
            location=cast(str | None, profile.get("location")),
            linkedin_url=profile_url,
            linkedin_profile_id=provider_id,
            source=LeadSource.LINKEDIN_SEARCH,
            status=LeadStatus.RAW,
        )

        db.add(lead)
        await db.flush()
        if list_id:
            await db.execute(
                pg_insert(lead_list_members)
                .values(lead_list_id=list_id, lead_id=lead.id)
                .on_conflict_do_nothing()
            )
        lead_ids.append(str(lead.id))
        created += 1

    await db.commit()

    logger.info(
        "linkedin_search.import_done",
        tenant_id=str(tenant_id),
        created=created,
        skipped=skipped,
    )
    return {"created": created, "skipped": skipped, "lead_ids": lead_ids}
