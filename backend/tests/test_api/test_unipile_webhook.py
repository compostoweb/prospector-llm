from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from api.webhooks import unipile as unipile_webhook
from integrations.llm import LLMRegistry
from models.enums import Channel, LeadStatus
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


def test_verify_signature_rejects_when_secret_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(unipile_webhook.settings, "UNIPILE_WEBHOOK_SECRET", "")
    monkeypatch.setattr(unipile_webhook.settings, "ENV", "dev")

    assert (
        unipile_webhook._verify_signature(
            b"{}",
            signature_header="",
            custom_auth_header="",
        )
        is False
    )


@pytest.mark.asyncio
async def test_handle_message_received_processes_linkedin_payload(
    db: AsyncSession,
    tenant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lead = Lead(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Lead LinkedIn",
        linkedin_url=f"https://linkedin.com/in/{uuid.uuid4().hex[:8]}",
        linkedin_profile_id="linkedin_123",
        status=LeadStatus.IN_CADENCE,
        source="manual",
    )
    db.add(lead)
    await db.flush()

    captured: dict[str, object] = {}

    async def _fake_resolve(account_id: str, db_session, **kwargs):  # type: ignore[no-untyped-def]
        assert account_id == "acc_li_1"
        return SimpleNamespace(tenant_id=tenant.id, channel=Channel.LINKEDIN_DM)

    async def _fake_process(**kwargs):  # type: ignore[no-untyped-def]
        captured.update(kwargs)
        return SimpleNamespace(
            intent=unipile_webhook.Intent.NEUTRAL, classification={"confidence": 0.91}
        )

    monkeypatch.setattr(unipile_webhook, "resolve_unipile_account_context", _fake_resolve)
    monkeypatch.setattr(unipile_webhook, "process_inbound_reply", _fake_process)

    payload = {
        "event": "message_received",
        "account_id": "acc_li_1",
        "sender": {"attendee_provider_id": "linkedin_123"},
        "message": {
            "id": "msg_li_1",
            "account_id": "acc_li_1",
            "message": "Oi, vamos conversar?",
            "account_type": "LINKEDIN",
        },
    }

    await unipile_webhook._handle_message_received(
        payload,
        db,
        cast(LLMRegistry, SimpleNamespace()),
    )

    assert captured["lead"] == lead
    assert captured["channel"] == Channel.LINKEDIN_DM
    assert captured["external_message_id"] == "msg_li_1"
    assert captured["reply_text"] == "Oi, vamos conversar?"


@pytest.mark.asyncio
async def test_handle_message_received_marks_bounce_for_mail_received(
    db: AsyncSession,
    tenant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lead = Lead(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Lead Email",
        email_corporate="contato@empresa.com",
        status=LeadStatus.IN_CADENCE,
        source="manual",
    )
    db.add(lead)
    await db.flush()

    async def _fake_resolve(account_id: str, db_session, **kwargs):  # type: ignore[no-untyped-def]
        assert account_id == "acc_mail_1"
        return SimpleNamespace(tenant_id=tenant.id, channel=Channel.EMAIL)

    async def _should_not_process(**kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("bounce não deve cair em process_inbound_reply")

    monkeypatch.setattr(unipile_webhook, "resolve_unipile_account_context", _fake_resolve)
    monkeypatch.setattr(unipile_webhook, "process_inbound_reply", _should_not_process)

    payload = {
        "event": "mail_received",
        "account_id": "acc_mail_1",
        "sender": {"attendee_provider_id": "mailer-daemon@googlemail.com"},
        "message": {
            "id": "mail_1",
            "account_id": "acc_mail_1",
            "account_type": "GMAIL",
            "subject": "Delivery Status Notification",
            "body": "Content-Type: message/delivery-status\r\nFinal-Recipient: rfc822; contato@empresa.com",
        },
    }

    await unipile_webhook._handle_message_received(
        payload,
        db,
        cast(LLMRegistry, SimpleNamespace()),
    )

    await db.refresh(lead)
    assert lead.email_bounced_at is not None
    assert lead.email_bounce_type == "hard"


@pytest.mark.asyncio
async def test_handle_relation_created_accepts_connection_from_payload(
    db: AsyncSession,
    tenant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lead = Lead(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Lead Conexao",
        linkedin_url=f"https://linkedin.com/in/{uuid.uuid4().hex[:8]}",
        linkedin_profile_id="li_rel_1",
        linkedin_connection_status="pending",
        status=LeadStatus.IN_CADENCE,
        source="manual",
    )
    db.add(lead)
    await db.flush()

    async def _fake_resolve(account_id: str, db_session, **kwargs):  # type: ignore[no-untyped-def]
        assert account_id == "acc_relation_1"
        return SimpleNamespace(tenant_id=tenant.id, channel=Channel.LINKEDIN_DM)

    async def _fake_broadcast(*args, **kwargs):  # type: ignore[no-untyped-def]
        return None

    async def _fake_invalidate(account_id: str) -> None:
        assert account_id == "acc_relation_1"

    monkeypatch.setattr(unipile_webhook, "resolve_unipile_account_context", _fake_resolve)

    from api.routes import ws as ws_module
    from integrations.unipile_client import unipile_client

    monkeypatch.setattr(ws_module, "broadcast_event", _fake_broadcast)
    monkeypatch.setattr(unipile_client, "invalidate_inbox_cache", _fake_invalidate)

    payload = {
        "event": "new_relation",
        "relation": {
            "account_id": "acc_relation_1",
            "account_type": "LINKEDIN",
            "user_provider_id": "li_rel_1",
        },
    }

    await unipile_webhook._handle_relation_created(payload, db)

    await db.refresh(lead)
    assert lead.linkedin_connection_status == "connected"
    assert lead.linkedin_connected_at is not None
