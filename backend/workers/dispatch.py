"""
workers/dispatch.py

Task Celery para despachar um step de cadência — o coração do sistema.

Task:
  dispatch_step(step_id, tenant_id)
    — Carrega CadenceStep, Lead, Cadence do banco
    — Busca contexto do website via ContextFetcher (cache 24h)
    — Gera mensagem personalizada via AIComposer (LLMRegistry)
    — Se use_voice=True: Speechify → MP3 → Unipile voice note
    — Senão: envia texto via Unipile (LinkedIn connect/DM ou e-mail)
    — Salva Interaction outbound
    — Atualiza step.status = SENT + step.sent_at = now()
    — Fila: "dispatch"

Em caso de falha:
  - retry automático (max 3x, backoff 60s)
  - Se falha definitiva: step.status = FAILED

Segurança anti-duplicata:
  - Verifica step.status antes de processar (idempotência)
  - Se já SENT/FAILED/SKIPPED → retorna imediatamente
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import structlog
from sqlalchemy import select

from workers.celery_app import celery_app

if TYPE_CHECKING:
    from models.lead import Lead

logger = structlog.get_logger()


@celery_app.task(
    bind=True,
    name="workers.dispatch.dispatch_step",
    max_retries=3,
    default_retry_delay=60,
    queue="dispatch",
)
def dispatch_step(self, step_id: str, tenant_id: str) -> dict:
    """
    Executa o envio de um step de cadência.
    Retorna dict com step_id, channel, status.
    """
    return asyncio.get_event_loop().run_until_complete(
        _dispatch_async(step_id, tenant_id, self)
    )


async def _dispatch_async(step_id: str, tenant_id: str, task) -> dict:  # type: ignore[type-arg]
    from core.database import get_session
    from integrations.context_fetcher import context_fetcher
    from integrations.llm import LLMRegistry
    from integrations.tts import TTSRegistry
    from integrations.unipile_client import unipile_client
    from models.cadence import Cadence
    from models.cadence_step import CadenceStep
    from models.enums import Channel, InteractionDirection, StepStatus
    from models.interaction import Interaction
    from models.lead import Lead
    from services.ai_composer import AIComposer
    from core.config import settings
    from core.redis_client import redis_client

    tid = uuid.UUID(tenant_id)
    sid = uuid.UUID(step_id)

    async for db in get_session(tid):
        # ── Carrega step ─────────────────────────────────────────────
        step_result = await db.execute(
            select(CadenceStep).where(CadenceStep.id == sid)
        )
        step = step_result.scalar_one_or_none()
        if not step:
            logger.warning("dispatch.step_not_found", step_id=step_id)
            return {"step_id": step_id, "status": "not_found"}

        # Idempotência — step já processado
        if step.status != StepStatus.PENDING:
            logger.info(
                "dispatch.step_already_processed",
                step_id=step_id,
                status=step.status.value,
            )
            return {"step_id": step_id, "status": step.status.value}

        # ── Carrega Lead e Cadence ────────────────────────────────────
        lead_result = await db.execute(select(Lead).where(Lead.id == step.lead_id))
        lead = lead_result.scalar_one_or_none()

        cadence_result = await db.execute(
            select(Cadence).where(Cadence.id == step.cadence_id)
        )
        cadence = cadence_result.scalar_one_or_none()

        if not lead or not cadence:
            step.status = StepStatus.FAILED
            await db.commit()
            logger.error("dispatch.missing_lead_or_cadence", step_id=step_id)
            return {"step_id": step_id, "status": "failed"}

        try:
            # ── Contexto do website (cache 24h, assíncrono) ───────────
            context: dict = {}
            if lead.website:
                website_text = await context_fetcher.fetch_from_website(lead.website)
                context["website"] = website_text
            elif lead.company:
                company_text = await context_fetcher.search_company(
                    lead.company, lead.website
                )
                context["company_info"] = company_text

            # ── Composição de mensagem via LLM ────────────────────────
            registry = LLMRegistry(settings=settings, redis=redis_client)
            composer = AIComposer(registry=registry)
            message_text = await composer.compose(
                lead=lead,
                channel=step.channel.value,
                step_number=step.step_number,
                context=context,
                cadence=cadence,
            )

            # ── Envio via Unipile ─────────────────────────────────────
            content_audio_url: str | None = None

            if step.channel == Channel.LINKEDIN_CONNECT:
                result = await unipile_client.send_linkedin_connect(
                    account_id=settings.UNIPILE_ACCOUNT_ID_LINKEDIN or "",
                    linkedin_profile_id=lead.linkedin_profile_id or "",
                    message=message_text,
                )

            elif step.channel == Channel.LINKEDIN_DM:
                if step.use_voice:
                    # Gera voice note MP3 via TTSRegistry, armazena no Redis e passa URL para Unipile
                    tts_registry = TTSRegistry(settings=settings, redis=redis_client)
                    tts_provider = cadence.tts_provider or settings.VOICE_PROVIDER
                    tts_voice_id = cadence.tts_voice_id or settings.SPEECHIFY_VOICE_ID
                    audio_bytes = await tts_registry.synthesize(
                        provider=tts_provider,
                        voice_id=tts_voice_id,
                        text=message_text,
                    )
                    audio_key = str(uuid.uuid4())
                    await redis_client.set_bytes(f"audio:{audio_key}", audio_bytes, ttl=3600)
                    audio_url = f"{settings.API_PUBLIC_URL}/audio/{audio_key}"
                    result = await unipile_client.send_linkedin_voice_note(
                        account_id=settings.UNIPILE_ACCOUNT_ID_LINKEDIN or "",
                        linkedin_profile_id=lead.linkedin_profile_id or "",
                        audio_url=audio_url,
                    )
                    content_audio_url = audio_url
                else:
                    result = await unipile_client.send_linkedin_dm(
                        account_id=settings.UNIPILE_ACCOUNT_ID_LINKEDIN or "",
                        linkedin_profile_id=lead.linkedin_profile_id or "",
                        message=message_text,
                    )

            elif step.channel == Channel.EMAIL:
                email_to = lead.email_corporate or lead.email_personal or ""
                if not email_to:
                    step.status = StepStatus.SKIPPED
                    await db.commit()
                    return {"step_id": step_id, "status": "skipped", "reason": "no_email"}

                result = await unipile_client.send_email(
                    account_id=settings.UNIPILE_ACCOUNT_ID_GMAIL or "",
                    to_email=email_to,
                    subject=_build_email_subject(lead, step.step_number),
                    body_html=message_text,
                )

            elif step.channel == Channel.MANUAL_TASK:
                # MANUAL_TASK: não envia mensagem — notifica admin via email
                from services.notification import send_manual_task_notification
                await send_manual_task_notification(
                    lead=lead,
                    cadence_name=cadence.name,
                    step_number=step.step_number,
                    message=message_text,
                    tenant_id=tid,
                    db=db,
                )
                # Fake result para manter o fluxo
                class _FakeResult:
                    success = True
                    message_id = None
                result = _FakeResult()

            else:
                step.status = StepStatus.SKIPPED
                await db.commit()
                return {"step_id": step_id, "status": "skipped", "reason": "unknown_channel"}

            # ── Salva Interaction outbound ────────────────────────────
            now = datetime.now(tz=timezone.utc)
            interaction = Interaction(
                id=uuid.uuid4(),
                tenant_id=tid,
                lead_id=lead.id,
                channel=step.channel,
                direction=InteractionDirection.OUTBOUND,
                content_text=message_text,
                content_audio_url=content_audio_url,
                unipile_message_id=result.message_id if result.success else None,
                created_at=now,
            )
            db.add(interaction)

            # ── Atualiza step ─────────────────────────────────────────
            step.status = StepStatus.SENT
            step.sent_at = now

            await db.commit()

            logger.info(
                "dispatch.sent",
                step_id=step_id,
                channel=step.channel.value,
                lead_id=str(lead.id),
                use_voice=step.use_voice,
            )
            return {"step_id": step_id, "channel": step.channel.value, "status": "sent"}

        except Exception as exc:
            logger.error(
                "dispatch.error",
                step_id=step_id,
                error=str(exc),
            )
            try:
                raise task.retry(exc=exc)
            except task.MaxRetriesExceededError:
                step.status = StepStatus.FAILED
                await db.commit()
                return {"step_id": step_id, "status": "failed", "error": str(exc)}

    return {"step_id": step_id, "status": "error", "error": "no_session"}


def _build_email_subject(lead: "Lead", step_number: int) -> str:
    """Gera assunto do e-mail baseado na empresa e número do step."""
    from models.lead import Lead
    company = lead.company or lead.name
    if step_number == 1:
        return f"Uma ideia para {company}"
    return f"Re: Uma ideia para {company}"
