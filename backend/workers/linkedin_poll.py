"""
workers/linkedin_poll.py

Task Celery para polling de inbox LinkedIn nas contas nativas (provider_type="native").

Contas Unipile usam webhook — este worker só entra em ação para provider nativo.

Task:
  linkedin_poll_tick()
    — Busca todas as contas nativas ativas (provider_type="native")
    — Para cada conta: lista conversas novas desde o último cursor
    — Para cada conversa nova: lê mensagens e dispara handle_linkedin_message
    — Atualiza cursor em Redis (linkedin:cursor:{account_id})
    — Fila: "cadence"

Cursor: timestamp da última mensagem processada (str ISO8601)
Redis key: linkedin:native:cursor:{account_id}  TTL: 7 dias
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import structlog

from workers.celery_app import celery_app

logger = structlog.get_logger()

_CURSOR_KEY = "linkedin:native:cursor:{account_id}"
_CURSOR_TTL = 60 * 60 * 24 * 7  # 7 dias


@celery_app.task(
    bind=True,
    name="workers.linkedin_poll.linkedin_poll_tick",
    max_retries=1,
    queue="cadence",
)
def linkedin_poll_tick(self) -> dict:
    """Polling de inbox LinkedIn para contas nativas."""
    return asyncio.run(_poll_async())


async def _poll_async() -> dict:
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from core.config import settings
    from core.redis_client import redis_client
    from models.linkedin_account import LinkedInAccount
    from services.linkedin_account_service import decrypt_credential

    engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    processed = 0
    errors = 0

    async with session_factory() as db:
        result = await db.execute(
            select(LinkedInAccount).where(
                LinkedInAccount.provider_type == "native",
                LinkedInAccount.is_active == True,  # noqa: E712
                LinkedInAccount.li_at_cookie.isnot(None),
            )
        )
        accounts = list(result.scalars().all())

    for account in accounts:
        try:
            li_at = decrypt_credential(account.li_at_cookie)
            cursor_key = _CURSOR_KEY.format(account_id=str(account.id))
            cursor = await redis_client.get(cursor_key)
            if isinstance(cursor, bytes):
                cursor = cursor.decode()

            count = await _poll_account(
                account_id=str(account.id),
                tenant_id=str(account.tenant_id),
                li_at=li_at,
                cursor=cursor,
                redis=redis_client,
                cursor_key=cursor_key,
            )
            processed += count
        except Exception as exc:
            errors += 1
            logger.error(
                "linkedin_poll.account_error",
                account_id=str(account.id),
                error=str(exc),
            )

    await engine.dispose()
    return {"processed": processed, "errors": errors}


async def _poll_account(
    account_id: str,
    tenant_id: str,
    li_at: str,
    cursor: str | None,
    redis: Any,
    cursor_key: str,
) -> int:
    """Processa mensagens novas de uma conta nativa."""
    from integrations.linkedin.native_provider import NativeLinkedInProvider

    provider = NativeLinkedInProvider(li_at=li_at)
    result = await provider.list_conversations(cursor=cursor, limit=50)
    conversations = result.get("items", [])
    new_cursor = result.get("cursor")

    if not conversations:
        return 0

    processed = 0
    for conv in conversations:
        try:
            messages = await provider.get_messages(
                conversation_id=conv.conversation_id,
                limit=20,
            )
            for msg in messages:
                if msg.is_own:
                    continue
                await _handle_native_message(
                    account_id=account_id,
                    tenant_id=tenant_id,
                    conversation_id=conv.conversation_id,
                    attendee_id=conv.attendee_id,
                    attendee_name=conv.attendee_name,
                    message=msg,
                )
                processed += 1
        except Exception as exc:
            logger.warning(
                "linkedin_poll.conv_error",
                conversation_id=conv.conversation_id,
                error=str(exc),
            )

    # Atualiza cursor no Redis
    if new_cursor:
        await redis.set(cursor_key, new_cursor, ex=_CURSOR_TTL)
    elif conversations:
        # Usa o timestamp da última conversa como novo cursor
        last = conversations[-1]
        if last.last_message_at:
            await redis.set(cursor_key, last.last_message_at, ex=_CURSOR_TTL)

    logger.info(
        "linkedin_poll.account_done",
        account_id=account_id,
        conversations=len(conversations),
        messages_processed=processed,
    )
    return processed


async def _handle_native_message(
    account_id: str,
    tenant_id: str,
    conversation_id: str,
    attendee_id: str,
    attendee_name: str,
    message: Any,
) -> None:
    """
    Processa uma mensagem recebida via polling nativo.
    Replica o fluxo do webhook Unipile: encontra lead, salva Interaction, atualiza step.
    """
    import uuid as _uuid_mod

    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from core.config import settings
    from integrations.llm import LLMRegistry
    from models.cadence_step import CadenceStep
    from models.enums import Channel, Intent, InteractionDirection, StepStatus
    from models.interaction import Interaction
    from models.lead import Lead
    from services.reply_parser import ReplyParser

    tid = _uuid_mod.UUID(tenant_id)

    engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as db:
        # Busca lead pelo linkedin_profile_id
        lead_result = await db.execute(
            select(Lead).where(
                Lead.tenant_id == tid,
                Lead.linkedin_profile_id == attendee_id,
            )
        )
        lead = lead_result.scalar_one_or_none()
        if not lead:
            logger.debug(
                "linkedin_poll.lead_not_found",
                attendee_id=attendee_id,
                tenant_id=tenant_id,
            )
            await engine.dispose()
            return

        # Evita duplicatas — checa se a mensagem já foi processada
        existing = await db.execute(
            select(Interaction).where(
                Interaction.tenant_id == tid,
                Interaction.unipile_message_id == message.id,
            )
        )
        if existing.scalar_one_or_none() is not None:
            await engine.dispose()
            return

        # Parse da intenção via LLM
        from core.redis_client import redis_client  # noqa: PLC0415

        registry = LLMRegistry(settings=settings, redis=redis_client)
        parser = ReplyParser(registry=registry)
        intent_str, summary = await parser.parse(message.text or "")
        try:
            intent = Intent(intent_str)
        except ValueError:
            intent = Intent.NEUTRAL

        # Salva Interaction inbound
        interaction = Interaction(
            tenant_id=tid,
            lead_id=lead.id,
            channel=Channel.LINKEDIN_DM,
            direction=InteractionDirection.INBOUND,
            content_text=message.text or "",
            intent=intent,
            unipile_message_id=message.id,
            unipile_chat_id=conversation_id,
        )
        db.add(interaction)

        # Atualiza step mais recente SENT → REPLIED
        step_result = await db.execute(
            select(CadenceStep)
            .where(
                CadenceStep.lead_id == lead.id,
                CadenceStep.status == StepStatus.SENT,
                CadenceStep.channel.in_([Channel.LINKEDIN_DM, Channel.LINKEDIN_CONNECT]),
            )
            .order_by(CadenceStep.sent_at.desc())
            .limit(1)
        )
        step = step_result.scalar_one_or_none()
        if step:
            step.status = StepStatus.REPLIED

        # Atualiza lead
        lead.last_reply_at = datetime.now(tz=timezone.utc)
        if intent == Intent.INTEREST:
            lead.linkedin_connection_status = "replied"

        await db.commit()
        logger.info(
            "linkedin_poll.message_processed",
            lead_id=str(lead.id),
            intent=intent.value,
            tenant_id=tenant_id,
        )

    await engine.dispose()
