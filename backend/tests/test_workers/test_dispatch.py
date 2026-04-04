"""
tests/test_workers/test_dispatch.py

Testes unitários para workers/dispatch._dispatch_async().

Estratégia:
  - Não chama o método Celery (.delay) — testa _dispatch_async diretamente
  - Banco de dados real (via fixture db do conftest) para criar fixtures
  - Integrações externas (Unipile, Speechify, ContextFetcher, LLMRegistry)
    são mockadas com AsyncMock para isolar o worker
  - Valida estados finais: step.status, Interaction criada, retorno do dict

Cobre:
  - Step não encontrado → {"status": "not_found"}
  - Step já processado (idempotência) → retorna status atual sem reprocessar
  - Canal LINKEDIN_CONNECT → envia connect, cria Interaction, step=SENT
  - Canal LINKEDIN_DM (texto) → envia DM, cria Interaction, step=SENT
  - Canal EMAIL → envia email, cria Interaction, step=SENT
  - EMAIL sem endereço cadastrado no lead → step=SKIPPED
  - Falha no envio → step=FAILED após MaxRetriesExceededError
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.cadence import Cadence
from models.cadence_step import CadenceStep
from models.email_template import EmailTemplate
from models.enums import Channel, LeadStatus, StepStatus
from models.interaction import Interaction
from models.lead import Lead

pytestmark = pytest.mark.asyncio

# ── Factories de objetos de teste ─────────────────────────────────────


def _make_lead(
    tenant_id: uuid.UUID,
    *,
    linkedin_profile_id: str = "li_profile_123",
    email_corporate: str | None = "lead@empresa.com",
    email_personal: str | None = None,
    website: str | None = None,
) -> Lead:
    return Lead(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="João Silva",
        company="Acme Corp",
        linkedin_url="https://linkedin.com/in/joao",
        linkedin_profile_id=linkedin_profile_id,
        email_corporate=email_corporate,
        email_personal=email_personal,
        website=website,
        status=LeadStatus.IN_CADENCE,
        source="manual",
    )


def _make_cadence(tenant_id: uuid.UUID) -> Cadence:
    return Cadence(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="Cadência Teste",
        llm_provider="openai",
        llm_model="gpt-4o-mini",
        llm_temperature=0.7,
        llm_max_tokens=512,
    )


def _make_step(
    tenant_id: uuid.UUID,
    lead_id: uuid.UUID,
    cadence_id: uuid.UUID,
    *,
    channel: Channel = Channel.LINKEDIN_CONNECT,
    use_voice: bool = False,
    status: StepStatus = StepStatus.PENDING,
) -> CadenceStep:
    return CadenceStep(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        lead_id=lead_id,
        cadence_id=cadence_id,
        channel=channel,
        step_number=1,
        day_offset=0,
        use_voice=use_voice,
        scheduled_at=datetime.now(tz=timezone.utc) - timedelta(minutes=5),
        status=status,
    )


# ── Mock de SendResult ─────────────────────────────────────────────────

def _send_result(message_id: str = "msg_abc123") -> MagicMock:
    r = MagicMock()
    r.message_id = message_id
    r.success = True
    return r


# ── Testes ────────────────────────────────────────────────────────────

async def test_dispatch_step_not_found(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    tenant,
) -> None:
    """Step inexistente retorna not_found sem explodir."""
    from workers.dispatch import _dispatch_async

    task_mock = MagicMock()
    result = await _dispatch_async(str(uuid.uuid4()), str(tenant_id), task_mock)
    assert result["status"] == "not_found"


async def test_dispatch_idempotency_already_sent(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    tenant,
) -> None:
    """Step com status=SENT não é reprocessado."""
    from workers.dispatch import _dispatch_async

    lead = _make_lead(tenant_id)
    cadence = _make_cadence(tenant_id)
    step = _make_step(tenant_id, lead.id, cadence.id, status=StepStatus.SENT)
    db.add_all([lead, cadence, step])
    await db.flush()

    task_mock = MagicMock()
    result = await _dispatch_async(str(step.id), str(tenant_id), task_mock)
    assert result["status"] == "sent"  # retorna o status existente


async def test_dispatch_linkedin_connect_creates_interaction(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    tenant,
) -> None:
    """Canal LINKEDIN_CONNECT: envia, cria Interaction e marca step=SENT."""
    from workers.dispatch import _dispatch_async

    lead = _make_lead(tenant_id)
    cadence = _make_cadence(tenant_id)
    step = _make_step(tenant_id, lead.id, cadence.id, channel=Channel.LINKEDIN_CONNECT)
    db.add_all([lead, cadence, step])
    await db.flush()

    with (
        patch("workers.dispatch.get_session") as mock_get_session,
        patch("workers.dispatch.context_fetcher") as mock_ctx,
        patch("workers.dispatch.AIComposer") as mock_composer_cls,
        patch("workers.dispatch.unipile_client") as mock_unipile,
        patch("workers.dispatch.LLMRegistry"),
        patch("workers.dispatch.redis_client"),
    ):
        # get_session deve entregar o db de teste
        async def _fake_session(_tid):
            yield db

        mock_get_session.side_effect = _fake_session
        mock_ctx.fetch_from_website = AsyncMock(return_value="site text")
        mock_ctx.search_company = AsyncMock(return_value="company info")

        composer_instance = MagicMock()
        composer_instance.compose = AsyncMock(return_value="Olá João, gostaria de conectar!")
        mock_composer_cls.return_value = composer_instance

        mock_unipile.send_linkedin_connect = AsyncMock(return_value=_send_result())

        task_mock = MagicMock()
        result = await _dispatch_async(str(step.id), str(tenant_id), task_mock)

    assert result["status"] == "sent"
    assert result["channel"] == "linkedin_connect"

    # Verifica step no banco
    await db.refresh(step)
    assert step.status == StepStatus.SENT
    assert step.sent_at is not None

    # Verifica Interaction criada
    intr_result = await db.execute(
        select(Interaction).where(Interaction.lead_id == lead.id)
    )
    interaction = intr_result.scalar_one_or_none()
    assert interaction is not None
    assert interaction.direction == "outbound"
    assert interaction.channel == Channel.LINKEDIN_CONNECT
    assert interaction.content_text == "Olá João, gostaria de conectar!"
    assert interaction.unipile_message_id == "msg_abc123"


async def test_dispatch_linkedin_dm_text(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    tenant,
) -> None:
    """Canal LINKEDIN_DM (texto): envia DM e marca step=SENT."""
    from workers.dispatch import _dispatch_async

    lead = _make_lead(tenant_id)
    cadence = _make_cadence(tenant_id)
    step = _make_step(tenant_id, lead.id, cadence.id, channel=Channel.LINKEDIN_DM)
    db.add_all([lead, cadence, step])
    await db.flush()

    with (
        patch("workers.dispatch.get_session") as mock_get_session,
        patch("workers.dispatch.context_fetcher") as mock_ctx,
        patch("workers.dispatch.AIComposer") as mock_composer_cls,
        patch("workers.dispatch.unipile_client") as mock_unipile,
        patch("workers.dispatch.LLMRegistry"),
        patch("workers.dispatch.redis_client"),
    ):
        async def _fake_session(_tid):
            yield db

        mock_get_session.side_effect = _fake_session
        mock_ctx.fetch_from_website = AsyncMock(return_value=None)
        mock_ctx.search_company = AsyncMock(return_value=None)

        composer_instance = MagicMock()
        composer_instance.compose = AsyncMock(return_value="Mensagem de DM aqui.")
        mock_composer_cls.return_value = composer_instance

        mock_unipile.send_linkedin_dm = AsyncMock(return_value=_send_result("dm_msg_456"))

        task_mock = MagicMock()
        result = await _dispatch_async(str(step.id), str(tenant_id), task_mock)

    assert result["status"] == "sent"
    assert result["channel"] == "linkedin_dm"

    await db.refresh(step)
    assert step.status == StepStatus.SENT


async def test_dispatch_email_sent(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    tenant,
) -> None:
    """Canal EMAIL: envia email e marca step=SENT."""
    from workers.dispatch import _dispatch_async

    lead = _make_lead(tenant_id, email_corporate="joao@acme.com")
    cadence = _make_cadence(tenant_id)
    step = _make_step(tenant_id, lead.id, cadence.id, channel=Channel.EMAIL)
    db.add_all([lead, cadence, step])
    await db.flush()

    with (
        patch("workers.dispatch.get_session") as mock_get_session,
        patch("workers.dispatch.context_fetcher") as mock_ctx,
        patch("workers.dispatch.AIComposer") as mock_composer_cls,
        patch("workers.dispatch.unipile_client") as mock_unipile,
        patch("workers.dispatch.LLMRegistry"),
        patch("workers.dispatch.redis_client"),
    ):
        async def _fake_session(_tid):
            yield db

        mock_get_session.side_effect = _fake_session
        mock_ctx.fetch_from_website = AsyncMock(return_value=None)
        mock_ctx.search_company = AsyncMock(return_value=None)

        composer_instance = MagicMock()
        composer_instance.compose = AsyncMock(return_value="Corpo do email aqui.")
        mock_composer_cls.return_value = composer_instance

        mock_unipile.send_email = AsyncMock(return_value=_send_result("email_msg_789"))

        task_mock = MagicMock()
        result = await _dispatch_async(str(step.id), str(tenant_id), task_mock)

    assert result["status"] == "sent"
    mock_unipile.send_email.assert_awaited_once()
    call_kwargs = mock_unipile.send_email.call_args.kwargs
    assert call_kwargs["to_email"] == "joao@acme.com"
    assert "body_html" in call_kwargs


async def test_dispatch_email_manual_template_body_is_used(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    tenant,
) -> None:
    """message_template configurado no step deve sobrescrever o body gerado por IA."""
    from workers.dispatch import _dispatch_async

    lead = _make_lead(tenant_id, email_corporate="joao@acme.com")
    cadence = _make_cadence(tenant_id)
    cadence.steps_template = [
        {
            "step_number": 1,
            "channel": "email",
            "day_offset": 0,
            "message_template": "Olá {first_name}, vi a operação da {company}.",
        }
    ]
    step = _make_step(tenant_id, lead.id, cadence.id, channel=Channel.EMAIL)
    db.add_all([lead, cadence, step])
    await db.flush()

    with (
        patch("workers.dispatch.get_session") as mock_get_session,
        patch("workers.dispatch.context_fetcher") as mock_ctx,
        patch("workers.dispatch.AIComposer") as mock_composer_cls,
        patch("workers.dispatch.unipile_client") as mock_unipile,
        patch("workers.dispatch.LLMRegistry"),
        patch("workers.dispatch.redis_client"),
    ):
        async def _fake_session(_tid):
            yield db

        mock_get_session.side_effect = _fake_session
        mock_ctx.fetch_from_website = AsyncMock(return_value=None)
        mock_ctx.search_company = AsyncMock(return_value=None)

        composer_instance = MagicMock()
        composer_instance.compose_email = AsyncMock(return_value=("Assunto IA", "Body IA"))
        mock_composer_cls.return_value = composer_instance

        mock_unipile.send_email = AsyncMock(return_value=_send_result("email_msg_manual"))

        task_mock = MagicMock()
        result = await _dispatch_async(str(step.id), str(tenant_id), task_mock)

    assert result["status"] == "sent"
    composer_instance.compose_email.assert_not_awaited()
    call_kwargs = mock_unipile.send_email.call_args.kwargs
    assert call_kwargs["subject"].startswith("Uma ideia para")
    assert "Olá João" in call_kwargs["body_html"]
    assert "Acme Corp" in call_kwargs["body_html"]


async def test_dispatch_email_saved_template_and_subject_variants(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    tenant,
) -> None:
    """email_template_id deve montar body/subject e subject_variants deve ter prioridade."""
    from workers.dispatch import _dispatch_async

    lead = _make_lead(tenant_id, email_corporate="joao@acme.com")
    cadence = _make_cadence(tenant_id)
    email_template = EmailTemplate(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="Primeiro contato",
        subject="Assunto base para {{company}}",
        body_html="<p>Olá {{name}}, aqui é um template para {{company}}.</p>",
    )
    cadence.steps_template = [
        {
            "step_number": 1,
            "channel": "email",
            "day_offset": 0,
            "email_template_id": str(email_template.id),
            "subject_variants": ["Variante A", "Variante B"],
        }
    ]
    step = _make_step(tenant_id, lead.id, cadence.id, channel=Channel.EMAIL)
    db.add_all([lead, cadence, email_template, step])
    await db.flush()

    with (
        patch("workers.dispatch.get_session") as mock_get_session,
        patch("workers.dispatch.context_fetcher") as mock_ctx,
        patch("workers.dispatch.AIComposer") as mock_composer_cls,
        patch("workers.dispatch.unipile_client") as mock_unipile,
        patch("workers.dispatch.LLMRegistry"),
        patch("workers.dispatch.redis_client"),
        patch("random.choice", return_value="Variante B"),
    ):
        async def _fake_session(_tid):
            yield db

        mock_get_session.side_effect = _fake_session
        mock_ctx.fetch_from_website = AsyncMock(return_value=None)
        mock_ctx.search_company = AsyncMock(return_value=None)

        composer_instance = MagicMock()
        composer_instance.compose_email = AsyncMock(return_value=("Assunto IA", "Body IA"))
        mock_composer_cls.return_value = composer_instance

        mock_unipile.send_email = AsyncMock(return_value=_send_result("email_msg_template"))

        task_mock = MagicMock()
        result = await _dispatch_async(str(step.id), str(tenant_id), task_mock)

    assert result["status"] == "sent"
    composer_instance.compose_email.assert_not_awaited()
    await db.refresh(step)
    assert step.subject_used == "Variante B"

    call_kwargs = mock_unipile.send_email.call_args.kwargs
    assert call_kwargs["subject"] == "Variante B"
    assert "João Silva" in call_kwargs["body_html"]
    assert "Acme Corp" in call_kwargs["body_html"]


async def test_dispatch_email_no_address_skips(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    tenant,
) -> None:
    """Lead sem email cadastrado → step=SKIPPED."""
    from workers.dispatch import _dispatch_async

    lead = _make_lead(tenant_id, email_corporate=None, email_personal=None)
    cadence = _make_cadence(tenant_id)
    step = _make_step(tenant_id, lead.id, cadence.id, channel=Channel.EMAIL)
    db.add_all([lead, cadence, step])
    await db.flush()

    with (
        patch("workers.dispatch.get_session") as mock_get_session,
        patch("workers.dispatch.context_fetcher") as mock_ctx,
        patch("workers.dispatch.AIComposer") as mock_composer_cls,
        patch("workers.dispatch.unipile_client"),
        patch("workers.dispatch.LLMRegistry"),
        patch("workers.dispatch.redis_client"),
    ):
        async def _fake_session(_tid):
            yield db

        mock_get_session.side_effect = _fake_session
        mock_ctx.fetch_from_website = AsyncMock(return_value=None)
        mock_ctx.search_company = AsyncMock(return_value=None)

        composer_instance = MagicMock()
        composer_instance.compose = AsyncMock(return_value="texto")
        mock_composer_cls.return_value = composer_instance

        task_mock = MagicMock()
        result = await _dispatch_async(str(step.id), str(tenant_id), task_mock)

    assert result["status"] == "skipped"
    assert result["reason"] == "no_email"

    await db.refresh(step)
    assert step.status == StepStatus.SKIPPED


async def test_dispatch_failure_marks_step_failed(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    tenant,
) -> None:
    """Quando todas as retentativas se esgotam, step=FAILED."""
    from workers.dispatch import _dispatch_async

    lead = _make_lead(tenant_id)
    cadence = _make_cadence(tenant_id)
    step = _make_step(tenant_id, lead.id, cadence.id, channel=Channel.LINKEDIN_CONNECT)
    db.add_all([lead, cadence, step])
    await db.flush()

    with (
        patch("workers.dispatch.get_session") as mock_get_session,
        patch("workers.dispatch.context_fetcher") as mock_ctx,
        patch("workers.dispatch.AIComposer") as mock_composer_cls,
        patch("workers.dispatch.unipile_client") as mock_unipile,
        patch("workers.dispatch.LLMRegistry"),
        patch("workers.dispatch.redis_client"),
    ):
        async def _fake_session(_tid):
            yield db

        mock_get_session.side_effect = _fake_session
        mock_ctx.fetch_from_website = AsyncMock(return_value=None)
        mock_ctx.search_company = AsyncMock(return_value=None)

        composer_instance = MagicMock()
        composer_instance.compose = AsyncMock(return_value="texto")
        mock_composer_cls.return_value = composer_instance

        mock_unipile.send_linkedin_connect = AsyncMock(
            side_effect=Exception("Unipile offline")
        )

        # Simula MaxRetriesExceededError após retry
        task_mock = MagicMock()
        task_mock.retry.side_effect = Exception("MaxRetriesExceededError")
        task_mock.MaxRetriesExceededError = Exception

        result = await _dispatch_async(str(step.id), str(tenant_id), task_mock)

    assert result["status"] == "failed"

    await db.refresh(step)
    assert step.status == StepStatus.FAILED
