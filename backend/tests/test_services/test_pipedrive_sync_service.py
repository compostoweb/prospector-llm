from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from models.enums import Channel, Intent, InteractionDirection
from models.interaction import Interaction
from models.lead import Lead
from models.tenant import TenantIntegration
from services.pipedrive_sync_service import sync_reply_to_pipedrive

pytestmark = pytest.mark.asyncio


class FakePipedriveClient:
    instances: list[FakePipedriveClient] = []

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.args = args
        self.kwargs = kwargs
        self.notes: list[tuple[int, str]] = []
        FakePipedriveClient.instances.append(self)

    async def __aenter__(self) -> FakePipedriveClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def find_or_create_organization(self, name: str) -> int:
        assert name == "Acme Corp"
        return 301

    async def find_or_create_person(
        self,
        *,
        name: str,
        email: str | None,
        phone: str | None,
        linkedin_url: str | None,
        org_id: int | None,
    ) -> int:
        assert name == "João Silva"
        assert email == "joao@acme.com"
        assert phone == "+5511999999999"
        assert linkedin_url == "https://linkedin.com/in/joao"
        assert org_id == 301
        return 401

    async def create_deal(
        self,
        *,
        title: str,
        person_id: int | None,
        stage_id: int | None,
        owner_id: int | None,
        org_id: int | None,
    ) -> int:
        assert title == "Interesse - João Silva"
        assert person_id == 401
        assert stage_id == 10
        assert owner_id == 77
        assert org_id == 301
        return 501

    async def add_note(self, deal_id: int, content: str) -> bool:
        self.notes.append((deal_id, content))
        return True


def _make_lead(tenant_id: uuid.UUID) -> Lead:
    return Lead(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="João Silva",
        company="Acme Corp",
        linkedin_url="https://linkedin.com/in/joao",
        email_corporate="joao@acme.com",
        phone="+5511999999999",
        status="in_cadence",
        source="manual",
    )


async def test_sync_reply_to_pipedrive_creates_person_deal_and_note(
    db: AsyncSession,
    tenant,
) -> None:
    integration_result = await db.execute(
        select(TenantIntegration).where(TenantIntegration.tenant_id == tenant.id)
    )
    integration = integration_result.scalar_one()
    integration.pipedrive_api_token = "tenant-token"
    integration.pipedrive_domain = "tenant-domain"
    integration.pipedrive_stage_interest = 10
    integration.pipedrive_owner_id = 77

    lead = _make_lead(tenant.id)
    interaction = Interaction(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        lead_id=lead.id,
        channel=Channel.EMAIL,
        direction=InteractionDirection.INBOUND,
        content_text="Tenho interesse, me envie mais detalhes.",
        intent=Intent.INTEREST,
        reply_match_status="matched",
        reply_match_source="email_message_id",
        created_at=datetime.now(UTC),
    )
    db.add_all([lead, interaction])
    await db.flush()

    FakePipedriveClient.instances = []
    with patch("services.pipedrive_sync_service.PipedriveClient", FakePipedriveClient):
        result = await sync_reply_to_pipedrive(
            db=db,
            tenant_id=tenant.id,
            interaction_id=interaction.id,
        )

    await db.refresh(interaction)
    fake_client = FakePipedriveClient.instances[0]

    assert result.status == "synced"
    assert result.person_id == 401
    assert result.deal_id == 501
    assert fake_client.kwargs == {"token": "tenant-token", "domain": "tenant-domain"}
    assert fake_client.notes[0][0] == 501
    assert "Tenho interesse" in fake_client.notes[0][1]
    assert interaction.pipedrive_sync_status == "synced"
    assert interaction.pipedrive_person_id == 401
    assert interaction.pipedrive_deal_id == 501
    assert interaction.pipedrive_synced_at is not None
    assert interaction.pipedrive_sync_error is None


async def test_sync_reply_to_pipedrive_is_idempotent_when_already_synced(
    db: AsyncSession,
    tenant,
) -> None:
    lead = _make_lead(tenant.id)
    interaction = Interaction(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        lead_id=lead.id,
        channel=Channel.EMAIL,
        direction=InteractionDirection.INBOUND,
        content_text="Tenho interesse.",
        intent=Intent.INTEREST,
        pipedrive_sync_status="synced",
        pipedrive_person_id=123,
        pipedrive_deal_id=456,
    )
    db.add_all([lead, interaction])
    await db.flush()

    with patch("services.pipedrive_sync_service.PipedriveClient") as pipedrive_client:
        result = await sync_reply_to_pipedrive(
            db=db,
            tenant_id=tenant.id,
            interaction_id=interaction.id,
        )

    pipedrive_client.assert_not_called()
    assert result.status == "synced"
    assert result.person_id == 123
    assert result.deal_id == 456


async def test_sync_reply_to_pipedrive_skips_when_not_configured(
    db: AsyncSession,
    tenant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "PIPEDRIVE_API_TOKEN", None)
    monkeypatch.setattr(settings, "PIPEDRIVE_DOMAIN", None)

    lead = _make_lead(tenant.id)
    interaction = Interaction(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        lead_id=lead.id,
        channel=Channel.EMAIL,
        direction=InteractionDirection.INBOUND,
        content_text="Tenho interesse.",
        intent=Intent.INTEREST,
    )
    db.add_all([lead, interaction])
    await db.flush()

    result = await sync_reply_to_pipedrive(
        db=db,
        tenant_id=tenant.id,
        interaction_id=interaction.id,
    )

    await db.refresh(interaction)

    assert result.status == "skipped"
    assert result.error == "pipedrive_not_configured"
    assert interaction.pipedrive_sync_status == "skipped"
    assert interaction.pipedrive_sync_error == "pipedrive_not_configured"
