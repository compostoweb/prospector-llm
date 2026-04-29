from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.cadence import Cadence
from models.cadence_step import CadenceStep
from models.email_account import EmailAccount
from models.enums import Channel, Intent, LeadStatus, ManualTaskStatus, StepStatus
from models.interaction import Interaction
from models.lead import Lead
from models.lead_email import LeadEmail
from models.linkedin_account import LinkedInAccount
from models.manual_task import ManualTask
from models.tenant import TenantIntegration
from services.inbound_message_service import (
    find_lead_by_email,
    process_inbound_reply,
    resolve_unipile_account_context,
)

pytestmark = pytest.mark.asyncio


def _make_lead(tenant_id: uuid.UUID) -> Lead:
    suffix = uuid.uuid4().hex[:10]
    return Lead(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="João Silva",
        company="Acme Corp",
        linkedin_url=f"https://linkedin.com/in/{suffix}",
        linkedin_profile_id=f"li_{suffix}",
        email_corporate="joao@acme.com",
        status="in_cadence",
        source="manual",
    )


async def test_resolve_unipile_account_context_uses_provider_accounts(
    db: AsyncSession,
    tenant,
) -> None:
    linkedin_account = LinkedInAccount(
        tenant_id=tenant.id,
        display_name="LinkedIn Unipile",
        provider_type="unipile",
        unipile_account_id="li_acc_123",
    )
    email_account = EmailAccount(
        tenant_id=tenant.id,
        display_name="Gmail Unipile",
        email_address="owner@acme.com",
        provider_type="unipile_gmail",
        unipile_account_id="gm_acc_456",
    )
    db.add_all([linkedin_account, email_account])
    await db.flush()

    linkedin_context = await resolve_unipile_account_context("li_acc_123", db)
    email_context = await resolve_unipile_account_context("gm_acc_456", db)

    assert linkedin_context is not None
    assert linkedin_context.tenant_id == tenant.id
    assert linkedin_context.channel == Channel.LINKEDIN_DM

    assert email_context is not None
    assert email_context.tenant_id == tenant.id
    assert email_context.channel == Channel.EMAIL


async def test_resolve_unipile_account_context_filters_by_account_type(
    db: AsyncSession,
    tenant,
) -> None:
    result = await db.execute(
        select(TenantIntegration).where(TenantIntegration.tenant_id == tenant.id)
    )
    integration = result.scalar_one()
    integration.unipile_linkedin_account_id = "shared_acc"
    integration.unipile_gmail_account_id = "shared_acc"
    await db.flush()

    linkedin_context = await resolve_unipile_account_context(
        "shared_acc",
        db,
        account_type="LINKEDIN",
    )
    email_context = await resolve_unipile_account_context(
        "shared_acc",
        db,
        account_type="GMAIL",
    )

    assert linkedin_context is not None
    assert linkedin_context.channel == Channel.LINKEDIN_DM
    assert email_context is not None
    assert email_context.channel == Channel.EMAIL


async def test_find_lead_by_email_matches_lead_email_case_insensitive(
    db: AsyncSession,
    tenant,
) -> None:
    lead = _make_lead(tenant.id)
    db.add(lead)
    await db.flush()

    db.add(
        LeadEmail(
            tenant_id=tenant.id,
            lead_id=lead.id,
            email="Joao+Extra@Acme.com",
            source="import",
        )
    )
    await db.flush()

    found = await find_lead_by_email("joao+extra@acme.com", tenant.id, db)

    assert found is not None
    assert found.id == lead.id


