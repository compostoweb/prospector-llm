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
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

import structlog
from sqlalchemy import select

from core.config import settings
from core.database import get_worker_session
from core.redis_client import redis_client
from integrations.context_fetcher import context_fetcher
from integrations.llm import LLMRegistry
from integrations.llm.base import LLMNonRetryableError, close_async_resource
from integrations.unipile_client import UnipileNonRetryableError, unipile_client
from services.ai_composer import AIComposer, resolve_step_key
from services.cadence_delivery_budget import build_account_rate_limit_key
from services.cadence_manager import (
    get_previous_template_channel,
    get_template_step_config,
    get_total_template_steps,
)
from services.editorial_validator import validate_editorial_output
from services.email_account_service import resolve_outbound_email_account
from services.email_event_service import build_outbound_email_delivery_observation
from services.message_quality import (
    build_fallback_email_subject,
    normalize_email_subject,
    normalize_generated_text,
    plain_text_email_to_html,
)
from services.message_template_renderer import (
    render_message_template,
    render_saved_email_template,
)
from workers.celery_app import celery_app

if TYPE_CHECKING:
    from models.lead import Lead

logger = structlog.get_logger()


@dataclass
class _DispatchResult:
    success: bool
    message_id: str | None = None


@celery_app.task(
    bind=True,
    name="workers.dispatch.dispatch_step",
    max_retries=1,
    default_retry_delay=60,
    queue="dispatch",
)
def dispatch_step(self, step_id: str, tenant_id: str) -> dict:
    """
    Executa o envio de um step de cadência.
    Retorna dict com step_id, channel, status.
    """
    return asyncio.run(_dispatch_async(step_id, tenant_id, self))


async def _dispatch_async(step_id: str, tenant_id: str, task) -> dict:  # type: ignore[type-arg]

    tid = uuid.UUID(tenant_id)
    sid = uuid.UUID(step_id)

    # ── Lock distribuído Redis — impede processamento duplicado ────
    lock_key = f"dispatch:lock:{step_id}"
    lock_acquired = await redis_client.set_if_absent(lock_key, "1", ttl=300)
    if not lock_acquired:
        logger.info("dispatch.lock_exists", step_id=step_id)
        return {"step_id": step_id, "status": "locked"}

    try:
        return await _dispatch_inner(step_id, tenant_id, tid, sid, task, lock_key)
    finally:
        await redis_client.delete(lock_key)


