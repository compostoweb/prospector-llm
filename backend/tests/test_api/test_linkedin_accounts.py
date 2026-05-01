from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes import linkedin_accounts as linkedin_accounts_route
from core.config import settings
from core.security import create_user_token
from integrations.unipile_client import HostedAuthLink
from models.account_audit_log import AccountAuditLog
from models.linkedin_account import LinkedInAccount
from models.user import User
from services.linkedin_account_service import (
    build_hosted_linkedin_auth_state,
    parse_hosted_linkedin_auth_state,
)

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


async def test_create_unipile_account_sets_owner_for_user_token(
    client: AsyncClient,
    db: AsyncSession,
    tenant_id: uuid.UUID,
    tenant_admin_user: User,
) -> None:
    token = create_user_token(
        user_id=tenant_admin_user.id,
        email=tenant_admin_user.email,
        is_superuser=False,
        name=tenant_admin_user.name,
        tenant_id=tenant_id,
    )

    response = await client.post(
        "/linkedin-accounts/unipile",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "display_name": "SDR Owner",
            "linkedin_username": "sdr-owner",
            "unipile_account_id": "li-account-owner",
            "supports_inmail": False,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["owner_user_id"] == str(tenant_admin_user.id)
    assert body["created_by_user_id"] == str(tenant_admin_user.id)
    assert body["owner_email"] == tenant_admin_user.email

    result = await db.execute(
        select(LinkedInAccount).where(LinkedInAccount.unipile_account_id == "li-account-owner")
    )
    account = result.scalar_one()
    assert account.owner_user_id == tenant_admin_user.id
    assert account.created_by_user_id == tenant_admin_user.id

    audit_result = await db.execute(
        select(AccountAuditLog).where(
            AccountAuditLog.account_id == account.id,
            AccountAuditLog.event_type == "connected",
        )
    )
    audit_log = audit_result.scalar_one()
    assert audit_log.actor_user_id == tenant_admin_user.id
    assert audit_log.account_type == "linkedin"

    logs_response = await client.get("/account-audit-logs?account_type=linkedin")
    assert logs_response.status_code == 200
    logs_body = logs_response.json()
    assert logs_body["total"] >= 1
    assert logs_body["items"][0]["account_type"] == "linkedin"


async def test_create_unipile_hosted_auth_link_uses_linkedin_provider_only(
    client: AsyncClient,
    tenant_id: uuid.UUID,
    tenant_admin_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, object] = {}

    async def fake_create_hosted_auth_link(**kwargs: object) -> HostedAuthLink:
        calls.update(kwargs)
        return HostedAuthLink(url="https://account.unipile.com/hosted-linkedin")

    monkeypatch.setattr(settings, "UNIPILE_API_KEY", "test-key")
    monkeypatch.setattr(settings, "API_PUBLIC_URL", "https://api.prospector.test")
    monkeypatch.setattr(settings, "FRONTEND_URL", "https://app.prospector.test")
    monkeypatch.setattr(
        linkedin_accounts_route.unipile_client,
        "create_hosted_auth_link",
        fake_create_hosted_auth_link,
    )
    token = create_user_token(
        user_id=tenant_admin_user.id,
        email=tenant_admin_user.email,
        is_superuser=False,
        name=tenant_admin_user.name,
        tenant_id=tenant_id,
    )

    response = await client.post(
        "/linkedin-accounts/unipile/hosted-auth",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "display_name": "LinkedIn Hosted",
            "linkedin_username": "hosted-owner",
            "supports_inmail": True,
        },
    )

    assert response.status_code == 200
    assert response.json() == {"auth_url": "https://account.unipile.com/hosted-linkedin"}
    assert calls["auth_type"] == "create"
    assert calls["providers"] == ["LINKEDIN"]
    assert calls["notify_url"] == "https://api.prospector.test/webhooks/unipile/hosted-auth"
    assert calls["success_redirect_url"] == (
        "https://app.prospector.test/configuracoes/linkedin-accounts?unipile=success"
    )

    state = parse_hosted_linkedin_auth_state(str(calls["name"]))
    assert state.tenant_id == tenant_id
    assert state.user_id == tenant_admin_user.id
    assert state.display_name == "LinkedIn Hosted"
    assert state.linkedin_username == "hosted-owner"
    assert state.supports_inmail is True


