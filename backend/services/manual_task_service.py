"""
services/manual_task_service.py

Lógica de negócio para tarefas manuais da cadência semi-automática.

Responsabilidades:
  - Criar tasks quando aceitam conexão LinkedIn
  - Gerar conteúdo LLM (texto + TTS) para cada task
  - Enviar via Unipile ou marcar como feita externamente
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from integrations.llm import LLMRegistry
from models.cadence import Cadence
from models.enums import Channel, InteractionDirection, ManualTaskStatus
from models.interaction import Interaction
from models.lead import Lead
from models.manual_task import ManualTask
from models.tenant import TenantIntegration
from services.ai_composer import AIComposer
from services.email_account_service import resolve_outbound_email_account
from services.email_footer import inject_tracking

logger = structlog.get_logger()

# Channels pós-connect que geram tasks manuais
_POST_CONNECT_CHANNELS = {
    Channel.LINKEDIN_DM,
    Channel.EMAIL,
}


class ManualTaskService:
    """Gerenciador de tarefas manuais para cadência semi-automática."""

    async def create_tasks_for_lead(
        self,
        lead: Lead,
        cadence: Cadence,
        db: AsyncSession,
    ) -> list[ManualTask]:
        """
        Cria ManualTasks a partir do template da cadência.
        Apenas steps pós-connect (DM, email) viram tasks manuais.
        """
        template = cadence.steps_template or _default_post_connect_template()
        tasks: list[ManualTask] = []

        existing_result = await db.execute(
            select(ManualTask).where(
                ManualTask.tenant_id == lead.tenant_id,
                ManualTask.cadence_id == cadence.id,
                ManualTask.lead_id == lead.id,
            )
        )
        existing_keys = {
            (task.channel, task.step_number) for task in existing_result.scalars().all()
        }

        for default_step_number, item in enumerate(template, start=1):
            channel_str = item.get("channel", "")
            try:
                channel = Channel(channel_str)
            except ValueError:
                continue

            step_number = int(item.get("step_number") or default_step_number)

            # Pula o connect (já foi automático)
            if channel == Channel.LINKEDIN_CONNECT:
                continue

            if channel not in _POST_CONNECT_CHANNELS:
                continue

            if (channel, step_number) in existing_keys:
                continue

            task = ManualTask(
                id=uuid.uuid4(),
                tenant_id=lead.tenant_id,
                cadence_id=cadence.id,
                lead_id=lead.id,
                channel=channel,
                step_number=step_number,
                status=ManualTaskStatus.PENDING,
            )
            db.add(task)
            tasks.append(task)
            existing_keys.add((channel, step_number))

        logger.info(
            "manual_task.created",
            lead_id=str(lead.id),
            cadence_id=str(cadence.id),
            count=len(tasks),
        )
        return tasks

    async def generate_content(
        self,
        task_id: uuid.UUID,
        tenant_id: uuid.UUID,
        db: AsyncSession,
        registry: LLMRegistry,
    ) -> ManualTask:
        """Gera conteúdo LLM para a tarefa."""
        task = await self._get_task(task_id, db, tenant_id=tenant_id)
        lead = task.lead
        cadence = task.cadence

        # Busca contexto do site
        from integrations.context_fetcher import context_fetcher

        context: dict[str, str] = {}
        if lead.website:
            context["website"] = await context_fetcher.fetch_from_website(lead.website)
        elif lead.company:
            context["company_info"] = await context_fetcher.search_company(
                lead.company,
                lead.website,
            )

        composer = AIComposer(registry)
        text = await composer.compose(
            lead=lead,
            channel=task.channel.value,
            step_number=task.step_number,
            context=context,
            cadence=cadence,
        )

        task.generated_text = text
        task.status = ManualTaskStatus.CONTENT_GENERATED

        # Gera áudio TTS se channel é linkedin_dm (voz opcional)
        audio_url = await self._maybe_generate_tts(task, cadence, text)
        if audio_url:
            task.generated_audio_url = audio_url

        await db.commit()
        await db.refresh(task)

        logger.info(
            "manual_task.content_generated",
            task_id=str(task.id),
            channel=task.channel.value,
        )
        return task

    async def update_content(
        self,
        task_id: uuid.UUID,
        tenant_id: uuid.UUID,
        edited_text: str,
        db: AsyncSession,
    ) -> ManualTask:
        """Salva texto editado pelo operador."""
        task = await self._get_task(task_id, db, tenant_id=tenant_id)
        task.edited_text = edited_text
        await db.commit()
        await db.refresh(task)
        return task

    async def send_via_system(
        self,
        task_id: uuid.UUID,
        tenant_id: uuid.UUID,
        db: AsyncSession,
    ) -> ManualTask:
        """Envia a mensagem via Unipile e registra Interaction outbound."""
        from core.config import settings
        from integrations.email import EmailRegistry
        from integrations.linkedin import LinkedInRegistry
        from integrations.unipile_client import unipile_client
        from models.email_account import EmailAccount
        from models.linkedin_account import LinkedInAccount

        task = await self._get_task(task_id, db, tenant_id=tenant_id)
        lead = task.lead
        cadence = task.cadence
        text = task.edited_text or task.generated_text or ""

        if not text:
            raise ValueError("Tarefa não tem conteúdo para enviar")

        result: Any = None
        integration_result = await db.execute(
            select(TenantIntegration).where(TenantIntegration.tenant_id == tenant_id)
        )
        integration = integration_result.scalar_one_or_none()

        if task.channel == Channel.LINKEDIN_DM:
            if not lead.linkedin_profile_id:
                raise ValueError("Lead sem linkedin_profile_id")

            if cadence.linkedin_account_id:
                account_result = await db.execute(
                    select(LinkedInAccount).where(
                        LinkedInAccount.id == cadence.linkedin_account_id,
                        LinkedInAccount.tenant_id == tenant_id,
                    )
                )
                linkedin_account = account_result.scalar_one_or_none()
                if linkedin_account is None:
                    raise ValueError("Conta LinkedIn da cadência não encontrada")

                registry = LinkedInRegistry(settings=settings)
                if task.generated_audio_url:
                    result = await registry.send_voice_note(
                        account=linkedin_account,
                        linkedin_profile_id=lead.linkedin_profile_id,
                        audio_url=task.generated_audio_url,
                    )
                else:
                    result = await registry.send_dm(
                        account=linkedin_account,
                        linkedin_profile_id=lead.linkedin_profile_id,
                        message=text,
                    )
            else:
                account_id = (
                    (integration and integration.unipile_linkedin_account_id)
                    or settings.UNIPILE_ACCOUNT_ID_LINKEDIN
                    or ""
                )
                if not account_id:
                    raise ValueError("Conta LinkedIn não configurada")

                if task.generated_audio_url:
                    result = await unipile_client.send_linkedin_voice_note(
                        account_id=account_id,
                        linkedin_profile_id=lead.linkedin_profile_id,
                        audio_url=task.generated_audio_url,
                    )
                else:
                    result = await unipile_client.send_linkedin_dm(
                        account_id=account_id,
                        linkedin_profile_id=lead.linkedin_profile_id,
                        message=text,
                    )

        elif task.channel == Channel.EMAIL:
            email = lead.email_corporate or lead.email_personal
            if not email:
                raise ValueError("Lead sem email para envio")

            subject = f"Re: {lead.company or lead.name}"

            if cadence.email_account_id:
                account_result = await db.execute(
                    select(EmailAccount).where(
                        EmailAccount.id == cadence.email_account_id,
                        EmailAccount.tenant_id == tenant_id,
                    )
                )
                email_account: Any = account_result.scalar_one_or_none()
                if email_account is None:
                    raise ValueError("Conta de e-mail da cadência não encontrada")

                email_send_account = await resolve_outbound_email_account(db, email_account)

                email_registry = EmailRegistry(settings=settings)
                body_html = inject_tracking(
                    body_html=text,
                    interaction_id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    email=email,
                    signature_html=email_send_account.email_signature,
                )
                result = await email_registry.send(
                    account=email_send_account,
                    to_email=email,
                    subject=subject,
                    body_html=body_html,
                    from_name=email_send_account.from_name or email_send_account.display_name,
                )
            else:
                account_id = (
                    (integration and integration.unipile_gmail_account_id)
                    or settings.UNIPILE_ACCOUNT_ID_GMAIL
                    or ""
                )
                if not account_id:
                    raise ValueError("Conta de e-mail não configurada")

                result = await unipile_client.send_email(
                    account_id=account_id,
                    to_email=email,
                    subject=subject,
                    body_html=text,
                )

        if result is None or not result.success:
            raise ValueError("Falha ao enviar tarefa via sistema")

        # Registra Interaction outbound
        interaction = Interaction(
            id=uuid.uuid4(),
            tenant_id=lead.tenant_id,
            lead_id=lead.id,
            channel=task.channel,
            direction=InteractionDirection.OUTBOUND,
            content_text=text,
            content_audio_url=task.generated_audio_url,
            unipile_message_id=result.message_id if result else None,
            created_at=datetime.now(tz=UTC),
        )
        db.add(interaction)

        task.status = ManualTaskStatus.SENT
        task.sent_at = datetime.now(tz=UTC)
        task.unipile_message_id = result.message_id if result else None

        await db.commit()
        await db.refresh(task)

        logger.info(
            "manual_task.sent",
            task_id=str(task.id),
            channel=task.channel.value,
            message_id=result.message_id if result else None,
        )
        return task

    async def mark_done_external(
        self,
        task_id: uuid.UUID,
        tenant_id: uuid.UUID,
        notes: str | None,
        db: AsyncSession,
    ) -> ManualTask:
        """Marca a tarefa como executada externamente."""
        task = await self._get_task(task_id, db, tenant_id=tenant_id)
        task.status = ManualTaskStatus.DONE_EXTERNAL
        task.sent_at = datetime.now(tz=UTC)
        if notes:
            task.notes = notes
        await db.commit()
        await db.refresh(task)

        logger.info("manual_task.done_external", task_id=str(task.id))
        return task

    async def skip(
        self,
        task_id: uuid.UUID,
        tenant_id: uuid.UUID,
        db: AsyncSession,
    ) -> ManualTask:
        """Pula a tarefa."""
        task = await self._get_task(task_id, db, tenant_id=tenant_id)
        task.status = ManualTaskStatus.SKIPPED
        await db.commit()
        await db.refresh(task)

        logger.info("manual_task.skipped", task_id=str(task.id))
        return task

    async def regenerate_content(
        self,
        task_id: uuid.UUID,
        tenant_id: uuid.UUID,
        db: AsyncSession,
        registry: LLMRegistry,
    ) -> ManualTask:
        """Regera conteúdo LLM (nova chamada ao composer)."""
        task = await self._get_task(task_id, db, tenant_id=tenant_id)
        task.generated_text = None
        task.generated_audio_url = None
        task.edited_text = None
        task.status = ManualTaskStatus.PENDING
        await db.commit()
        return await self.generate_content(task_id, tenant_id, db, registry)

    async def list_tasks(
        self,
        tenant_id: uuid.UUID,
        db: AsyncSession,
        cadence_id: uuid.UUID | None = None,
        status: ManualTaskStatus | None = None,
        channel: Channel | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """Lista tarefas com filtros e paginação."""
        query = select(ManualTask).where(ManualTask.tenant_id == tenant_id)

        if cadence_id:
            query = query.where(ManualTask.cadence_id == cadence_id)
        if status:
            query = query.where(ManualTask.status == status)
        if channel:
            query = query.where(ManualTask.channel == channel)

        # Contagem total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Paginação
        query = query.order_by(ManualTask.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        tasks = list(result.scalars().all())

        return {
            "items": tasks,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def get_stats(
        self,
        tenant_id: uuid.UUID,
        db: AsyncSession,
    ) -> dict:
        """Estatísticas de tarefas."""
        base = select(func.count()).where(ManualTask.tenant_id == tenant_id)

        pending = await db.execute(base.where(ManualTask.status == ManualTaskStatus.PENDING))
        generated = await db.execute(
            base.where(ManualTask.status == ManualTaskStatus.CONTENT_GENERATED)
        )
        sent = await db.execute(base.where(ManualTask.status == ManualTaskStatus.SENT))
        done_ext = await db.execute(base.where(ManualTask.status == ManualTaskStatus.DONE_EXTERNAL))

        return {
            "pending": pending.scalar() or 0,
            "content_generated": generated.scalar() or 0,
            "sent": sent.scalar() or 0,
            "done_external": done_ext.scalar() or 0,
        }

    # ── Private helpers ───────────────────────────────────────────────

    async def _get_task(
        self,
        task_id: uuid.UUID,
        db: AsyncSession,
        tenant_id: uuid.UUID | None = None,
    ) -> ManualTask:
        query = (
            select(ManualTask)
            .where(ManualTask.id == task_id)
            .options(
                selectinload(ManualTask.lead),
                selectinload(ManualTask.cadence),
            )
        )
        if tenant_id is not None:
            query = query.where(ManualTask.tenant_id == tenant_id)

        result = await db.execute(query)
        task = result.scalar_one_or_none()
        if not task:
            raise ValueError(f"Tarefa {task_id} não encontrada")
        return task

    async def _maybe_generate_tts(
        self,
        task: ManualTask,
        cadence: Cadence,
        text: str,
    ) -> str | None:
        """Gera áudio TTS se o channel suporta voz."""
        if task.channel != Channel.LINKEDIN_DM:
            return None

        try:
            from core.config import settings
            from core.redis_client import redis_client
            from integrations.tts import TTSRegistry

            tts_registry = TTSRegistry(settings=settings, redis=redis_client)
            provider_name = cadence.tts_provider or settings.VOICE_PROVIDER
            voice_id = (
                cadence.tts_voice_id
                or settings.SPEECHIFY_VOICE_ID
                or settings.EDGE_TTS_DEFAULT_VOICE
            )
            available = tts_registry.available_providers()
            if not available:
                return None

            if provider_name not in available and "edge" in available:
                provider_name = "edge"
                voice_id = settings.EDGE_TTS_DEFAULT_VOICE

            audio_bytes = await tts_registry.synthesize(
                provider=provider_name,
                voice_id=voice_id,
                text=text,
                speed=cadence.tts_speed,
                pitch=cadence.tts_pitch,
            )

            audio_key = str(uuid.uuid4())
            await redis_client.set_bytes(f"audio:{audio_key}", audio_bytes, ttl=3600)
            return f"{settings.API_PUBLIC_URL}/audio/{audio_key}"

        except Exception:
            logger.warning(
                "manual_task.tts_failed",
                task_id=str(task.id),
            )
            return None


def _default_post_connect_template() -> list[dict]:
    """Template padrão de steps pós-connect para cadência semi-manual."""
    return [
        {"channel": "linkedin_dm", "step_number": 1, "use_voice": False},
        {"channel": "linkedin_dm", "step_number": 2, "use_voice": True},
        {"channel": "email", "step_number": 3, "use_voice": False},
        {"channel": "linkedin_dm", "step_number": 4, "use_voice": False},
    ]
