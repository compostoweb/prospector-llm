from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.linkedin_account import LinkedInAccount

pytestmark = pytest.mark.asyncio


async def test_create_unipile_account_persists_inmail_capability(
    client: AsyncClient,
    db: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    response = await client.post(
        "/linkedin-accounts/unipile",
        json={
            "display_name": "SDR Premium",
            "linkedin_username": "sdr-premium",
            "unipile_account_id": "li-account-123",
            "supports_inmail": True,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["supports_inmail"] is True

    result = await db.execute(select(LinkedInAccount).where(LinkedInAccount.tenant_id == tenant_id))
    account = result.scalar_one()
    assert account.supports_inmail is True


async def test_update_linkedin_account_supports_inmail(
    client: AsyncClient,
    db: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    account = LinkedInAccount(
        tenant_id=tenant_id,
        display_name="SDR Operacao",
        linkedin_username="sdr-operacao",
        provider_type="unipile",
        unipile_account_id="li-account-999",
        is_active=True,
        supports_inmail=False,
    )
    db.add(account)
    await db.flush()

    response = await client.patch(
        f"/linkedin-accounts/{account.id}",
        json={"supports_inmail": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["supports_inmail"] is True
    assert account.supports_inmail is True