async def test_process_inbound_reply_marks_connect_step_replied_for_linkedin_dm(
    db: AsyncSession,
    tenant,
) -> None:
    lead = _make_lead(tenant.id)
    cadence = Cadence(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Cadência Teste",
        is_active=True,
        llm_provider="openai",
        llm_model="gpt-5.4-mini",
        llm_temperature=0.7,
        llm_max_tokens=256,
    )
    step = CadenceStep(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        lead_id=lead.id,
        cadence_id=cadence.id,
        channel=Channel.LINKEDIN_CONNECT,
        step_number=1,
        day_offset=0,
        scheduled_at=datetime.now(tz=UTC) - timedelta(days=1),
        sent_at=datetime.now(tz=UTC) - timedelta(hours=2),
        status=StepStatus.SENT,
    )
    db.add_all([lead, cadence, step])
    await db.flush()

    parser_instance = MagicMock()
    parser_instance.classify = AsyncMock(
        return_value={
            "intent": "INTEREST",
            "confidence": 0.96,
            "summary": "Aceitou continuar a conversa",
        }
    )

    with (
        patch(
            "services.inbound_message_service.resolve_tenant_llm_config",
            new=AsyncMock(return_value=SimpleNamespace(provider="openai", model="gpt-5.4-mini")),
        ),
        patch("services.inbound_message_service.ReplyParser", return_value=parser_instance),
        patch("services.notification.send_reply_notification", new=AsyncMock()),
        patch("api.routes.ws.broadcast_event", new=AsyncMock()),
        patch(
            "services.pipedrive_sync_service.enqueue_pipedrive_sync_for_reply",
            return_value=True,
        ) as enqueue_pipedrive_sync,
    ):
        result = await process_inbound_reply(
            db=db,
            registry=MagicMock(),
            tenant_id=tenant.id,
            lead=lead,
            channel=Channel.LINKEDIN_DM,
            reply_text="Aceitei, pode me mandar mais detalhes.",
            external_message_id="msg_li_123",
        )

    await db.refresh(step)
    await db.refresh(lead)
    interaction_result = await db.execute(
        select(Interaction).where(Interaction.unipile_message_id == "msg_li_123")
    )
    interaction = interaction_result.scalar_one_or_none()

    assert result.intent == Intent.INTEREST
    assert step.status == StepStatus.REPLIED
    assert lead.status == "converted"
    assert interaction is not None
    assert interaction.channel == Channel.LINKEDIN_DM
    enqueue_pipedrive_sync.assert_called_once_with(
        interaction_id=interaction.id,
        tenant_id=tenant.id,
    )


async def test_process_inbound_reply_pauses_remaining_steps_on_neutral_reply(
    db: AsyncSession,
    tenant,
) -> None:
    lead = _make_lead(tenant.id)
    cadence = Cadence(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Cadência Teste",
        is_active=True,
        llm_provider="openai",
        llm_model="gpt-5.4-mini",
        llm_temperature=0.7,
        llm_max_tokens=256,
    )
    replied_step = CadenceStep(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        lead_id=lead.id,
        cadence_id=cadence.id,
        channel=Channel.EMAIL,
        step_number=1,
        day_offset=0,
        scheduled_at=datetime.now(tz=UTC) - timedelta(days=2),
        sent_at=datetime.now(tz=UTC) - timedelta(hours=3),
        status=StepStatus.SENT,
    )
    pending_step = CadenceStep(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        lead_id=lead.id,
        cadence_id=cadence.id,
        channel=Channel.LINKEDIN_DM,
        step_number=2,
        day_offset=1,
        scheduled_at=datetime.now(tz=UTC) + timedelta(hours=4),
        status=StepStatus.PENDING,
    )
    outbound_interaction = Interaction(
        tenant_id=tenant.id,
        lead_id=lead.id,
        cadence_step_id=replied_step.id,
        channel=Channel.EMAIL,
        direction="outbound",
        email_message_id="<threaded-neutral@prospector.local>",
    )
    db.add_all([lead, cadence, replied_step, pending_step, outbound_interaction])
    await db.flush()

    parser_instance = MagicMock()
    parser_instance.classify = AsyncMock(
        return_value={
            "intent": "NEUTRAL",
            "confidence": 0.81,
            "summary": "Respondeu sem demonstrar interesse imediato",
        }
    )

    with (
        patch(
            "services.inbound_message_service.resolve_tenant_llm_config",
            new=AsyncMock(return_value=SimpleNamespace(provider="openai", model="gpt-5.4-mini")),
        ),
        patch("services.inbound_message_service.ReplyParser", return_value=parser_instance),
        patch("api.routes.ws.broadcast_event", new=AsyncMock()),
    ):
        result = await process_inbound_reply(
            db=db,
            registry=MagicMock(),
            tenant_id=tenant.id,
            lead=lead,
            channel=Channel.EMAIL,
            reply_text="Recebi aqui, obrigado.",
            external_message_id="msg_email_123",
            reply_to_message_ids=["<threaded-neutral@prospector.local>"],
        )

    await db.refresh(replied_step)
    await db.refresh(pending_step)
    await db.refresh(lead)

    assert result.intent == Intent.NEUTRAL
    assert replied_step.status == StepStatus.REPLIED
    assert pending_step.status == StepStatus.SKIPPED
    assert lead.status == LeadStatus.IN_CADENCE