async def _dispatch_inner(
    step_id: str,
    tenant_id: str,
    tid: uuid.UUID,
    sid: uuid.UUID,
    task,  # type: ignore[type-arg]
    lock_key: str,
) -> dict:
    from models.cadence import Cadence
    from models.cadence_step import CadenceStep
    from models.enums import Channel, InteractionDirection, StepStatus
    from models.interaction import Interaction
    from models.lead import Lead
    from models.tenant import TenantIntegration

    async for db in get_worker_session(tid):
        # ── Carrega step ─────────────────────────────────────────────
        step_result = await db.execute(select(CadenceStep).where(CadenceStep.id == sid))
        step = step_result.scalar_one_or_none()
        if not step:
            logger.warning("dispatch.step_not_found", step_id=step_id)
            return {"step_id": step_id, "status": "not_found"}

        # Idempotência — aceita PENDING (legado) e DISPATCHING (novo fluxo)
        if step.status not in (StepStatus.PENDING, StepStatus.DISPATCHING):
            logger.info(
                "dispatch.step_already_processed",
                step_id=step_id,
                status=step.status.value,
            )
            return {"step_id": step_id, "status": step.status.value}

        step_channel = step.channel
        account_rate_limit_key: str | None = None

        async def _release_rate_limit_slot() -> None:
            await redis_client.release_rate_limit(step_channel.value, tid)
            if account_rate_limit_key:
                await redis_client.release_rate_limit_key(account_rate_limit_key)

        # ── Carrega Lead e Cadence ────────────────────────────────────
        lead_result = await db.execute(select(Lead).where(Lead.id == step.lead_id))
        lead = lead_result.scalar_one_or_none()

        cadence_result = await db.execute(select(Cadence).where(Cadence.id == step.cadence_id))
        cadence = cadence_result.scalar_one_or_none()

        if not lead or not cadence:
            step.status = StepStatus.FAILED
            await db.commit()
            await _release_rate_limit_slot()
            logger.error("dispatch.missing_lead_or_cadence", step_id=step_id)
            return {"step_id": step_id, "status": "failed"}

        # ── Cadência desativada — não despachar ──────────────────
        if not cadence.is_active:
            step.status = StepStatus.SKIPPED
            await db.commit()
            await _release_rate_limit_slot()
            logger.info(
                "dispatch.cadence_inactive",
                step_id=step_id,
                cadence_id=str(cadence.id),
            )
            return {"step_id": step_id, "status": "skipped"}

        # ── Resolve account_ids do tenant (fallback para settings globais) ──
        integ_result = await db.execute(
            select(TenantIntegration).where(TenantIntegration.tenant_id == tid)
        )
        integration = integ_result.scalar_one_or_none()
        account_rate_limit_key = build_account_rate_limit_key(
            cadence=cadence,
            integration=integration,
            channel=step.channel,
        )

        # ── Circuit breaker — muitas falhas seguidas pausam o tenant ──
        cb_key = f"dispatch:failures:{tenant_id}"
        cb_count = await redis_client.get(cb_key)
        if cb_count and int(cb_count) >= 5:
            # Reverter para PENDING para re-tentar depois da pausa
            step.status = StepStatus.PENDING
            await db.commit()
            await _release_rate_limit_slot()
            logger.warning(
                "dispatch.circuit_breaker_open",
                step_id=step_id,
                tenant_id=tenant_id,
                failure_count=int(cb_count),
            )
            return {"step_id": step_id, "status": "circuit_breaker"}

        linkedin_account_id = (
            (integration and integration.unipile_linkedin_account_id)
            or settings.UNIPILE_ACCOUNT_ID_LINKEDIN
            or ""
        )
        gmail_account_id = (
            (integration and integration.unipile_gmail_account_id)
            or settings.UNIPILE_ACCOUNT_ID_GMAIL
            or ""
        )

        registry: LLMRegistry | None = None
        try:
            # ── Contexto do website (cache 24h, assíncrono) ───────────
            context: dict = {}
            if lead.website:
                website_text = await context_fetcher.fetch_from_website(lead.website)
                context["website"] = website_text
            elif lead.company:
                company_text = await context_fetcher.search_company(lead.company, lead.website)
                context["company_info"] = company_text

            # ── Composição de mensagem via LLM ────────────────────────
            # LINKEDIN_POST_REACTION não precisa de LLM — apenas reage ao post
            # EMAIL usa compose_email() diretamente no branch abaixo (gera subject+body em chamada única)
            registry = LLMRegistry(settings=settings, redis=redis_client)
            composer = AIComposer(registry=registry)
            template_step = get_template_step_config(cadence, step.step_number)
            previous_channel = get_previous_template_channel(cadence, step.step_number)
            total_steps = get_total_template_steps(cadence)
            configured_step_type = (
                str(template_step.get("step_type"))
                if template_step and template_step.get("step_type")
                else None
            )
            configured_message = render_message_template(
                template_step.get("message_template") if template_step else None,
                lead,
            )
            if configured_message:
                configured_message = normalize_generated_text(configured_message)
            if step.channel not in (Channel.LINKEDIN_POST_REACTION, Channel.EMAIL):
                if configured_message:
                    message_text = configured_message
                elif step.composed_text:
                    # Cache hit — reusa composição anterior (retry/re-enqueue)
                    message_text = step.composed_text
                    logger.info("dispatch.compose_cache_hit", step_id=step_id)
                else:
                    message_text = await composer.compose(
                        lead=lead,
                        channel=step.channel.value,
                        step_number=step.step_number,
                        context=context,
                        cadence=cadence,
                        total_steps=total_steps,
                        use_voice=step.use_voice,
                        previous_channel=previous_channel,
                        step_type=configured_step_type,
                    )
                    # Persiste cache de composição para retry
                    step.composed_text = message_text
                    await db.flush()
            else:
                message_text = ""

            step_key = resolve_step_key(
                step.channel.value,
                step.step_number,
                total_steps,
                use_voice=step.use_voice,
                previous_channel=previous_channel,
                step_type=configured_step_type,
            )

            if step.channel not in (Channel.EMAIL, Channel.LINKEDIN_POST_REACTION):
                editorial_validation = validate_editorial_output(step_key, message_text)
                if not editorial_validation.ok or editorial_validation.warning_count:
                    logger.warning(
                        "dispatch.editorial_validation",
                        step_id=step_id,
                        channel=step.channel.value,
                        step_key=step_key,
                        hard_failures=editorial_validation.hard_failure_count,
                        warnings=editorial_validation.warning_count,
                        issues=[issue.code for issue in editorial_validation.issues],
                    )

            # ── Envio via canal LinkedIn / Email ──────────────────────
            content_audio_url: str | None = None
            # Interaction pré-criada pelo canal EMAIL (necessário antes do envio para o pixel)
            email_interaction: Interaction | None = None
            email_account = None
            email_send_account = None
            email_provider_type: str | None = None
            email_delivery_observation = None
            result: _DispatchResult

            if step.channel == Channel.LINKEDIN_CONNECT:
                if getattr(cadence, "linkedin_account_id", None):
                    # Usa LinkedInRegistry com conta configurada na cadência
                    from integrations.linkedin import LinkedInRegistry as _LIR  # noqa: PLC0415
                    from models.linkedin_account import LinkedInAccount as _LIA  # noqa: PLC0415

                    _li_acc_q = await db.execute(
                        select(_LIA).where(_LIA.id == cadence.linkedin_account_id)
                    )
                    _li_account = _li_acc_q.scalar_one_or_none()
                    if _li_account is None:
                        step.status = StepStatus.SKIPPED
                        await db.commit()
                        await _release_rate_limit_slot()
                        return {
                            "step_id": step_id,
                            "status": "skipped",
                            "reason": "linkedin_account_not_found",
                        }
                    _li_registry = _LIR(settings=settings)
                    _li_result = await _li_registry.send_connect(
                        account=_li_account,
                        linkedin_profile_id=lead.linkedin_profile_id or "",
                        message=message_text,
                    )
                    result = _DispatchResult(
                        success=_li_result.success,
                        message_id=_li_result.message_id,
                    )
                else:
                    connect_result = await unipile_client.send_linkedin_connect(
                        account_id=linkedin_account_id,
                        linkedin_profile_id=lead.linkedin_profile_id or "",
                        message=message_text,
                    )
                    result = _DispatchResult(
                        success=connect_result.success,
                        message_id=connect_result.message_id,
                    )

            elif step.channel == Channel.LINKEDIN_DM:
                if step.use_voice:
                    # Voice note — pode ser áudio pré-gravado (S3) ou TTS gerado
                    if step.audio_file_id:
                        # Áudio pré-gravado no S3 — só passa a URL
                        from models.audio_file import AudioFile

                        af_result = await db.execute(
                            select(AudioFile).where(AudioFile.id == step.audio_file_id)
                        )
                        audio_file = af_result.scalar_one_or_none()
                        if audio_file:
                            audio_url = audio_file.url
                        else:
                            logger.warning(
                                "dispatch.audio_file_not_found",
                                audio_file_id=str(step.audio_file_id),
                            )
                            # Fallback: gera via TTS
                            audio_url = await _generate_tts_audio(
                                cadence,
                                message_text,
                                settings,
                                redis_client,
                            )
                    else:
                        # Gera via TTS
                        audio_url = await _generate_tts_audio(
                            cadence,
                            message_text,
                            settings,
                            redis_client,
                        )

                    voice_result = await unipile_client.send_linkedin_voice_note(
                        account_id=linkedin_account_id,
                        linkedin_profile_id=lead.linkedin_profile_id or "",
                        audio_url=audio_url,
                    )
                    result = _DispatchResult(
                        success=voice_result.success,
                        message_id=voice_result.message_id,
                    )
                    content_audio_url = audio_url
                else:
                    if getattr(cadence, "linkedin_account_id", None):
                        from integrations.linkedin import LinkedInRegistry as _LIR  # noqa: PLC0415
                        from models.linkedin_account import LinkedInAccount as _LIA  # noqa: PLC0415

                        _li_acc_q = await db.execute(
                            select(_LIA).where(_LIA.id == cadence.linkedin_account_id)
                        )
                        _li_account = _li_acc_q.scalar_one_or_none()
                        if _li_account is None:
                            step.status = StepStatus.SKIPPED
                            await db.commit()
                            await _release_rate_limit_slot()
                            return {
                                "step_id": step_id,
                                "status": "skipped",
                                "reason": "linkedin_account_not_found",
                            }
                        _li_registry = _LIR(settings=settings)
                        _li_result = await _li_registry.send_dm(
                            account=_li_account,
                            linkedin_profile_id=lead.linkedin_profile_id or "",
                            message=message_text,
                        )
                        result = _DispatchResult(
                            success=_li_result.success,
                            message_id=_li_result.message_id,
                        )
                    else:
                        dm_result = await unipile_client.send_linkedin_dm(
                            account_id=linkedin_account_id,
                            linkedin_profile_id=lead.linkedin_profile_id or "",
                            message=message_text,
                        )
                        result = _DispatchResult(
                            success=dm_result.success,
                            message_id=dm_result.message_id,
                        )

            elif step.channel == Channel.EMAIL:
                import random as _random  # noqa: PLC0415

                from models.email_template import EmailTemplate  # noqa: PLC0415
                from models.email_unsubscribe import EmailUnsubscribe  # noqa: PLC0415
                from services.email_footer import inject_tracking  # noqa: PLC0415

                email_to = lead.email_corporate or lead.email_personal or ""
                if not email_to:
                    step.status = StepStatus.SKIPPED
                    await db.commit()
                    await _release_rate_limit_slot()
                    return {"step_id": step_id, "status": "skipped", "reason": "no_email"}

                # Verifica bounce
                if lead.email_bounced_at is not None:
                    step.status = StepStatus.SKIPPED
                    await db.commit()
                    await _release_rate_limit_slot()
                    return {"step_id": step_id, "status": "skipped", "reason": "email_bounced"}

                # Verifica descadastro
                unsub_q = await db.execute(
                    select(EmailUnsubscribe).where(
                        EmailUnsubscribe.tenant_id == tid,
                        EmailUnsubscribe.email == email_to.lower(),
                    )
                )
                if unsub_q.scalar_one_or_none() is not None:
                    step.status = StepStatus.SKIPPED
                    await db.commit()
                    await _release_rate_limit_slot()
                    return {"step_id": step_id, "status": "skipped", "reason": "unsubscribed"}

                subject_variants = template_step.get("subject_variants") if template_step else None
                configured_email_template_id = (
                    template_step.get("email_template_id") if template_step else None
                )

                if configured_email_template_id:
                    email_template: EmailTemplate | None = None
                    email_body_is_html = False
                    try:
                        template_uuid = uuid.UUID(str(configured_email_template_id))
                        template_result = await db.execute(
                            select(EmailTemplate).where(
                                EmailTemplate.id == template_uuid,
                                EmailTemplate.tenant_id == tid,
                                EmailTemplate.is_active.is_(True),
                            )
                        )
                        email_template = template_result.scalar_one_or_none()
                    except ValueError:
                        email_template = None

                    if email_template is not None:
                        subject, message_text = render_saved_email_template(email_template, lead)
                        subject = normalize_email_subject(subject)
                        email_body_is_html = True
                    else:
                        logger.warning(
                            "dispatch.email_template_not_found",
                            cadence_id=str(cadence.id),
                            step_id=step_id,
                            email_template_id=str(configured_email_template_id),
                        )
                        configured_email_template_id = None

                if not configured_email_template_id:
                    email_body_is_html = False
                    if configured_message:
                        subject = _build_email_subject(lead, step.step_number)
                        message_text = configured_message
                    elif step.composed_text and step.composed_subject:
                        # Cache hit — reusa composição anterior (retry/re-enqueue)
                        subject = step.composed_subject
                        message_text = step.composed_text
                        logger.info("dispatch.compose_email_cache_hit", step_id=step_id)
                    else:
                        # Gera subject + body via LLM em chamada única (JSON internamente)
                        subject, message_text = await composer.compose_email(
                            lead=lead,
                            step_number=step.step_number,
                            context=context,
                            cadence=cadence,
                            step_type=configured_step_type,
                            total_steps=total_steps,
                            previous_channel=previous_channel,
                        )
                        # Persiste cache de composição para retry
                        step.composed_text = message_text
                        step.composed_subject = subject
                        await db.flush()

                # A/B override: se cadência tem subject_variants configurado, tem prioridade
                if subject_variants:
                    cleaned_variants = [
                        str(item).strip() for item in subject_variants if str(item).strip()
                    ]
                    if cleaned_variants:
                        subject = normalize_email_subject(_random.choice(cleaned_variants))
                subject = normalize_email_subject(subject)
                email_editorial_validation = validate_editorial_output(
                    step_key,
                    message_text,
                    subject=subject,
                )
                if not email_editorial_validation.ok or email_editorial_validation.warning_count:
                    logger.warning(
                        "dispatch.editorial_validation",
                        step_id=step_id,
                        channel=step.channel.value,
                        step_key=step_key,
                        hard_failures=email_editorial_validation.hard_failure_count,
                        warnings=email_editorial_validation.warning_count,
                        issues=[issue.code for issue in email_editorial_validation.issues],
                    )
                # Persiste subject para analytics de open-rate
                step.subject_used = subject

                if getattr(cadence, "email_account_id", None):
                    from sqlalchemy import select as _sel  # noqa: PLC0415

                    from models.email_account import EmailAccount  # noqa: PLC0415

                    _acc_result = await db.execute(
                        _sel(EmailAccount).where(EmailAccount.id == cadence.email_account_id)
                    )
                    email_account = _acc_result.scalar_one_or_none()
                    if email_account is None:
                        logger.warning(
                            "dispatch.email_account_not_found",
                            cadence_id=str(cadence.id),
                            email_account_id=str(cadence.email_account_id),
                        )
                        step.status = StepStatus.SKIPPED
                        await db.commit()
                        await _release_rate_limit_slot()
                        return {
                            "step_id": step_id,
                            "status": "skipped",
                            "reason": "email_account_not_found",
                        }

                # Pré-cria Interaction antes do envio para ter o ID para o pixel de rastreamento
                now_pre = datetime.now(tz=UTC)
                email_interaction = Interaction(
                    id=uuid.uuid4(),
                    tenant_id=tid,
                    lead_id=lead.id,
                    channel=Channel.EMAIL,
                    direction=InteractionDirection.OUTBOUND,
                    content_text=message_text,
                    created_at=now_pre,
                )
                db.add(email_interaction)
                await db.flush()  # garante email_interaction.id sem commit

                if email_account is not None:
                    email_send_account = await resolve_outbound_email_account(db, email_account)

                # Injeta pixel de abertura e rodapé de descadastro
                tracked_html = inject_tracking(
                    body_html=message_text
                    if email_body_is_html
                    else plain_text_email_to_html(message_text),
                    interaction_id=email_interaction.id,
                    tenant_id=tid,
                    email=email_to,
                    signature_html=getattr(
                        email_send_account or email_account, "email_signature", None
                    ),
                )

                # Usa EmailRegistry se a cadência tem email_account_id configurado
                if email_account is not None:
                    from core.config import settings as _cfg  # noqa: PLC0415
                    from integrations.email import (
                        EmailRegistry,  # noqa: PLC0415
                        EmailSendResult,  # noqa: PLC0415
                    )

                    _registry = EmailRegistry(settings=_cfg)
                    account_for_send = email_send_account or email_account
                    email_provider_type = str(account_for_send.provider_type)
                    _send_result = cast(
                        EmailSendResult,
                        await _registry.send(
                            account=account_for_send,
                            to_email=email_to,
                            subject=subject,
                            body_html=tracked_html,
                            from_name=account_for_send.from_name or account_for_send.display_name,
                        ),
                    )
                    result = _DispatchResult(
                        success=_send_result.success,
                        message_id=_send_result.message_id,
                    )
                else:
                    # Fallback: usa Unipile global (comportamento anterior)
                    email_provider_type = "unipile_gmail"
                    _r = await unipile_client.send_email(
                        account_id=gmail_account_id,
                        to_email=email_to,
                        subject=subject,
                        body_html=tracked_html,
                    )
                    result = _DispatchResult(success=_r.success, message_id=_r.message_id)

                email_interaction.unipile_message_id = result.message_id if result.success else None
                email_delivery_observation = build_outbound_email_delivery_observation(
                    email_provider_type,
                    success=result.success,
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
                result = _DispatchResult(success=True)

            elif step.channel == Channel.LINKEDIN_POST_REACTION:
                # Não usa LLM — reage diretamente ao post mais recente do lead
                if not lead.linkedin_profile_id:
                    step.status = StepStatus.SKIPPED
                    await db.commit()
                    await _release_rate_limit_slot()
                    return {
                        "step_id": step_id,
                        "status": "skipped",
                        "reason": "no_linkedin_profile_id",
                    }

                reacted = await unipile_client.react_to_latest_post(
                    account_id=linkedin_account_id,
                    provider_id=lead.linkedin_profile_id,
                    emoji="LIKE",
                )
                if not reacted:
                    step.status = StepStatus.SKIPPED
                    await db.commit()
                    await _release_rate_limit_slot()
                    logger.info(
                        "dispatch.post_reaction.skipped",
                        step_id=step_id,
                        lead_id=str(lead.id),
                        reason="no_recent_post",
                    )
                    return {"step_id": step_id, "status": "skipped", "reason": "no_recent_post"}

                # message_text fica vazio pois não é mensagem de texto
                message_text = ""

                result = _DispatchResult(success=True)

            elif step.channel == Channel.LINKEDIN_POST_COMMENT:
                if not lead.linkedin_profile_id:
                    step.status = StepStatus.SKIPPED
                    await db.commit()
                    await _release_rate_limit_slot()
                    return {
                        "step_id": step_id,
                        "status": "skipped",
                        "reason": "no_linkedin_profile_id",
                    }

                # message_text já foi gerado pelo composer (deve ser o comentário)
                commented = await unipile_client.comment_on_latest_post(
                    account_id=linkedin_account_id,
                    provider_id=lead.linkedin_profile_id,
                    comment_text=message_text,
                )
                if not commented:
                    step.status = StepStatus.SKIPPED
                    await db.commit()
                    await _release_rate_limit_slot()
                    logger.info(
                        "dispatch.post_comment.skipped",
                        step_id=step_id,
                        lead_id=str(lead.id),
                        reason="no_recent_post",
                    )
                    return {"step_id": step_id, "status": "skipped", "reason": "no_recent_post"}

                result = _DispatchResult(success=True)

            elif step.channel == Channel.LINKEDIN_INMAIL:
                if not lead.linkedin_profile_id:
                    step.status = StepStatus.SKIPPED
                    await db.commit()
                    await _release_rate_limit_slot()
                    return {
                        "step_id": step_id,
                        "status": "skipped",
                        "reason": "no_linkedin_profile_id",
                    }

                # Composer retorna JSON: {"subject": "...", "body": "..."}
                try:
                    import json as _json  # noqa: PLC0415

                    inmail_data = _json.loads(message_text)
                    inmail_subject = inmail_data.get("subject", "")
                    inmail_body = inmail_data.get("body", message_text)
                except (ValueError, KeyError):
                    # Fallback: usa message_text como corpo sem assunto
                    inmail_subject = ""
                    inmail_body = message_text

                inmail_result = await unipile_client.send_linkedin_inmail(
                    account_id=linkedin_account_id,
                    linkedin_profile_id=lead.linkedin_profile_id,
                    subject=inmail_subject,
                    message=inmail_body,
                )
                result = _DispatchResult(
                    success=inmail_result.success,
                    message_id=inmail_result.message_id,
                )
                # Salva o corpo efetivo como content_text
                message_text = inmail_body

            else:
                step.status = StepStatus.SKIPPED
                await db.commit()
                await _release_rate_limit_slot()
                return {"step_id": step_id, "status": "skipped", "reason": "unknown_channel"}

            # ── Salva Interaction outbound ────────────────────────────
            now = datetime.now(tz=UTC)
            if email_interaction is not None:
                # EMAIL: interaction já pré-criada e adicionada; só garante o now
                interaction = email_interaction
                now = email_interaction.created_at  # type: ignore[assignment]
            else:
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
                delivery_state=email_delivery_observation.state
                if email_delivery_observation
                else None,
                delivery_confirmed=(
                    email_delivery_observation.confirmed if email_delivery_observation else None
                ),
            )

            # Sucesso — reseta circuit breaker
            cb_key = f"dispatch:failures:{tenant_id}"
            await redis_client.delete(cb_key)

            return {"step_id": step_id, "channel": step.channel.value, "status": "sent"}

        except LLMNonRetryableError as exc:
            # Erro permanente de LLM (billing, auth, config) — NÃO retentar
            logger.error(
                "dispatch.permanent_llm_error",
                step_id=step_id,
                error=str(exc),
            )
            step.status = StepStatus.FAILED
            await db.commit()
            await _release_rate_limit_slot()
            return {"step_id": step_id, "status": "failed", "error": str(exc)}

        except UnipileNonRetryableError as exc:
            # Erro 4xx da Unipile (conta inválida, payload errado) — NÃO retentar
            logger.error(
                "dispatch.permanent_unipile_error",
                step_id=step_id,
                error=str(exc),
            )
            step.status = StepStatus.FAILED
            await db.commit()
            await _release_rate_limit_slot()
            return {"step_id": step_id, "status": "failed", "error": str(exc)}

        except Exception as exc:
            logger.error(
                "dispatch.error",
                step_id=step_id,
                error=str(exc),
            )

            # Incrementa circuit breaker (TTL 30min = 1800s)
            cb_key = f"dispatch:failures:{tenant_id}"
            await redis_client.increment_with_ttl(cb_key, 1800)

            try:
                # Mantém step em DISPATCHING durante retry do Celery
                raise task.retry(exc=RuntimeError(f"{type(exc).__name__}: {exc}"))
            except task.MaxRetriesExceededError:
                # Retries esgotados — reverte para PENDING para re-tentativa futura
                # pelo cadence_tick (em vez de FAILED permanente)
                step.status = StepStatus.PENDING
                await db.commit()
                await _release_rate_limit_slot()
                logger.warning(
                    "dispatch.max_retries_reverted_to_pending",
                    step_id=step_id,
                    error=str(exc),
                )
                return {"step_id": step_id, "status": "pending", "error": str(exc)}
        finally:
            if registry is not None:
                await close_async_resource(registry)

    return {"step_id": step_id, "status": "error", "error": "no_session"}


