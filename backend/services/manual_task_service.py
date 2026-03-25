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
from datetime import datetime, timezone

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from integrations.llm import LLMRegistry
from models.cadence import Cadence
from models.enums import Channel, InteractionDirection, ManualTaskStatus
from models.interaction import Interaction
from models.lead import Lead
from models.manual_task import ManualTask
from services.ai_composer import AIComposer

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

        for item in template:
            channel_str = item.get("channel", "")
            try:
                channel = Channel(channel_str)
            except ValueError:
                continue

            # Pula o connect (já foi automático)
            if channel == Channel.LINKEDIN_CONNECT:
                continue

            if channel not in _POST_CONNECT_CHANNELS:
                continue

            task = ManualTask(
                id=uuid.uuid4(),
                tenant_id=lead.tenant_id,
                cadence_id=cadence.id,
                lead_id=lead.id,
                channel=channel,
                step_number=item.get("step_number", 1),
                status=ManualTaskStatus.PENDING,
            )
            db.add(task)
            tasks.append(task)

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
        db: AsyncSession,
        registry: LLMRegistry,
    ) -> ManualTask:
        """Gera conteúdo LLM para a tarefa."""
        task = await self._get_task(task_id, db)
        lead = task.lead
        cadence = task.cadence

        # Busca contexto do site
        from integrations.context_fetcher import context_fetcher
        context = await context_fetcher.fetch(lead.company_domain) if lead.company_domain else {}

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
        edited_text: str,
        db: AsyncSession,
    ) -> ManualTask:
        """Salva texto editado pelo operador."""
        task = await self._get_task(task_id, db)
        task.edited_text = edited_text
        await db.commit()
        await db.refresh(task)
        return task

    async def send_via_system(
        self,
        task_id: uuid.UUID,
        db: AsyncSession,
    ) -> ManualTask:
        """Envia a mensagem via Unipile e registra Interaction outbound."""
        from core.config import settings
        from integrations.unipile_client import unipile_client

        task = await self._get_task(task_id, db)
        lead = task.lead
        text = task.edited_text or task.generated_text or ""

        if not text:
            raise ValueError("Tarefa não tem conteúdo para enviar")

        account_id = ""
        result = None

        if task.channel == Channel.LINKEDIN_DM:
            account_id = settings.UNIPILE_ACCOUNT_ID_LINKEDIN or ""
            if not lead.linkedin_profile_id:
                raise ValueError("Lead sem linkedin_profile_id")

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
            account_id = settings.UNIPILE_ACCOUNT_ID_GMAIL or ""
            email = lead.email_corporate or lead.email_personal
            if not email:
                raise ValueError("Lead sem email para envio")

            result = await unipile_client.send_email(
                account_id=account_id,
                to_email=email,
                subject=f"Re: {lead.company or lead.name}",
                body_html=text,
            )

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
            created_at=datetime.now(tz=timezone.utc),
        )
        db.add(interaction)

        task.status = ManualTaskStatus.SENT
        task.sent_at = datetime.now(tz=timezone.utc)
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
        notes: str | None,
        db: AsyncSession,
    ) -> ManualTask:
        """Marca a tarefa como executada externamente."""
        task = await self._get_task(task_id, db)
        task.status = ManualTaskStatus.DONE_EXTERNAL
        task.sent_at = datetime.now(tz=timezone.utc)
        if notes:
            task.notes = notes
        await db.commit()
        await db.refresh(task)

        logger.info("manual_task.done_external", task_id=str(task.id))
        return task

    async def skip(
        self,
        task_id: uuid.UUID,
        db: AsyncSession,
    ) -> ManualTask:
        """Pula a tarefa."""
        task = await self._get_task(task_id, db)
        task.status = ManualTaskStatus.SKIPPED
        await db.commit()
        await db.refresh(task)

        logger.info("manual_task.skipped", task_id=str(task.id))
        return task

    async def regenerate_content(
        self,
        task_id: uuid.UUID,
        db: AsyncSession,
        registry: LLMRegistry,
    ) -> ManualTask:
        """Regera conteúdo LLM (nova chamada ao composer)."""
        task = await self._get_task(task_id, db)
        task.generated_text = None
        task.generated_audio_url = None
        task.edited_text = None
        task.status = ManualTaskStatus.PENDING
        await db.commit()
        return await self.generate_content(task_id, db, registry)

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

        pending = await db.execute(
            base.where(ManualTask.status == ManualTaskStatus.PENDING)
        )
        generated = await db.execute(
            base.where(ManualTask.status == ManualTaskStatus.CONTENT_GENERATED)
        )
        sent = await db.execute(
            base.where(ManualTask.status == ManualTaskStatus.SENT)
        )
        done_ext = await db.execute(
            base.where(ManualTask.status == ManualTaskStatus.DONE_EXTERNAL)
        )

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
    ) -> ManualTask:
        result = await db.execute(
            select(ManualTask).where(ManualTask.id == task_id)
        )
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
            from integrations.tts import TTSRegistry

            tts_registry = TTSRegistry()
            provider_name = cadence.tts_provider or "edge"
            provider = tts_registry.get(provider_name)
            if not provider:
                return None

            audio_bytes = await provider.synthesize(
                text=text,
                voice_id=cadence.tts_voice_id,
                speed=cadence.tts_speed,
                pitch=cadence.tts_pitch,
            )

            # Armazena no Redis temporariamente (1h)
            from core.redis_client import redis_client
            audio_key = f"tts:manual_task:{task.id}"
            await redis_client.set(audio_key, audio_bytes, ex=3600)

            return f"/api/audio/temp/{audio_key}"

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