async def test_process_inbound_reply_does_not_auto_match_email_without_reference_even_single_cadence(
    db: AsyncSession,
    tenant,
) -> None:
    lead = _make_lead(tenant.id)
    cadence = Cadence(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Cadência Email",
        is_active=True,
        llm_provider="openai",
        llm_model="gpt-5.4-mini",
        llm_temperature=0.7,
        llm_max_tokens=256,
    )
    sent_step = CadenceStep(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        lead_id=lead.id,
        cadence_id=cadence.id,
        channel=Channel.EMAIL,
        step_number=1,
        day_offset=0,
        scheduled_at=datetime.now(tz=UTC) - timedelta(days=2),
        sent_at=datetime.now(tz=UTC) - timedelta(hours=3),
        status=StepStatus.SENT,
    )
    pending_step = CadenceStep(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        lead_id=lead.id,
        cadence_id=cadence.id,
        channel=Channel.EMAIL,
        step_number=2,
        day_offset=1,
        scheduled_at=datetime.now(tz=UTC) + timedelta(days=1),
        status=StepStatus.PENDING,
    )
    db.add_all([lead, cadence, sent_step, pending_step])
    await db.flush()

    parser_instance = MagicMock()
    parser_instance.classify = AsyncMock(
        return_value={"intent": "NEUTRAL", "confidence": 0.66, "summary": "Mensagem genérica"}
    )

    with (
        patch(
            "services.inbound_message_service.resolve_tenant_llm_config",
            new=AsyncMock(return_value=SimpleNamespace(provider="openai", model="gpt-5.4-mini")),
        ),
        patch("services.inbound_message_service.ReplyParser", return_value=parser_instance),
        patch("api.routes.ws.broadcast_event", new=AsyncMock()),
    ):
        await process_inbound_reply(
            db=db,
            registry=MagicMock(),
            tenant_id=tenant.id,
            lead=lead,
            channel=Channel.EMAIL,
            reply_text="Backup realizado com sucesso.",
            external_message_id="msg_email_unrelated",
        )

    await db.refresh(sent_step)
    await db.refresh(pending_step)
    interaction_result = await db.execute(
        select(Interaction).where(Interaction.unipile_message_id == "msg_email_unrelated")
    )
    interaction = interaction_result.scalar_one()

    assert sent_step.status == StepStatus.SENT
    assert pending_step.status == StepStatus.PENDING
    assert interaction.cadence_step_id is None
    assert interaction.reply_match_status == "unmatched"
    assert interaction.reply_match_source is None