async def test_create_unipile_reconnect_link_uses_existing_account(
    client: AsyncClient,
    db: AsyncSession,
    tenant_id: uuid.UUID,
    tenant_admin_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, object] = {}

    async def fake_create_hosted_auth_link(**kwargs: object) -> HostedAuthLink:
        calls.update(kwargs)
        return HostedAuthLink(url="https://account.unipile.com/reconnect-linkedin")

    account = LinkedInAccount(
        tenant_id=tenant_id,
        display_name="LinkedIn para reconectar",
        linkedin_username="reconnect-owner",
        provider_type="unipile",
        unipile_account_id="li-reconnect-123",
        supports_inmail=True,
        is_active=True,
        provider_status="credentials",
    )
    db.add(account)
    await db.flush()

    monkeypatch.setattr(settings, "UNIPILE_API_KEY", "test-key")
    monkeypatch.setattr(settings, "API_PUBLIC_URL", "https://api.prospector.test")
    monkeypatch.setattr(settings, "FRONTEND_URL", "https://app.prospector.test")
    monkeypatch.setattr(
        linkedin_accounts_route.unipile_client,
        "create_hosted_auth_link",
        fake_create_hosted_auth_link,
    )
    token = create_user_token(
        user_id=tenant_admin_user.id,
        email=tenant_admin_user.email,
        is_superuser=False,
        name=tenant_admin_user.name,
        tenant_id=tenant_id,
    )

    response = await client.post(
        f"/linkedin-accounts/{account.id}/unipile/reconnect-link",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == {"auth_url": "https://account.unipile.com/reconnect-linkedin"}
    assert calls["auth_type"] == "reconnect"
    assert calls["providers"] == ["LINKEDIN"]
    assert calls["reconnect_account"] == "li-reconnect-123"
    assert calls["notify_url"] == "https://api.prospector.test/webhooks/unipile/hosted-auth"
    assert calls["success_redirect_url"] == (
        "https://app.prospector.test/configuracoes/linkedin-accounts?unipile=reconnected"
    )

    audit_result = await db.execute(
        select(AccountAuditLog).where(
            AccountAuditLog.account_id == account.id,
            AccountAuditLog.event_type == "reconnect_link_created",
        )
    )
    audit_log = audit_result.scalar_one()
    assert audit_log.actor_user_id == tenant_admin_user.id

    state = parse_hosted_linkedin_auth_state(str(calls["name"]))
    assert state.tenant_id == tenant_id
    assert state.user_id == tenant_admin_user.id
    assert state.display_name == "LinkedIn para reconectar"
    assert state.linkedin_username == "reconnect-owner"
    assert state.supports_inmail is True


async def test_unipile_hosted_auth_webhook_creates_owned_linkedin_account(
    client: AsyncClient,
    db: AsyncSession,
    tenant_id: uuid.UUID,
    tenant_admin_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "UNIPILE_WEBHOOK_SECRET", "secret-123")
    monkeypatch.setattr(settings, "ENV", "prod")
    state = build_hosted_linkedin_auth_state(
        tenant_id=tenant_id,
        user_id=tenant_admin_user.id,
        display_name="LinkedIn Callback",
        linkedin_username="callback-owner",
        supports_inmail=True,
    )

    response = await client.post(
        "/webhooks/unipile/hosted-auth",
        headers={"Unipile-Auth": "secret-123"},
        json={
            "status": "CREATION_SUCCESS",
            "account_id": "li-hosted-callback",
            "name": state,
        },
    )

    assert response.status_code == 200
    result = await db.execute(
        select(LinkedInAccount).where(LinkedInAccount.unipile_account_id == "li-hosted-callback")
    )
    account = result.scalar_one()
    assert account.tenant_id == tenant_id
    assert account.owner_user_id == tenant_admin_user.id
    assert account.created_by_user_id == tenant_admin_user.id
    assert account.display_name == "LinkedIn Callback"
    assert account.linkedin_username == "callback-owner"
    assert account.supports_inmail is True
    assert account.provider_status == "connected"
    assert account.connected_at is not None

    audit_result = await db.execute(
        select(AccountAuditLog).where(
            AccountAuditLog.account_id == account.id,
            AccountAuditLog.event_type == "connected",
        )
    )
    audit_log = audit_result.scalar_one()
    assert audit_log.actor_user_id == tenant_admin_user.id
    assert audit_log.external_account_id == "li-hosted-callback"


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
