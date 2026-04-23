from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_llm_registry, get_session_no_auth
from api.main import app
from api.webhooks import unipile as unipile_webhook
from integrations.llm import LLMRegistry
from models.cadence import Cadence
from models.cadence_step import CadenceStep
from models.email_account import EmailAccount
from models.enums import Channel, LeadStatus, ManualTaskStatus, StepStatus
from models.interaction import Interaction
from models.lead import Lead
from models.manual_task import ManualTask


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
async def test_handle_message_received_ignores_outbound_mail_from_tenant_account(
    db: AsyncSession,
    tenant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lead = Lead(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Lead Email",
        email_corporate="adriano@compostoweb.com.br",
        status=LeadStatus.IN_CADENCE,
        source="manual",
    )
    email_account = EmailAccount(
        tenant_id=tenant.id,
        display_name="Gmail principal",
        email_address="adriano@compostoweb.com.br",
        provider_type="unipile_gmail",
        unipile_account_id="acc_mail_1",
        is_active=True,
    )
    db.add(lead)
    db.add(email_account)
    await db.flush()

    async def _fake_resolve(account_id: str, db_session, **kwargs):  # type: ignore[no-untyped-def]
        assert account_id == "acc_mail_1"
        return SimpleNamespace(tenant_id=tenant.id, channel=Channel.EMAIL)

    async def _should_not_process(**kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("autoenvio não deve cair em process_inbound_reply")

    monkeypatch.setattr(unipile_webhook, "resolve_unipile_account_context", _fake_resolve)
    monkeypatch.setattr(unipile_webhook, "process_inbound_reply", _should_not_process)

    payload = {
        "event": "mail_received",
        "account_id": "acc_mail_1",
        "sender": {"attendee_provider_id": "adriano@compostoweb.com.br"},
        "message": {
            "id": "mail_self_1",
            "account_id": "acc_mail_1",
            "account_type": "GMAIL",
            "subject": "Teste",
            "body": "Oi, Adriano.",
        },
    }

    await unipile_webhook._handle_message_received(
        payload,
        db,
        cast(LLMRegistry, SimpleNamespace()),
    )


@pytest.mark.asyncio
async def test_unipile_webhook_email_reply_matches_manual_task_end_to_end(
    client: AsyncClient,
    db: AsyncSession,
    tenant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lead = Lead(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Lead Email Manual",
        email_corporate="lead.manual@empresa.com",
        status=LeadStatus.IN_CADENCE,
        source="manual",
    )
    cadence = Cadence(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Cadência Email Manual",
        is_active=True,
        mode="semi_manual",
        llm_provider="openai",
        llm_model="gpt-5.4-mini",
    )
    connect_step = CadenceStep(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        lead_id=lead.id,
        cadence_id=cadence.id,
        channel=Channel.LINKEDIN_CONNECT,
        step_number=1,
        day_offset=0,
        use_voice=False,
        status=StepStatus.SENT,
        scheduled_at=datetime.now(tz=UTC) - timedelta(days=2),
        sent_at=datetime.now(tz=UTC) - timedelta(days=2),
    )
    future_step = CadenceStep(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        lead_id=lead.id,
        cadence_id=cadence.id,
        channel=Channel.EMAIL,
        step_number=4,
        day_offset=4,
        use_voice=False,
        status=StepStatus.PENDING,
        scheduled_at=datetime.now(tz=UTC) + timedelta(days=2),
    )
    manual_task = ManualTask(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        cadence_id=cadence.id,
        lead_id=lead.id,
        cadence_step_id=connect_step.id,
        channel=Channel.EMAIL,
        step_number=3,
        status=ManualTaskStatus.SENT,
        edited_text="Email manual enviado.",
        sent_at=datetime.now(tz=UTC) - timedelta(hours=3),
    )
    outbound_interaction = Interaction(
        tenant_id=tenant.id,
        lead_id=lead.id,
        manual_task_id=manual_task.id,
        channel=Channel.EMAIL,
        direction="outbound",
        email_message_id="<manual-email@prospector.local>",
        content_text="Email manual enviado.",
        created_at=datetime.now(tz=UTC) - timedelta(hours=3),
    )
    db.add_all([lead, cadence, connect_step, future_step, manual_task])
    await db.flush()
    db.add(outbound_interaction)
    await db.commit()

    async def _override_session():
        yield db

    async def _fake_resolve(account_id: str, db_session, **kwargs):  # type: ignore[no-untyped-def]
        assert account_id == "acc_mail_manual"
        return SimpleNamespace(tenant_id=tenant.id, channel=Channel.EMAIL)

    parser_instance = MagicMock()
    parser_instance.classify = AsyncMock(
        return_value={"intent": "NEUTRAL", "confidence": 0.88, "summary": "Resposta por email"}
    )

    monkeypatch.setattr(unipile_webhook.settings, "UNIPILE_WEBHOOK_SECRET", "secret-123")
    monkeypatch.setattr(unipile_webhook.settings, "ENV", "prod")
    monkeypatch.setattr(unipile_webhook, "resolve_unipile_account_context", _fake_resolve)
    app.dependency_overrides[get_session_no_auth] = _override_session
    app.dependency_overrides[get_llm_registry] = lambda: cast(LLMRegistry, SimpleNamespace())

    try:
        with (
            patch(
                "services.inbound_message_service.resolve_tenant_llm_config",
                new=AsyncMock(return_value=SimpleNamespace(provider="openai", model="gpt-5.4-mini")),
            ),
            patch("services.inbound_message_service.ReplyParser", return_value=parser_instance),
            patch("api.routes.ws.broadcast_event", new=AsyncMock()),
        ):
            resp = await client.post(
                "/webhooks/unipile",
                content=json.dumps(
                    {
                        "event": "mail_received",
                        "account_id": "acc_mail_manual",
                        "sender": {"attendee_provider_id": "lead.manual@empresa.com"},
                        "message": {
                            "id": "mail_reply_manual_1",
                            "account_id": "acc_mail_manual",
                            "account_type": "GMAIL",
                            "subject": "Re: proposta",
                            "body": "Tenho interesse, pode seguir.",
                            "reply_to_message_id": "<manual-email@prospector.local>",
                        },
                    }
                ),
                headers={"Unipile-Auth": "secret-123"},
            )
    finally:
        app.dependency_overrides.pop(get_session_no_auth, None)
        app.dependency_overrides.pop(get_llm_registry, None)

    assert resp.status_code == 200, resp.text

    interaction_result = await db.execute(
        select(Interaction).where(Interaction.unipile_message_id == "mail_reply_manual_1")
    )
    inbound_interaction = interaction_result.scalar_one()
    await db.refresh(future_step)

    assert inbound_interaction.manual_task_id == manual_task.id
    assert inbound_interaction.reply_match_status == "matched"
    assert inbound_interaction.reply_match_source == "email_message_id"
    assert future_step.status == StepStatus.SKIPPED


@pytest.mark.asyncio
async def test_unipile_webhook_linkedin_reply_matches_manual_task_end_to_end(
    client: AsyncClient,
    db: AsyncSession,
    tenant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lead = Lead(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Lead LinkedIn Manual",
        linkedin_url=f"https://linkedin.com/in/{uuid.uuid4().hex[:8]}",
        linkedin_profile_id="linkedin_manual_123",
        status=LeadStatus.IN_CADENCE,
        source="manual",
    )
    cadence = Cadence(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Cadência LinkedIn Manual",
        is_active=True,
        mode="semi_manual",
        llm_provider="openai",
        llm_model="gpt-5.4-mini",
    )
    connect_step = CadenceStep(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        lead_id=lead.id,
        cadence_id=cadence.id,
        channel=Channel.LINKEDIN_CONNECT,
        step_number=1,
        day_offset=0,
        use_voice=False,
        status=StepStatus.SENT,
        scheduled_at=datetime.now(tz=UTC) - timedelta(days=2),
        sent_at=datetime.now(tz=UTC) - timedelta(days=2),
    )
    future_step = CadenceStep(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        lead_id=lead.id,
        cadence_id=cadence.id,
        channel=Channel.EMAIL,
        step_number=3,
        day_offset=3,
        use_voice=False,
        status=StepStatus.PENDING,
        scheduled_at=datetime.now(tz=UTC) + timedelta(days=1),
    )
    manual_task = ManualTask(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        cadence_id=cadence.id,
        lead_id=lead.id,
        cadence_step_id=connect_step.id,
        channel=Channel.LINKEDIN_DM,
        step_number=2,
        status=ManualTaskStatus.SENT,
        edited_text="DM manual enviada.",
        sent_at=datetime.now(tz=UTC) - timedelta(hours=3),
        unipile_message_id="li_manual_msg_123",
    )
    outbound_interaction = Interaction(
        tenant_id=tenant.id,
        lead_id=lead.id,
        manual_task_id=manual_task.id,
        channel=Channel.LINKEDIN_DM,
        direction="outbound",
        unipile_message_id="li_manual_msg_123",
        content_text="DM manual enviada.",
        created_at=datetime.now(tz=UTC) - timedelta(hours=3),
    )
    db.add_all([lead, cadence, connect_step, future_step, manual_task])
    await db.flush()
    db.add(outbound_interaction)
    await db.commit()

    async def _override_session():
        yield db

    async def _fake_resolve(account_id: str, db_session, **kwargs):  # type: ignore[no-untyped-def]
        assert account_id == "acc_li_manual"
        return SimpleNamespace(tenant_id=tenant.id, channel=Channel.LINKEDIN_DM)

    parser_instance = MagicMock()
    parser_instance.classify = AsyncMock(
        return_value={"intent": "NEUTRAL", "confidence": 0.84, "summary": "Resposta LinkedIn"}
    )

    monkeypatch.setattr(unipile_webhook.settings, "UNIPILE_WEBHOOK_SECRET", "secret-123")
    monkeypatch.setattr(unipile_webhook.settings, "ENV", "prod")
    monkeypatch.setattr(unipile_webhook, "resolve_unipile_account_context", _fake_resolve)
    app.dependency_overrides[get_session_no_auth] = _override_session
    app.dependency_overrides[get_llm_registry] = lambda: cast(LLMRegistry, SimpleNamespace())

    try:
        with (
            patch(
                "services.inbound_message_service.resolve_tenant_llm_config",
                new=AsyncMock(return_value=SimpleNamespace(provider="openai", model="gpt-5.4-mini")),
            ),
            patch("services.inbound_message_service.ReplyParser", return_value=parser_instance),
            patch("api.routes.ws.broadcast_event", new=AsyncMock()),
        ):
            resp = await client.post(
                "/webhooks/unipile",
                content=json.dumps(
                    {
                        "event": "message_received",
                        "account_id": "acc_li_manual",
                        "sender": {"attendee_provider_id": "linkedin_manual_123"},
                        "message": {
                            "id": "li_reply_manual_1",
                            "account_id": "acc_li_manual",
                            "account_type": "LINKEDIN",
                            "message": "Vi sua mensagem e tenho interesse.",
                            "reply_to_message_id": "li_manual_msg_123",
                        },
                    }
                ),
                headers={"Unipile-Auth": "secret-123"},
            )
    finally:
        app.dependency_overrides.pop(get_session_no_auth, None)
        app.dependency_overrides.pop(get_llm_registry, None)

    assert resp.status_code == 200, resp.text

    interaction_result = await db.execute(
        select(Interaction).where(Interaction.unipile_message_id == "li_reply_manual_1")
    )
    inbound_interaction = interaction_result.scalar_one()
    await db.refresh(future_step)

    assert inbound_interaction.manual_task_id == manual_task.id
    assert inbound_interaction.reply_match_status == "matched"
    assert inbound_interaction.reply_match_source == "unipile_message_id"
    assert future_step.status == StepStatus.SKIPPED


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