async def test_process_inbound_reply_matches_reply_to_exact_outbound_message(
    db: AsyncSession,
    tenant,
) -> None:
    lead = _make_lead(tenant.id)
    cadence_a = Cadence(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Cadência A",
        is_active=True,
        llm_provider="openai",
        llm_model="gpt-5.4-mini",
    )
    cadence_b = Cadence(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Cadência B",
        is_active=True,
        llm_provider="openai",
        llm_model="gpt-5.4-mini",
    )
    older_step = CadenceStep(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        lead_id=lead.id,
        cadence_id=cadence_a.id,
        channel=Channel.EMAIL,
        step_number=1,
        day_offset=0,
        scheduled_at=datetime.now(tz=UTC) - timedelta(days=3),
        sent_at=datetime.now(tz=UTC) - timedelta(days=2),
        status=StepStatus.SENT,
    )
    latest_step = CadenceStep(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        lead_id=lead.id,
        cadence_id=cadence_b.id,
        channel=Channel.EMAIL,
        step_number=1,
        day_offset=0,
        scheduled_at=datetime.now(tz=UTC) - timedelta(days=1),
        sent_at=datetime.now(tz=UTC) - timedelta(hours=2),
        status=StepStatus.SENT,
    )
    older_interaction = Interaction(
        tenant_id=tenant.id,
        lead_id=lead.id,
        cadence_step_id=older_step.id,
        channel=Channel.EMAIL,
        direction="outbound",
        email_message_id="<older-message@prospector.local>",
    )
    latest_interaction = Interaction(
        tenant_id=tenant.id,
        lead_id=lead.id,
        cadence_step_id=latest_step.id,
        channel=Channel.EMAIL,
        direction="outbound",
        email_message_id="<latest-message@prospector.local>",
    )
    db.add_all(
        [lead, cadence_a, cadence_b, older_step, latest_step, older_interaction, latest_interaction]
    )
    await db.flush()

    parser_instance = MagicMock()
    parser_instance.classify = AsyncMock(
        return_value={"intent": "NEUTRAL", "confidence": 0.77, "summary": "Resposta direta"}
    )

    with (
        patch(
            "services.inbound_message_service.resolve_tenant_llm_config",
            new=AsyncMock(return_value=SimpleNamespace(provider="openai", model="gpt-5.4-mini")),
        ),
        patch("services.inbound_message_service.ReplyParser", return_value=parser_instance),
        patch("api.routes.ws.broadcast_event", new=AsyncMock()),
    ):
        await process_inbound_reply(
            db=db,
            registry=MagicMock(),
            tenant_id=tenant.id,
            lead=lead,
            channel=Channel.EMAIL,
            reply_text="Respondendo ao email certo.",
            external_message_id="reply_msg_1",
            reply_to_message_ids=["<older-message@prospector.local>"],
        )

    await db.refresh(older_step)
    await db.refresh(latest_step)
    interaction_result = await db.execute(
        select(Interaction).where(Interaction.unipile_message_id == "reply_msg_1")
    )
    interaction = interaction_result.scalar_one()

    assert older_step.status == StepStatus.REPLIED
    assert latest_step.status == StepStatus.SENT
    assert interaction.reply_match_status == "matched"
    assert interaction.reply_match_source == "email_message_id"


async def test_process_inbound_reply_matches_manual_task_reply_and_pauses_future_steps(
    db: AsyncSession,
    tenant,
) -> None:
    lead = _make_lead(tenant.id)
    cadence = Cadence(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Cadência Manual Task",
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
        scheduled_at=datetime.now(tz=UTC) - timedelta(days=2),
        sent_at=datetime.now(tz=UTC) - timedelta(days=2),
        status=StepStatus.SENT,
    )
    future_step = CadenceStep(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        lead_id=lead.id,
        cadence_id=cadence.id,
        channel=Channel.EMAIL,
        step_number=3,
        day_offset=3,
        scheduled_at=datetime.now(tz=UTC) + timedelta(days=1),
        status=StepStatus.PENDING,
    )
    manual_task = ManualTask(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        cadence_id=cadence.id,
        lead_id=lead.id,
        cadence_step_id=connect_step.id,
        channel=Channel.EMAIL,
        step_number=2,
        status=ManualTaskStatus.SENT,
        edited_text="Email manual enviado.",
        sent_at=datetime.now(tz=UTC) - timedelta(hours=2),
    )
    outbound_interaction = Interaction(
        tenant_id=tenant.id,
        lead_id=lead.id,
        manual_task_id=manual_task.id,
        channel=Channel.EMAIL,
        direction="outbound",
        email_message_id="<manual-task-message@prospector.local>",
        created_at=datetime.now(tz=UTC) - timedelta(hours=2),
    )
    db.add_all([lead, cadence, connect_step, future_step, manual_task])
    await db.flush()
    db.add(outbound_interaction)
    await db.flush()

    parser_instance = MagicMock()
    parser_instance.classify = AsyncMock(
        return_value={"intent": "NEUTRAL", "confidence": 0.81, "summary": "Resposta manual"}
    )

    with (
        patch(
            "services.inbound_message_service.resolve_tenant_llm_config",
            new=AsyncMock(return_value=SimpleNamespace(provider="openai", model="gpt-5.4-mini")),
        ),
        patch("services.inbound_message_service.ReplyParser", return_value=parser_instance),
        patch("api.routes.ws.broadcast_event", new=AsyncMock()),
    ):
        await process_inbound_reply(
            db=db,
            registry=MagicMock(),
            tenant_id=tenant.id,
            lead=lead,
            channel=Channel.EMAIL,
            reply_text="Respondendo a tarefa manual.",
            external_message_id="reply_manual_task_1",
            reply_to_message_ids=["<manual-task-message@prospector.local>"],
        )

    await db.refresh(future_step)
    interaction_result = await db.execute(
        select(Interaction).where(Interaction.unipile_message_id == "reply_manual_task_1")
    )
    interaction = interaction_result.scalar_one()

    assert future_step.status == StepStatus.SKIPPED
    assert interaction.cadence_step_id is None
    assert interaction.manual_task_id == manual_task.id
    assert interaction.reply_match_status == "matched"
    assert interaction.reply_match_source == "email_message_id"


