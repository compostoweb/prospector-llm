from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from api.webhooks import unipile as unipile_webhook
from models.lead import Lead


@pytest.mark.asyncio
async def test_resolve_tenant_id_for_account_uses_account_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()

    async def _fake_resolve(account_id: str, db, **kwargs):  # type: ignore[no-untyped-def]
        assert account_id == "linkedin-account-123"
        return SimpleNamespace(tenant_id=tenant_id)

    monkeypatch.setattr(unipile_webhook, "resolve_unipile_account_context", _fake_resolve)
    db = cast(AsyncSession, SimpleNamespace())

    resolved = await unipile_webhook._resolve_tenant_id_for_unipile_account(
        "linkedin-account-123",
        db,
    )  # type: ignore[arg-type]

    assert resolved == tenant_id


@pytest.mark.asyncio
async def test_find_lead_by_sender_delegates_to_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    lead = cast(Lead, object())

    async def _fake_find(sender_id: str, tenant_id_arg: uuid.UUID, db):  # type: ignore[no-untyped-def]
        assert sender_id == "contato@empresa.com"
        assert tenant_id_arg == tenant_id
        return lead

    monkeypatch.setattr(unipile_webhook, "_svc_find_lead_by_sender", _fake_find)
    db = cast(AsyncSession, SimpleNamespace())

    found = await unipile_webhook._find_lead_by_sender(
        "contato@empresa.com",
        tenant_id,
        db,
    )  # type: ignore[arg-type]

    assert found is lead


def test_extract_text_supports_unipile_message_payload() -> None:
    assert (
        unipile_webhook._extract_text(
            {
                "message": "Hello World !",
                "event": "message_received",
            }
        )
        == "Hello World !"
    )


def test_extract_text_supports_mail_payload() -> None:
    assert (
        unipile_webhook._extract_text(
            {
                "event": "mail_received",
                "body": "Resposta por email",
            }
        )
        == "Resposta por email"
    )


def test_extract_event_type_supports_account_status_payload() -> None:
    assert (
        unipile_webhook._extract_event_type(
            {
                "AccountStatus": {
                    "account_id": "acc_123",
                    "message": "SYNC_SUCCESS",
                }
            }
        )
        == "sync_success"
    )


def test_is_outbound_message_event_detects_own_sender() -> None:
    assert unipile_webhook._is_outbound_message_event(
        {
            "event": "message_received",
            "account_info": {"user_id": "me-123"},
            "sender": {"attendee_provider_id": "me-123"},
        }
    )


@pytest.mark.asyncio
async def test_verify_signature_accepts_custom_auth_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(unipile_webhook.settings, "UNIPILE_WEBHOOK_SECRET", "secret-123")
    monkeypatch.setattr(unipile_webhook.settings, "ENV", "prod")

    assert unipile_webhook._verify_signature(
        b"{}",
        signature_header="",
        custom_auth_header="secret-123",
    )