def _build_email_subject(lead: Lead, step_number: int) -> str:
    """Gera assunto do e-mail baseado na empresa e número do step."""
    company = lead.company or lead.name
    return build_fallback_email_subject(company, step_number)


async def _generate_tts_audio(
    cadence: Cadence,  # type: ignore[name-defined]  # noqa: F821
    text: str,
    settings: Settings,  # type: ignore[name-defined]  # noqa: F821
    redis_client: RedisClient,  # type: ignore[name-defined]  # noqa: F821
) -> str:
    """Gera áudio TTS, armazena no Redis e retorna a URL pública."""
    from integrations.tts import TTSRegistry

    tts_registry = TTSRegistry(settings=settings, redis=redis_client)
    tts_provider = cadence.tts_provider or settings.VOICE_PROVIDER
    tts_voice_id = cadence.tts_voice_id or settings.SPEECHIFY_VOICE_ID
    tts_speed = getattr(cadence, "tts_speed", 1.0) or 1.0
    tts_pitch = getattr(cadence, "tts_pitch", 0.0) or 0.0

    # Fallback: se o provider configurado não estiver disponível, usa edge
    available = list(tts_registry._providers.keys())
    if tts_provider not in available and "edge" in available:
        tts_provider = "edge"
        tts_voice_id = settings.EDGE_TTS_DEFAULT_VOICE

    audio_bytes = await tts_registry.synthesize(
        provider=tts_provider,
        voice_id=tts_voice_id,
        text=text,
        speed=tts_speed,
        pitch=tts_pitch,
    )
    audio_key = str(uuid.uuid4())
    await redis_client.set_bytes(f"audio:{audio_key}", audio_bytes, ttl=3600)
    return f"{settings.API_PUBLIC_URL}/audio/{audio_key}"