async def test_process_inbound_reply_does_not_pick_cadence_when_multiple_sent_and_no_reference(
    db: AsyncSession,
    tenant,
) -> None:
    lead = _make_lead(tenant.id)
    cadence_a = Cadence(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Cadência A",
        is_active=True,
        llm_provider="openai",
        llm_model="gpt-5.4-mini",
    )
    cadence_b = Cadence(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Cadência B",
        is_active=True,
        llm_provider="openai",
        llm_model="gpt-5.4-mini",
    )
    step_a = CadenceStep(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        lead_id=lead.id,
        cadence_id=cadence_a.id,
        channel=Channel.EMAIL,
        step_number=1,
        day_offset=0,
        scheduled_at=datetime.now(tz=UTC) - timedelta(days=2),
        sent_at=datetime.now(tz=UTC) - timedelta(days=1),
        status=StepStatus.SENT,
    )
    step_b = CadenceStep(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        lead_id=lead.id,
        cadence_id=cadence_b.id,
        channel=Channel.EMAIL,
        step_number=1,
        day_offset=0,
        scheduled_at=datetime.now(tz=UTC) - timedelta(days=1),
        sent_at=datetime.now(tz=UTC) - timedelta(hours=1),
        status=StepStatus.SENT,
    )
    future_step_a = CadenceStep(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        lead_id=lead.id,
        cadence_id=cadence_a.id,
        channel=Channel.LINKEDIN_DM,
        step_number=2,
        day_offset=2,
        scheduled_at=datetime.now(tz=UTC) + timedelta(days=1),
        status=StepStatus.PENDING,
    )
    future_step_b = CadenceStep(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        lead_id=lead.id,
        cadence_id=cadence_b.id,
        channel=Channel.EMAIL,
        step_number=2,
        day_offset=2,
        scheduled_at=datetime.now(tz=UTC) + timedelta(days=1),
        status=StepStatus.DISPATCHING,
    )
    db.add_all([lead, cadence_a, cadence_b, step_a, step_b, future_step_a, future_step_b])
    await db.flush()

    parser_instance = MagicMock()
    parser_instance.classify = AsyncMock(
        return_value={"intent": "INTEREST", "confidence": 0.93, "summary": "Quero saber mais"}
    )

    with (
        patch(
            "services.inbound_message_service.resolve_tenant_llm_config",
            new=AsyncMock(return_value=SimpleNamespace(provider="openai", model="gpt-5.4-mini")),
        ),
        patch("services.inbound_message_service.ReplyParser", return_value=parser_instance),
        patch("api.routes.ws.broadcast_event", new=AsyncMock()),
        patch("services.notification.send_reply_notification", new=AsyncMock()),
    ):
        await process_inbound_reply(
            db=db,
            registry=MagicMock(),
            tenant_id=tenant.id,
            lead=lead,
            channel=Channel.EMAIL,
            reply_text="Tenho interesse.",
            external_message_id="reply_msg_2",
        )

    await db.refresh(step_a)
    await db.refresh(step_b)
    await db.refresh(future_step_a)
    await db.refresh(future_step_b)
    await db.refresh(lead)
    interaction_result = await db.execute(
        select(Interaction).where(Interaction.unipile_message_id == "reply_msg_2")
    )
    interaction = interaction_result.scalar_one()

    assert step_a.status == StepStatus.SENT
    assert step_b.status == StepStatus.SENT
    assert future_step_a.status == StepStatus.SKIPPED
    assert future_step_b.status == StepStatus.SKIPPED
    assert interaction.reply_match_status == "ambiguous"
    assert interaction.reply_match_source == "ambiguous_reply_hold"
    assert interaction.reply_match_sent_cadence_count == 2
    assert future_step_a.reply_hold_interaction_id == interaction.id
    assert future_step_b.reply_hold_interaction_id == interaction.id
    assert future_step_a.reply_hold_previous_status == "pending"
    assert future_step_b.reply_hold_previous_status == "dispatching"
    assert lead.status == LeadStatus.IN_CADENCE


