"""
services/cadence_manager.py

Gerencia o enrollment de leads em cadências e a progressão dos steps.

Responsabilidades:
  - enroll(lead, cadence, db):
      Cria os CadenceSteps de acordo com o template da cadência
      Calcula scheduled_at = now() + timedelta(days=day_offset)
      Atualiza lead.status = IN_CADENCE
  - get_due_steps(db, tenant_id):
      Retorna steps com scheduled_at <= now() e status = PENDING
      (usado pelo cadence_worker.tick para despachar)
  - mark_sent / mark_skipped / mark_failed:
      Atualizam o status do step após a tentativa de envio

Template de steps (configuração estática por cadência):
  Step 1: linkedin_connect    day_offset=0
  Step 2: linkedin_dm         day_offset=3   (after connect accepted)
  Step 3: email               day_offset=5
  Step 4: linkedin_dm         day_offset=10  (follow-up — com voz se use_voice=True)
  Step 5: email               day_offset=14  (follow-up final)

O template é expandido dinamicamente com base nos canais disponíveis para o lead.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.cadence import Cadence
from models.cadence_step import CadenceStep
from models.enums import Channel, LeadStatus, StepStatus
from models.lead import Lead

logger = structlog.get_logger()

# Template padrão de cadência multi-canal
# Cada entry: (channel, day_offset, use_voice)
_DEFAULT_TEMPLATE: list[tuple[Channel, int, bool]] = [
    (Channel.LINKEDIN_CONNECT, 0,  False),
    (Channel.LINKEDIN_DM,      3,  False),
    (Channel.EMAIL,            5,  False),
    (Channel.LINKEDIN_DM,      10, True),   # follow-up com voz
    (Channel.EMAIL,            14, False),  # follow-up final
]


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


class CadenceManager:
    """
    Orquestra o enrollment e a gestão de steps de cadência.
    """

    async def enroll(
        self,
        lead: Lead,
        cadence: Cadence,
        db: AsyncSession,
    ) -> list[CadenceStep]:
        """
        Inscreve o lead na cadência criando os CadenceSteps necessários.

        - Filtra steps pelo que o lead possui (ex: sem LinkedIn → skip connect/dm)
        - Filtra e-mail se lead não tem e-mail corporativo e cadência não permite pessoal
        - Atualiza lead.status = IN_CADENCE
        - Retorna os steps criados

        Lança ValueError se o lead não tiver nenhum canal disponível.
        """
        # Idempotência: verifica se lead já tem steps PENDING nesta cadência
        existing = await db.execute(
            select(CadenceStep.id)
            .where(
                CadenceStep.lead_id == lead.id,
                CadenceStep.cadence_id == cadence.id,
                CadenceStep.status == StepStatus.PENDING,
            )
            .limit(1)
        )
        if existing.scalar_one_or_none() is not None:
            logger.warning(
                "cadence_manager.already_enrolled",
                lead_id=str(lead.id),
                cadence_id=str(cadence.id),
            )
            return []

        now = _utcnow()
        steps: list[CadenceStep] = []

        # Usa template customizado da cadência ou o padrão
        template = _resolve_template(cadence)

        for step_number, (channel, day_offset, use_voice) in enumerate(
            template, start=1
        ):
            # Verifica se o lead tem os dados para o canal
            if not _lead_has_channel(lead, channel, cadence):
                logger.debug(
                    "cadence_manager.step_skipped_no_channel",
                    lead_id=str(lead.id),
                    channel=channel.value,
                )
                continue

            scheduled_at = now + timedelta(days=day_offset)

            step = CadenceStep(
                id=uuid.uuid4(),
                tenant_id=lead.tenant_id,
                cadence_id=cadence.id,
                lead_id=lead.id,
                channel=channel,
                step_number=step_number,
                day_offset=day_offset,
                use_voice=use_voice,
                status=StepStatus.PENDING,
                scheduled_at=scheduled_at,
            )
            db.add(step)
            steps.append(step)

        if not steps:
            raise ValueError(
                f"Lead {lead.id} não possui nenhum canal disponível para cadência {cadence.id}"
            )

        lead.status = LeadStatus.IN_CADENCE

        await db.flush()  # persiste IDs sem fechar a transação

        logger.info(
            "cadence_manager.enrolled",
            lead_id=str(lead.id),
            cadence_id=str(cadence.id),
            steps_created=len(steps),
        )
        return steps

    async def get_due_steps(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        limit: int = 100,
    ) -> list[CadenceStep]:
        """
        Retorna steps pendentes cujo scheduled_at já passou.
        Ordenado por scheduled_at ASC (mais antigos primeiro).
        """
        now = _utcnow()
        result = await db.execute(
            select(CadenceStep)
            .where(
                CadenceStep.tenant_id == tenant_id,
                CadenceStep.status == StepStatus.PENDING,
                CadenceStep.scheduled_at <= now,
            )
            .order_by(CadenceStep.scheduled_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def mark_sent(
        self,
        step: CadenceStep,
        db: AsyncSession,
    ) -> None:
        step.status = StepStatus.SENT
        step.sent_at = _utcnow()
        await db.flush()
        logger.info("cadence_manager.step_sent", step_id=str(step.id))

    async def mark_skipped(
        self,
        step: CadenceStep,
        db: AsyncSession,
    ) -> None:
        step.status = StepStatus.SKIPPED
        await db.flush()
        logger.info("cadence_manager.step_skipped", step_id=str(step.id))

    async def mark_failed(
        self,
        step: CadenceStep,
        db: AsyncSession,
        reason: str = "",
    ) -> None:
        step.status = StepStatus.FAILED
        await db.flush()
        logger.warning(
            "cadence_manager.step_failed",
            step_id=str(step.id),
            reason=reason,
        )


# ── Helpers ───────────────────────────────────────────────────────────

def _resolve_template(cadence: Cadence) -> list[tuple[Channel, int, bool]]:
    """Retorna o template de steps: customizado (JSONB) ou o padrão."""
    if not cadence.steps_template:
        return _DEFAULT_TEMPLATE
    return [
        (Channel(item["channel"]), item["day_offset"], item.get("use_voice", False))
        for item in cadence.steps_template
    ]


def _lead_has_channel(lead: Lead, channel: Channel, cadence: Cadence) -> bool:
    """Verifica se o lead tem os dados necessários para o canal."""
    if channel == Channel.LINKEDIN_CONNECT:
        return bool(lead.linkedin_url)

    if channel == Channel.LINKEDIN_DM:
        return bool(lead.linkedin_url)

    if channel == Channel.EMAIL:
        if lead.email_corporate:
            return True
        if lead.email_personal and cadence.allow_personal_email:
            return True
        return False

    return False


# Singleton
cadence_manager = CadenceManager()
