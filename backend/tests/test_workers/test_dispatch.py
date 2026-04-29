"""
tests/test_workers/test_dispatch.py

Testes unitários para workers/dispatch._dispatch_async().

Estratégia:
    - Não chama o método Celery (.delay) — testa _dispatch_async diretamente
    - Usa sessão assíncrona fake em memória para evitar dependência de asyncpg
    - Integrações externas (Unipile, ContextFetcher, LLMRegistry)
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
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import operators
from sqlalchemy.sql.elements import BinaryExpression, BooleanClauseList

from models.cadence import Cadence
from models.cadence_step import CadenceStep
from models.email_account import EmailAccount
from models.email_template import EmailTemplate
from models.enums import Channel, ContactPointKind, ContactQualityBucket, LeadStatus, StepStatus
from models.interaction import Interaction
from models.lead import Lead
from models.lead_contact_point import LeadContactPoint
from models.linkedin_account import LinkedInAccount
from models.tenant import Tenant, TenantIntegration

pytestmark = pytest.mark.asyncio


class _FakeScalarResult:
    def __init__(self, value: object | None) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object | None:
        return self._value

    def scalars(self) -> _FakeScalarResult:
        return self

    def all(self) -> list[object]:
        if self._value is None:
            return []
        if isinstance(self._value, list):
            return self._value
        return [self._value]


class _SingleSessionIterator:
    def __init__(self, db: Any) -> None:
        self._db = db
        self._yielded = False

    def __aiter__(self) -> _SingleSessionIterator:
        return self

    async def __anext__(self) -> Any:
        if self._yielded:
            raise StopAsyncIteration

        self._yielded = True
        return self._db


class FakeAsyncSession:
    def __init__(self) -> None:
        self._items: dict[type[Any], list[Any]] = {}

    def add(self, obj: object) -> None:
        _apply_column_defaults(obj)
        bucket = self._items.setdefault(type(obj), [])
        if obj not in bucket:
            bucket.append(obj)

    def add_all(self, objects: list[object]) -> None:
        for obj in objects:
            self.add(obj)

    async def execute(self, statement) -> _FakeScalarResult:  # type: ignore[no-untyped-def]
        entity = statement.column_descriptions[0].get("entity")
        candidates = list(self._items.get(entity, [])) if entity is not None else []

        for criterion in getattr(statement, "_where_criteria", ()):  # noqa: SLF001
            candidates = [item for item in candidates if _matches_criterion(item, criterion)]

        if entity is LeadContactPoint:
            return _FakeScalarResult(candidates)
        return _FakeScalarResult(candidates[0] if candidates else None)

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        return None

    async def refresh(self, obj: object) -> None:
        return None

    async def close(self) -> None:
        return None


def _matches_criterion(obj: object, criterion: object) -> bool:
    if isinstance(criterion, BooleanClauseList):
        return all(_matches_criterion(obj, clause) for clause in criterion.clauses)

    if not isinstance(criterion, BinaryExpression):
        return True

    field_name = getattr(criterion.left, "key", None)
    if field_name is None:
        field_name = getattr(criterion.left, "name", None)
    if not isinstance(field_name, str):
        return True

    current_value = getattr(obj, field_name, None)
    expected_value = getattr(criterion.right, "value", criterion.right)

    if criterion.operator is operators.eq:
        return cast(bool, current_value == expected_value)
    if criterion.operator is operators.is_:
        return cast(bool, current_value is expected_value or current_value == expected_value)

    return True


def _apply_column_defaults(obj: object) -> None:
    mapper = getattr(obj, "__mapper__", None)
    if mapper is None:
        return

    for column in mapper.columns:
        if getattr(obj, column.key, None) is not None:
            continue

        default = column.default
        if default is None:
            continue

        if getattr(default, "is_scalar", False):
            setattr(obj, column.key, default.arg)
            continue

        if getattr(default, "is_callable", False):
            try:
                value = default.arg()
            except TypeError:
                value = default.arg(None)
            setattr(obj, column.key, value)


@pytest.fixture
def tenant_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def db() -> FakeAsyncSession:
    return FakeAsyncSession()


@pytest.fixture
def tenant(db: FakeAsyncSession, tenant_id: uuid.UUID) -> Tenant:
    instance = Tenant(
        id=tenant_id,
        name="Tenant Teste",
        slug=f"tenant-dispatch-{tenant_id.hex[:12]}",
    )
    db.add(instance)
    db.add(TenantIntegration(tenant_id=tenant_id))
    return instance


# ── Factories de objetos de teste ─────────────────────────────────────


def _make_lead(
    tenant_id: uuid.UUID,
    *,
    linkedin_profile_id: str | None = None,
    email_corporate: str | None = "lead@empresa.com",
    email_personal: str | None = None,
    website: str | None = None,
) -> Lead:
    unique_suffix = uuid.uuid4().hex[:10]
    return Lead(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="João Silva",
        company="Acme Corp",
        linkedin_url=f"https://linkedin.com/in/{unique_suffix}",
        linkedin_profile_id=linkedin_profile_id or f"li_profile_{unique_suffix}",
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
        is_active=True,
        llm_provider="openai",
        llm_model="gpt-5.4-mini",
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
        scheduled_at=datetime.now(tz=UTC) - timedelta(minutes=5),
        status=status,
    )


# ── Mock de SendResult ─────────────────────────────────────────────────


def _send_result(message_id: str = "msg_abc123") -> MagicMock:
    r = MagicMock()
    r.message_id = message_id
    r.success = True
    return r


def _mock_worker_session(db: AsyncSession):
    async def _fake_commit() -> None:
        await db.flush()

    db.commit = AsyncMock(side_effect=_fake_commit)  # type: ignore[method-assign]

    def _fake_session(_tid: object) -> _SingleSessionIterator:
        return _SingleSessionIterator(db)

    return _fake_session


def _make_task_mock() -> MagicMock:
    task_mock = MagicMock()
    task_mock.retry.side_effect = lambda *args, **kwargs: kwargs.get("exc")
    task_mock.MaxRetriesExceededError = RuntimeError
    return task_mock


def _mock_redis() -> MagicMock:
    """Redis client mock com métodos async pré-configurados para o dispatch."""
    mock = MagicMock()
    mock.set_if_absent = AsyncMock(return_value=True)
    mock.delete = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.increment_with_ttl = AsyncMock()
    mock.release_rate_limit = AsyncMock()
    mock.release_rate_limit_key = AsyncMock()
    mock.check_and_increment = AsyncMock(return_value=True)
    return mock


# ── Testes ────────────────────────────────────────────────────────────


async def test_dispatch_step_not_found(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    tenant,
) -> None:
    """Step inexistente retorna not_found sem explodir."""
    from workers.dispatch import _dispatch_async

    with (
        patch("workers.dispatch.get_worker_session", new=_mock_worker_session(db)),
        patch("workers.dispatch.redis_client", new=_mock_redis()),
    ):
        task_mock = _make_task_mock()
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

    with (
        patch("workers.dispatch.get_worker_session", new=_mock_worker_session(db)),
        patch("workers.dispatch.redis_client", new=_mock_redis()),
    ):
        task_mock = _make_task_mock()
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
        patch("workers.dispatch.get_worker_session", new=_mock_worker_session(db)),
        patch("workers.dispatch.context_fetcher") as mock_ctx,
        patch("workers.dispatch.AIComposer") as mock_composer_cls,
        patch("workers.dispatch.unipile_client") as mock_unipile,
        patch("workers.dispatch.LLMRegistry"),
        patch("workers.dispatch.redis_client", new=_mock_redis()),
    ):
        mock_ctx.fetch_from_website = AsyncMock(return_value="site text")
        mock_ctx.search_company = AsyncMock(return_value="company info")

        composer_instance = MagicMock()
        composer_instance.compose = AsyncMock(return_value="Olá João, gostaria de conectar!")
        mock_composer_cls.return_value = composer_instance

        mock_unipile.send_linkedin_connect = AsyncMock(return_value=_send_result())

        task_mock = _make_task_mock()
        result = await _dispatch_async(str(step.id), str(tenant_id), task_mock)

    assert result["status"] == "sent"
    assert result["channel"] == "linkedin_connect"

    # Verifica step no banco
    await db.refresh(step)
    assert step.status == StepStatus.SENT
    assert step.sent_at is not None

    # Verifica Interaction criada
    intr_result = await db.execute(select(Interaction).where(Interaction.lead_id == lead.id))
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
        patch("workers.dispatch.get_worker_session", new=_mock_worker_session(db)),
        patch("workers.dispatch.context_fetcher") as mock_ctx,
        patch("workers.dispatch.AIComposer") as mock_composer_cls,
        patch("workers.dispatch.unipile_client") as mock_unipile,
        patch("workers.dispatch.LLMRegistry"),
        patch("workers.dispatch.redis_client", new=_mock_redis()),
    ):
        mock_ctx.fetch_from_website = AsyncMock(return_value=None)
        mock_ctx.search_company = AsyncMock(return_value=None)

        composer_instance = MagicMock()
        composer_instance.compose = AsyncMock(return_value="Mensagem de DM aqui.")
        mock_composer_cls.return_value = composer_instance

        mock_unipile.send_linkedin_dm = AsyncMock(return_value=_send_result("dm_msg_456"))

        task_mock = _make_task_mock()
        result = await _dispatch_async(str(step.id), str(tenant_id), task_mock)

    assert result["status"] == "sent"
    assert result["channel"] == "linkedin_dm"

    await db.refresh(step)
    assert step.status == StepStatus.SENT


async def test_dispatch_linkedin_post_comment_uses_account_registry(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    tenant,
) -> None:
    from workers.dispatch import _dispatch_async

    lead = _make_lead(tenant_id)
    cadence = _make_cadence(tenant_id)
    linkedin_account = LinkedInAccount(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        display_name="SDR Ana",
        provider_type="unipile",
        unipile_account_id="li-provider-account",
        is_active=True,
    )
    cadence.linkedin_account_id = linkedin_account.id
    step = _make_step(tenant_id, lead.id, cadence.id, channel=Channel.LINKEDIN_POST_COMMENT)
    db.add_all([lead, cadence, linkedin_account, step])
    await db.flush()

    with (
        patch("workers.dispatch.get_worker_session", new=_mock_worker_session(db)),
        patch("workers.dispatch.context_fetcher") as mock_ctx,
        patch("workers.dispatch.AIComposer") as mock_composer_cls,
        patch("workers.dispatch.unipile_client") as mock_unipile,
        patch("workers.dispatch.LLMRegistry"),
        patch("integrations.linkedin.LinkedInRegistry") as mock_li_registry_cls,
        patch(
            "services.cadence_step_eligibility.LinkedInRegistry"
        ) as mock_eligibility_registry_cls,
        patch("workers.dispatch.redis_client", new=_mock_redis()),
    ):
        mock_ctx.fetch_from_website = AsyncMock(return_value=None)
        mock_ctx.search_company = AsyncMock(return_value=None)

        composer_instance = MagicMock()
        composer_instance.compose = AsyncMock(return_value="Excelente ponto sobre a agenda de IA.")
        mock_composer_cls.return_value = composer_instance

        registry_instance = MagicMock()
        registry_instance.get_lead_posts = AsyncMock(return_value=[{"id": "post_1"}])
        registry_instance.comment_on_latest_post = AsyncMock(
            return_value=MagicMock(success=True, message_id="comment_msg_1")
        )
        mock_li_registry_cls.return_value = registry_instance
        mock_eligibility_registry_cls.return_value = registry_instance

        task_mock = _make_task_mock()
        result = await _dispatch_async(str(step.id), str(tenant_id), task_mock)

    assert result["status"] == "sent"
    assert result["channel"] == "linkedin_post_comment"
    mock_unipile.comment_on_latest_post.assert_not_called()
    registry_instance.comment_on_latest_post.assert_awaited_once()
    await db.refresh(step)
    assert step.status == StepStatus.SENT


async def test_dispatch_linkedin_inmail_uses_account_registry(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    tenant,
) -> None:
    from workers.dispatch import _dispatch_async

    lead = _make_lead(tenant_id)
    cadence = _make_cadence(tenant_id)
    linkedin_account = LinkedInAccount(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        display_name="SDR Bia",
        provider_type="unipile",
        unipile_account_id="li-provider-account-2",
        is_active=True,
        supports_inmail=True,
    )
    cadence.linkedin_account_id = linkedin_account.id
    step = _make_step(tenant_id, lead.id, cadence.id, channel=Channel.LINKEDIN_INMAIL)
    db.add_all([lead, cadence, linkedin_account, step])
    await db.flush()

    with (
        patch("workers.dispatch.get_worker_session", new=_mock_worker_session(db)),
        patch("workers.dispatch.context_fetcher") as mock_ctx,
        patch("workers.dispatch.AIComposer") as mock_composer_cls,
        patch("workers.dispatch.unipile_client") as mock_unipile,
        patch("workers.dispatch.LLMRegistry"),
        patch("integrations.linkedin.LinkedInRegistry") as mock_li_registry_cls,
        patch("workers.dispatch.redis_client", new=_mock_redis()),
    ):
        mock_ctx.fetch_from_website = AsyncMock(return_value=None)
        mock_ctx.search_company = AsyncMock(return_value=None)

        composer_instance = MagicMock()
        composer_instance.compose = AsyncMock(
            return_value='{"subject":"Convite para conversar","body":"Queria compartilhar uma ideia objetiva."}'
        )
        mock_composer_cls.return_value = composer_instance

        registry_instance = MagicMock()
        registry_instance.send_inmail = AsyncMock(
            return_value=MagicMock(success=True, message_id="inmail_msg_1")
        )
        mock_li_registry_cls.return_value = registry_instance

        task_mock = _make_task_mock()
        result = await _dispatch_async(str(step.id), str(tenant_id), task_mock)

    assert result["status"] == "sent"
    assert result["channel"] == "linkedin_inmail"
    mock_unipile.send_linkedin_inmail.assert_not_called()
    registry_instance.send_inmail.assert_awaited_once()
    await db.refresh(step)
    assert step.status == StepStatus.SENT


async def test_dispatch_linkedin_inmail_skips_when_account_has_no_capability(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    tenant,
) -> None:
    from workers.dispatch import _dispatch_async

    lead = _make_lead(tenant_id)
    cadence = _make_cadence(tenant_id)
    linkedin_account = LinkedInAccount(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        display_name="SDR Sem Premium",
        provider_type="unipile",
        unipile_account_id="li-provider-account-3",
        is_active=True,
        supports_inmail=False,
    )
    cadence.linkedin_account_id = linkedin_account.id
    step = _make_step(tenant_id, lead.id, cadence.id, channel=Channel.LINKEDIN_INMAIL)
    db.add_all([lead, cadence, linkedin_account, step])
    await db.flush()

    with (
        patch("workers.dispatch.get_worker_session", new=_mock_worker_session(db)),
        patch("workers.dispatch.context_fetcher") as mock_ctx,
        patch("workers.dispatch.AIComposer") as mock_composer_cls,
        patch("workers.dispatch.unipile_client") as mock_unipile,
        patch("workers.dispatch.LLMRegistry"),
        patch("integrations.linkedin.LinkedInRegistry") as mock_li_registry_cls,
        patch("workers.dispatch.redis_client", new=_mock_redis()),
    ):
        mock_ctx.fetch_from_website = AsyncMock(return_value=None)
        mock_ctx.search_company = AsyncMock(return_value=None)

        composer_instance = MagicMock()
        composer_instance.compose = AsyncMock(
            return_value='{"subject":"Convite para conversar","body":"Queria compartilhar uma ideia objetiva."}'
        )
        mock_composer_cls.return_value = composer_instance

        registry_instance = MagicMock()
        registry_instance.send_inmail = AsyncMock(
            return_value=MagicMock(success=True, message_id="inmail_msg_2")
        )
        mock_li_registry_cls.return_value = registry_instance

        task_mock = _make_task_mock()
        result = await _dispatch_async(str(step.id), str(tenant_id), task_mock)

    assert result["status"] == "skipped"
    assert result["reason"] == "inmail_not_supported"
    mock_unipile.send_linkedin_inmail.assert_not_called()
    registry_instance.send_inmail.assert_not_called()
    await db.refresh(step)
    assert step.status == StepStatus.SKIPPED


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
        patch("workers.dispatch.get_worker_session", new=_mock_worker_session(db)),
        patch("workers.dispatch.context_fetcher") as mock_ctx,
        patch("workers.dispatch.AIComposer") as mock_composer_cls,
        patch("workers.dispatch.unipile_client") as mock_unipile,
        patch("workers.dispatch.LLMRegistry"),
        patch("workers.dispatch.redis_client", new=_mock_redis()),
    ):
        mock_ctx.fetch_from_website = AsyncMock(return_value=None)
        mock_ctx.search_company = AsyncMock(return_value=None)

        composer_instance = MagicMock()
        composer_instance.compose_email = AsyncMock(
            return_value=("Assunto gerado", "Corpo do email aqui.")
        )
        mock_composer_cls.return_value = composer_instance

        mock_unipile.send_email = AsyncMock(return_value=_send_result("email_msg_789"))

        task_mock = _make_task_mock()
        result = await _dispatch_async(str(step.id), str(tenant_id), task_mock)

    assert result["status"] == "sent"
    composer_instance.compose_email.assert_awaited_once()
    mock_unipile.send_email.assert_awaited_once()
    call_kwargs = mock_unipile.send_email.call_args.kwargs
    assert call_kwargs["to_email"] == "joao@acme.com"
    assert call_kwargs["subject"] == "Assunto gerado"
    assert "body_html" in call_kwargs


async def test_dispatch_email_skips_when_only_available_emails_are_red(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    tenant,
) -> None:
    from workers.dispatch import _dispatch_async

    lead = _make_lead(
        tenant_id,
        email_corporate="joao@acme.com",
        email_personal="joao@gmail.com",
    )
    cadence = _make_cadence(tenant_id)
    step = _make_step(tenant_id, lead.id, cadence.id, channel=Channel.EMAIL)
    db.add_all(
        [
            lead,
            cadence,
            step,
            LeadContactPoint(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                lead_id=lead.id,
                kind=ContactPointKind.EMAIL,
                value="joao@acme.com",
                normalized_value="joao@acme.com",
                quality_bucket=ContactQualityBucket.RED,
                is_primary=True,
            ),
            LeadContactPoint(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                lead_id=lead.id,
                kind=ContactPointKind.EMAIL,
                value="joao@gmail.com",
                normalized_value="joao@gmail.com",
                quality_bucket=ContactQualityBucket.RED,
                is_primary=False,
            ),
        ]
    )
    await db.flush()

    with (
        patch("workers.dispatch.get_worker_session", new=_mock_worker_session(db)),
        patch("workers.dispatch.context_fetcher") as mock_ctx,
        patch("workers.dispatch.AIComposer") as mock_composer_cls,
        patch("workers.dispatch.unipile_client") as mock_unipile,
        patch("workers.dispatch.LLMRegistry"),
        patch("workers.dispatch.redis_client", new=_mock_redis()),
    ):
        mock_ctx.fetch_from_website = AsyncMock(return_value=None)
        mock_ctx.search_company = AsyncMock(return_value=None)

        composer_instance = MagicMock()
        composer_instance.compose_email = AsyncMock(
            return_value=("Assunto gerado", "Corpo do email aqui.")
        )
        mock_composer_cls.return_value = composer_instance

        task_mock = _make_task_mock()
        result = await _dispatch_async(str(step.id), str(tenant_id), task_mock)

    assert result["status"] == "skipped"
    assert result["reason"] == "email_quality_red"
    composer_instance.compose_email.assert_not_awaited()
    mock_unipile.send_email.assert_not_called()


async def test_dispatch_email_uses_non_red_canonical_email_when_snapshot_is_red(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    tenant,
) -> None:
    from workers.dispatch import _dispatch_async

    lead = _make_lead(tenant_id, email_corporate="joao@acme.com", email_personal=None)
    lead.email_bounced_at = datetime.now(UTC)
    lead.email_bounce_type = "hard"
    cadence = _make_cadence(tenant_id)
    step = _make_step(tenant_id, lead.id, cadence.id, channel=Channel.EMAIL)
    db.add_all(
        [
            lead,
            cadence,
            step,
            LeadContactPoint(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                lead_id=lead.id,
                kind=ContactPointKind.EMAIL,
                value="joao@acme.com",
                normalized_value="joao@acme.com",
                quality_bucket=ContactQualityBucket.RED,
                is_primary=True,
            ),
            LeadContactPoint(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                lead_id=lead.id,
                kind=ContactPointKind.EMAIL,
                value="joao.alt@acme.com",
                normalized_value="joao.alt@acme.com",
                quality_bucket=ContactQualityBucket.GREEN,
                is_primary=False,
            ),
        ]
    )
    await db.flush()

    with (
        patch("workers.dispatch.get_worker_session", new=_mock_worker_session(db)),
        patch("workers.dispatch.context_fetcher") as mock_ctx,
        patch("workers.dispatch.AIComposer") as mock_composer_cls,
        patch("workers.dispatch.unipile_client") as mock_unipile,
        patch("workers.dispatch.LLMRegistry"),
        patch("workers.dispatch.redis_client", new=_mock_redis()),
    ):
        mock_ctx.fetch_from_website = AsyncMock(return_value=None)
        mock_ctx.search_company = AsyncMock(return_value=None)

        composer_instance = MagicMock()
        composer_instance.compose_email = AsyncMock(
            return_value=("Assunto gerado", "Corpo do email aqui.")
        )
        mock_composer_cls.return_value = composer_instance
        mock_unipile.send_email = AsyncMock(return_value=_send_result("email_msg_alt"))

        task_mock = _make_task_mock()
        result = await _dispatch_async(str(step.id), str(tenant_id), task_mock)

    assert result["status"] == "sent"
    assert mock_unipile.send_email.call_args.kwargs["to_email"] == "joao.alt@acme.com"


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
        patch("workers.dispatch.get_worker_session", new=_mock_worker_session(db)),
        patch("workers.dispatch.context_fetcher") as mock_ctx,
        patch("workers.dispatch.AIComposer") as mock_composer_cls,
        patch("workers.dispatch.unipile_client") as mock_unipile,
        patch("workers.dispatch.LLMRegistry"),
        patch("workers.dispatch.redis_client", new=_mock_redis()),
    ):
        mock_ctx.fetch_from_website = AsyncMock(return_value=None)
        mock_ctx.search_company = AsyncMock(return_value=None)

        composer_instance = MagicMock()
        composer_instance.compose_email = AsyncMock(return_value=("Assunto IA", "Body IA"))
        mock_composer_cls.return_value = composer_instance

        mock_unipile.send_email = AsyncMock(return_value=_send_result("email_msg_manual"))

        task_mock = _make_task_mock()
        result = await _dispatch_async(str(step.id), str(tenant_id), task_mock)

    assert result["status"] == "sent"
    composer_instance.compose_email.assert_not_awaited()
    call_kwargs = mock_unipile.send_email.call_args.kwargs
    assert call_kwargs["subject"] == "Acme Corp: processo manual ou automatizado?"
    assert "Oi João" in call_kwargs["body_html"]
    assert "Acme Corp" in call_kwargs["body_html"]


async def test_dispatch_email_plain_text_body_is_wrapped_as_html(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    tenant,
) -> None:
    from workers.dispatch import _dispatch_async

    lead = _make_lead(tenant_id, email_corporate="joao@acme.com")
    cadence = _make_cadence(tenant_id)
    step = _make_step(tenant_id, lead.id, cadence.id, channel=Channel.EMAIL)
    db.add_all([lead, cadence, step])
    await db.flush()

    with (
        patch("workers.dispatch.get_worker_session", new=_mock_worker_session(db)),
        patch("workers.dispatch.context_fetcher") as mock_ctx,
        patch("workers.dispatch.AIComposer") as mock_composer_cls,
        patch("workers.dispatch.unipile_client") as mock_unipile,
        patch("workers.dispatch.LLMRegistry"),
        patch("workers.dispatch.redis_client", new=_mock_redis()),
    ):
        mock_ctx.fetch_from_website = AsyncMock(return_value=None)
        mock_ctx.search_company = AsyncMock(return_value=None)

        composer_instance = MagicMock()
        composer_instance.compose_email = AsyncMock(
            return_value=(
                "Assunto gerado",
                "Oi João,\n\nVi um ponto manual na operação.\nQueria sua leitura.",
            )
        )
        mock_composer_cls.return_value = composer_instance

        mock_unipile.send_email = AsyncMock(return_value=_send_result("email_msg_html"))

        task_mock = _make_task_mock()
        result = await _dispatch_async(str(step.id), str(tenant_id), task_mock)

    assert result["status"] == "sent"
    assert mock_unipile.send_email.call_args is not None
    body_html = mock_unipile.send_email.call_args.kwargs["body_html"]
    assert "<p>Oi João,</p>" in body_html
    assert "<p>Vi um ponto manual na operação.<br />Queria sua leitura.</p>" in body_html


async def test_dispatch_email_account_uses_from_name_and_signature(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    tenant,
) -> None:
    from workers.dispatch import _dispatch_async

    lead = _make_lead(tenant_id, email_corporate="joao@acme.com")
    cadence = _make_cadence(tenant_id)
    cadence.email_account_id = uuid.uuid4()
    step = _make_step(tenant_id, lead.id, cadence.id, channel=Channel.EMAIL)
    step.composed_subject = "Assunto teste"
    step.composed_text = "Corpo do email aqui."
    email_account = EmailAccount(
        id=cadence.email_account_id,
        tenant_id=tenant_id,
        display_name="Conta Principal",
        from_name="Adriano Valadao",
        email_address="adriano@compostoweb.com.br",
        provider_type="google_oauth",
        google_refresh_token="encrypted-token",
        email_signature="<p>Assinatura importada</p>",
    )
    db.add_all([lead, cadence, step, email_account])
    await db.flush()

    send_mock = AsyncMock(return_value=_send_result("email_account_msg_1"))

    with (
        patch("workers.dispatch.get_worker_session", new=_mock_worker_session(db)),
        patch("workers.dispatch.context_fetcher") as mock_ctx,
        patch("workers.dispatch.AIComposer") as mock_composer_cls,
        patch("workers.dispatch.LLMRegistry"),
        patch("workers.dispatch.redis_client", new=_mock_redis()),
        patch("integrations.email.registry.EmailRegistry.send", new=send_mock),
    ):
        mock_ctx.fetch_from_website = AsyncMock(return_value=None)
        mock_ctx.search_company = AsyncMock(return_value=None)

        composer_instance = MagicMock()
        composer_instance.compose_email = AsyncMock(return_value=("Assunto IA", "Body IA"))
        mock_composer_cls.return_value = composer_instance

        task_mock = _make_task_mock()
        result = await _dispatch_async(str(step.id), str(tenant_id), task_mock)

    assert result["status"] == "sent"
    call_kwargs = cast(Any, send_mock.await_args).kwargs
    assert call_kwargs["from_name"] == "Adriano Valadao"
    assert "Assinatura importada" in call_kwargs["body_html"]
    assert "/track/open/" in call_kwargs["body_html"]
    assert "lista de prospecção" not in call_kwargs["body_html"]
    assert "/track/unsubscribe/" not in call_kwargs["body_html"]


async def test_dispatch_unipile_email_account_prefers_google_oauth_twin_for_send(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    tenant,
) -> None:
    from workers.dispatch import _dispatch_async

    lead = _make_lead(tenant_id, email_corporate="joao@acme.com")
    cadence = _make_cadence(tenant_id)
    cadence.email_account_id = uuid.uuid4()
    step = _make_step(tenant_id, lead.id, cadence.id, channel=Channel.EMAIL)
    step.composed_subject = "Assunto teste"
    step.composed_text = "Corpo do email aqui."

    unipile_account = EmailAccount(
        id=cadence.email_account_id,
        tenant_id=tenant_id,
        display_name="Gmail via Unipile",
        from_name="Adriano Valadao",
        email_address="adriano@compostoweb.com.br",
        provider_type="unipile_gmail",
        unipile_account_id="uni_123",
        email_signature="<p>Assinatura Unipile</p>",
    )
    google_account = EmailAccount(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        display_name="Gmail OAuth",
        from_name="Adriano Valadão",
        email_address="adriano@compostoweb.com.br",
        provider_type="google_oauth",
        google_refresh_token="encrypted-token",
        email_signature="<p>Assinatura OAuth</p>",
    )
    db.add_all([lead, cadence, step, unipile_account, google_account])
    await db.flush()

    send_mock = AsyncMock(return_value=_send_result("email_account_msg_2"))

    with (
        patch("workers.dispatch.get_worker_session", new=_mock_worker_session(db)),
        patch("workers.dispatch.context_fetcher") as mock_ctx,
        patch("workers.dispatch.AIComposer") as mock_composer_cls,
        patch("workers.dispatch.LLMRegistry"),
        patch("workers.dispatch.redis_client", new=_mock_redis()),
        patch("integrations.email.registry.EmailRegistry.send", new=send_mock),
    ):
        mock_ctx.fetch_from_website = AsyncMock(return_value=None)
        mock_ctx.search_company = AsyncMock(return_value=None)

        composer_instance = MagicMock()
        composer_instance.compose_email = AsyncMock(return_value=("Assunto IA", "Body IA"))
        mock_composer_cls.return_value = composer_instance

        task_mock = _make_task_mock()
        result = await _dispatch_async(str(step.id), str(tenant_id), task_mock)

    assert result["status"] == "sent"
    assert send_mock.await_count == 1
    call_kwargs = send_mock.await_args_list[0].kwargs
    assert call_kwargs["account"].id == google_account.id
    assert call_kwargs["from_name"] == "Adriano Valadão"
    assert "Assinatura OAuth" in call_kwargs["body_html"]


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
        patch("workers.dispatch.get_worker_session", new=_mock_worker_session(db)),
        patch("workers.dispatch.context_fetcher") as mock_ctx,
        patch("workers.dispatch.AIComposer") as mock_composer_cls,
        patch("workers.dispatch.unipile_client") as mock_unipile,
        patch("workers.dispatch.LLMRegistry"),
        patch("workers.dispatch.redis_client", new=_mock_redis()),
        patch("random.choice", return_value="Variante B"),
    ):
        mock_ctx.fetch_from_website = AsyncMock(return_value=None)
        mock_ctx.search_company = AsyncMock(return_value=None)

        composer_instance = MagicMock()
        composer_instance.compose_email = AsyncMock(return_value=("Assunto IA", "Body IA"))
        mock_composer_cls.return_value = composer_instance

        mock_unipile.send_email = AsyncMock(return_value=_send_result("email_msg_template"))

        task_mock = _make_task_mock()
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
        patch("workers.dispatch.get_worker_session", new=_mock_worker_session(db)),
        patch("workers.dispatch.context_fetcher") as mock_ctx,
        patch("workers.dispatch.AIComposer") as mock_composer_cls,
        patch("workers.dispatch.unipile_client"),
        patch("workers.dispatch.LLMRegistry"),
        patch("workers.dispatch.redis_client", new=_mock_redis()),
    ):
        mock_ctx.fetch_from_website = AsyncMock(return_value=None)
        mock_ctx.search_company = AsyncMock(return_value=None)

        composer_instance = MagicMock()
        composer_instance.compose = AsyncMock(return_value="texto")
        mock_composer_cls.return_value = composer_instance

        task_mock = _make_task_mock()
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
    """Quando todas as retentativas se esgotam, step volta para PENDING (retry futuro pelo tick)."""
    from workers.dispatch import _dispatch_async

    lead = _make_lead(tenant_id)
    cadence = _make_cadence(tenant_id)
    step = _make_step(tenant_id, lead.id, cadence.id, channel=Channel.LINKEDIN_CONNECT)
    db.add_all([lead, cadence, step])
    await db.flush()

    with (
        patch("workers.dispatch.get_worker_session", new=_mock_worker_session(db)),
        patch("workers.dispatch.context_fetcher") as mock_ctx,
        patch("workers.dispatch.AIComposer") as mock_composer_cls,
        patch("workers.dispatch.unipile_client") as mock_unipile,
        patch("workers.dispatch.LLMRegistry"),
        patch("workers.dispatch.redis_client", new=_mock_redis()),
    ):
        mock_ctx.fetch_from_website = AsyncMock(return_value=None)
        mock_ctx.search_company = AsyncMock(return_value=None)

        composer_instance = MagicMock()
        composer_instance.compose = AsyncMock(return_value="texto")
        mock_composer_cls.return_value = composer_instance

        mock_unipile.send_linkedin_connect = AsyncMock(side_effect=Exception("Unipile offline"))

        # Simula MaxRetriesExceededError após retry
        task_mock = _make_task_mock()
        task_mock.retry.side_effect = RuntimeError("MaxRetriesExceededError")

        result = await _dispatch_async(str(step.id), str(tenant_id), task_mock)

    assert result["status"] == "pending"

    await db.refresh(step)
    assert step.status == StepStatus.PENDING