async def test_process_inbound_reply_broadcasts_alert_when_reply_is_ambiguous(
    db: AsyncSession,
    tenant,
) -> None:
    lead = _make_lead(tenant.id)
    cadence_a = Cadence(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Cadência A",
        is_active=True,
        llm_provider="openai",
        llm_model="gpt-5.4-mini",
    )
    cadence_b = Cadence(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Cadência B",
        is_active=True,
        llm_provider="openai",
        llm_model="gpt-5.4-mini",
    )
    step_a = CadenceStep(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        lead_id=lead.id,
        cadence_id=cadence_a.id,
        channel=Channel.EMAIL,
        step_number=1,
        day_offset=0,
        scheduled_at=datetime.now(tz=UTC) - timedelta(days=2),
        sent_at=datetime.now(tz=UTC) - timedelta(days=1),
        status=StepStatus.SENT,
    )
    step_b = CadenceStep(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        lead_id=lead.id,
        cadence_id=cadence_b.id,
        channel=Channel.EMAIL,
        step_number=1,
        day_offset=0,
        scheduled_at=datetime.now(tz=UTC) - timedelta(days=1),
        sent_at=datetime.now(tz=UTC) - timedelta(hours=1),
        status=StepStatus.SENT,
    )
    db.add_all([lead, cadence_a, cadence_b, step_a, step_b])
    await db.flush()

    parser_instance = MagicMock()
    parser_instance.classify = AsyncMock(
        return_value={"intent": "NEUTRAL", "confidence": 0.71, "summary": "Resposta curta"}
    )
    broadcast_event = AsyncMock()

    with (
        patch(
            "services.inbound_message_service.resolve_tenant_llm_config",
            new=AsyncMock(return_value=SimpleNamespace(provider="openai", model="gpt-5.4-mini")),
        ),
        patch("services.inbound_message_service.ReplyParser", return_value=parser_instance),
        patch("api.routes.ws.broadcast_event", new=broadcast_event),
    ):
        await process_inbound_reply(
            db=db,
            registry=MagicMock(),
            tenant_id=tenant.id,
            lead=lead,
            channel=Channel.EMAIL,
            reply_text="Pode me explicar melhor?",
            external_message_id="reply_msg_3",
        )

    ambiguous_calls = [
        call
        for call in broadcast_event.await_args_list
        if call.args[1].get("type") == "inbound.reply_ambiguous"
    ]
    interaction_result = await db.execute(
        select(Interaction).where(Interaction.unipile_message_id == "reply_msg_3")
    )
    interaction = interaction_result.scalar_one()

    assert len(ambiguous_calls) == 1
    assert ambiguous_calls[0].args[0] == str(tenant.id)
    assert ambiguous_calls[0].args[1]["lead_id"] == str(lead.id)
    assert ambiguous_calls[0].args[1]["sent_cadence_count"] == 2
    assert interaction.reply_match_status == "ambiguous"
    assert interaction.reply_match_sent_cadence_count == 2
    assert lead.status == LeadStatus.IN_CADENCE


async def test_process_inbound_reply_matches_email_by_subject_when_unique(
    db: AsyncSession,
    tenant,
) -> None:
    lead = _make_lead(tenant.id)
    cadence_a = Cadence(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Cadência A",
        is_active=True,
        llm_provider="openai",
        llm_model="gpt-5.4-mini",
    )
    cadence_b = Cadence(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Cadência B",
        is_active=True,
        llm_provider="openai",
        llm_model="gpt-5.4-mini",
    )
    target_step = CadenceStep(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        lead_id=lead.id,
        cadence_id=cadence_a.id,
        channel=Channel.EMAIL,
        step_number=1,
        day_offset=0,
        scheduled_at=datetime.now(tz=UTC) - timedelta(days=2),
        sent_at=datetime.now(tz=UTC) - timedelta(hours=5),
        status=StepStatus.SENT,
        subject_used="Acme: processo manual ou automatizado?",
    )
    other_step = CadenceStep(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        lead_id=lead.id,
        cadence_id=cadence_b.id,
        channel=Channel.EMAIL,
        step_number=1,
        day_offset=0,
        scheduled_at=datetime.now(tz=UTC) - timedelta(days=1),
        sent_at=datetime.now(tz=UTC) - timedelta(hours=2),
        status=StepStatus.SENT,
        subject_used="Novo angulo sobre esse processo",
    )
    db.add_all([lead, cadence_a, cadence_b, target_step, other_step])
    await db.flush()

    parser_instance = MagicMock()
    parser_instance.classify = AsyncMock(
        return_value={"intent": "NEUTRAL", "confidence": 0.74, "summary": "Resposta direta"}
    )

    with (
        patch(
            "services.inbound_message_service.resolve_tenant_llm_config",
            new=AsyncMock(return_value=SimpleNamespace(provider="openai", model="gpt-5.4-mini")),
        ),
        patch("services.inbound_message_service.ReplyParser", return_value=parser_instance),
        patch("api.routes.ws.broadcast_event", new=AsyncMock()),
    ):
        await process_inbound_reply(
            db=db,
            registry=MagicMock(),
            tenant_id=tenant.id,
            lead=lead,
            channel=Channel.EMAIL,
            reply_text="Respondendo pelo assunto.",
            external_message_id="reply_msg_subject_1",
            inbound_subject="Re: Acme: processo manual ou automatizado?",
        )

    await db.refresh(target_step)
    await db.refresh(other_step)
    interaction_result = await db.execute(
        select(Interaction).where(Interaction.unipile_message_id == "reply_msg_subject_1")
    )
    interaction = interaction_result.scalar_one()

    assert target_step.status == StepStatus.REPLIED
    assert other_step.status == StepStatus.SENT
    assert interaction.cadence_step_id == target_step.id
    assert interaction.reply_match_status == "matched"
    assert interaction.reply_match_source == "email_subject"


async def test_process_inbound_reply_matches_email_by_similar_subject_when_unique(
    db: AsyncSession,
    tenant,
) -> None:
    lead = _make_lead(tenant.id)
    cadence = Cadence(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Cadência Similar Subject",
        is_active=True,
        llm_provider="openai",
        llm_model="gpt-5.4-mini",
    )
    target_step = CadenceStep(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        lead_id=lead.id,
        cadence_id=cadence.id,
        channel=Channel.EMAIL,
        step_number=1,
        day_offset=0,
        scheduled_at=datetime.now(tz=UTC) - timedelta(days=2),
        sent_at=datetime.now(tz=UTC) - timedelta(hours=5),
        status=StepStatus.SENT,
        subject_used="Acme: processo manual ou automatizado?",
    )
    future_step = CadenceStep(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        lead_id=lead.id,
        cadence_id=cadence.id,
        channel=Channel.EMAIL,
        step_number=2,
        day_offset=1,
        scheduled_at=datetime.now(tz=UTC) + timedelta(days=1),
        status=StepStatus.PENDING,
    )
    db.add_all([lead, cadence, target_step, future_step])
    await db.flush()

    parser_instance = MagicMock()
    parser_instance.classify = AsyncMock(
        return_value={"intent": "NEUTRAL", "confidence": 0.74, "summary": "Resposta direta"}
    )

    with (
        patch(
            "services.inbound_message_service.resolve_tenant_llm_config",
            new=AsyncMock(return_value=SimpleNamespace(provider="openai", model="gpt-5.4-mini")),
        ),
        patch("services.inbound_message_service.ReplyParser", return_value=parser_instance),
        patch("api.routes.ws.broadcast_event", new=AsyncMock()),
    ):
        await process_inbound_reply(
            db=db,
            registry=MagicMock(),
            tenant_id=tenant.id,
            lead=lead,
            channel=Channel.EMAIL,
            reply_text="Respondendo pelo assunto quase igual.",
            external_message_id="reply_msg_subject_similar_1",
            inbound_subject="Re: Acme: processo manual ou automatizado?!",
        )

    await db.refresh(target_step)
    await db.refresh(future_step)
    interaction_result = await db.execute(
        select(Interaction).where(Interaction.unipile_message_id == "reply_msg_subject_similar_1")
    )
    interaction = interaction_result.scalar_one()

    assert target_step.status == StepStatus.REPLIED
    assert future_step.status == StepStatus.SKIPPED
    assert interaction.cadence_step_id == target_step.id
    assert interaction.reply_match_status == "matched"
    assert interaction.reply_match_source == "email_subject_similar"


async def test_process_inbound_reply_does_not_match_email_by_subject_when_non_unique_same_cadence(
    db: AsyncSession,
    tenant,
) -> None:
    lead = _make_lead(tenant.id)
    cadence = Cadence(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Cadência Email",
        is_active=True,
        llm_provider="openai",
        llm_model="gpt-5.4-mini",
    )
    first_step = CadenceStep(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        lead_id=lead.id,
        cadence_id=cadence.id,
        channel=Channel.EMAIL,
        step_number=1,
        day_offset=0,
        scheduled_at=datetime.now(tz=UTC) - timedelta(days=3),
        sent_at=datetime.now(tz=UTC) - timedelta(days=2),
        status=StepStatus.SENT,
        subject_used="Acme: processo manual ou automatizado?",
    )
    second_step = CadenceStep(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        lead_id=lead.id,
        cadence_id=cadence.id,
        channel=Channel.EMAIL,
        step_number=2,
        day_offset=1,
        scheduled_at=datetime.now(tz=UTC) - timedelta(days=2),
        sent_at=datetime.now(tz=UTC) - timedelta(hours=6),
        status=StepStatus.SENT,
        subject_used="Acme: processo manual ou automatizado?",
    )
    db.add_all([lead, cadence, first_step, second_step])
    await db.flush()

    parser_instance = MagicMock()
    parser_instance.classify = AsyncMock(
        return_value={"intent": "NEUTRAL", "confidence": 0.68, "summary": "Resposta curta"}
    )

    with (
        patch(
            "services.inbound_message_service.resolve_tenant_llm_config",
            new=AsyncMock(return_value=SimpleNamespace(provider="openai", model="gpt-5.4-mini")),
        ),
        patch("services.inbound_message_service.ReplyParser", return_value=parser_instance),
        patch("api.routes.ws.broadcast_event", new=AsyncMock()),
    ):
        await process_inbound_reply(
            db=db,
            registry=MagicMock(),
            tenant_id=tenant.id,
            lead=lead,
            channel=Channel.EMAIL,
            reply_text="Respondendo sem referência forte.",
            external_message_id="reply_msg_subject_2",
            inbound_subject="Re: Acme: processo manual ou automatizado?",
        )

    await db.refresh(first_step)
    await db.refresh(second_step)
    interaction_result = await db.execute(
        select(Interaction).where(Interaction.unipile_message_id == "reply_msg_subject_2")
    )
    interaction = interaction_result.scalar_one()

    assert first_step.status == StepStatus.SENT
    assert second_step.status == StepStatus.SENT
    assert interaction.cadence_step_id is None
    assert interaction.reply_match_status == "unmatched"
    assert interaction.reply_match_source is None
