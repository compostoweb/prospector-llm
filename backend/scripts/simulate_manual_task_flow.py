"""
scripts/simulate_manual_task_flow.py

Simulação local do fluxo semi-manual de cadência sem depender de webhook,
LLM ou envio real. O objetivo é validar enrollment, criação das manual tasks
e transições done/skip com dados controlados em dev.

Uso:
    cd backend
    ENV=dev python -m scripts.simulate_manual_task_flow
    ENV=dev python -m scripts.simulate_manual_task_flow --tenant-id <uuid>
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import structlog
from sqlalchemy import select, text

if TYPE_CHECKING:
    from models.tenant import Tenant

logger = structlog.get_logger()


async def _resolve_tenant(session, tenant_id: str | None) -> Tenant | None:
    from models.tenant import Tenant

    if tenant_id:
        result = await session.execute(select(Tenant).where(Tenant.id == uuid.UUID(tenant_id)))
        return result.scalar_one_or_none()

    result = await session.execute(
        select(Tenant).where(Tenant.is_active.is_(True)).order_by(Tenant.created_at.asc()).limit(1)
    )
    return result.scalar_one_or_none()


async def simulate_manual_task_flow(tenant_id: uuid.UUID) -> None:
    from core.database import AsyncSessionLocal
    from models.cadence import Cadence
    from models.cadence_step import CadenceStep
    from models.enums import CadenceMode, LeadSource, LeadStatus, ManualTaskStatus, StepStatus
    from models.lead import Lead
    from models.manual_task import ManualTask
    from services.cadence_manager import CadenceManager
    from services.manual_task_service import ManualTaskService

    async with AsyncSessionLocal() as session:
        tid = str(tenant_id)
        await session.execute(text(f"SET LOCAL app.current_tenant_id = '{tid}'"))

        lead = Lead(
            tenant_id=tenant_id,
            name="Lead Simulação Semi-manual",
            first_name="Lead",
            last_name="Simulado",
            company="Acme Simulada",
            linkedin_url=f"https://linkedin.com/in/manual-sim-{uuid.uuid4()}",
            linkedin_profile_id=f"manual-sim-{uuid.uuid4().hex[:12]}",
            email_corporate="lead.simulado@acme.test",
            source=LeadSource.MANUAL,
            status=LeadStatus.RAW,
        )
        session.add(lead)

        cadence = Cadence(
            tenant_id=tenant_id,
            name=f"Cadência Semi-manual Simulada {uuid.uuid4().hex[:6]}",
            description="Criada por script para revisar integração com tarefas manuais.",
            is_active=True,
            mode=CadenceMode.SEMI_MANUAL.value,
            llm_provider="openai",
            llm_model="gpt-5.4-mini",
            steps_template=[
                {"step_number": 1, "channel": "linkedin_connect", "day_offset": 0},
                {
                    "step_number": 2,
                    "channel": "linkedin_dm",
                    "day_offset": 1,
                    "manual_task_type": "linkedin_post_comment",
                    "manual_task_detail": "Comentar no post mais recente antes de retomar a conversa.",
                },
                {
                    "step_number": 3,
                    "channel": "email",
                    "day_offset": 3,
                    "manual_task_type": "whatsapp",
                    "manual_task_detail": "Se houver contexto, confirmar o melhor canal para continuar.",
                },
            ],
        )
        session.add(cadence)
        await session.flush()

        cadence_manager = CadenceManager()
        task_service = ManualTaskService()

        steps = await cadence_manager.enroll(lead, cadence, session)
        await session.flush()

        lead.linkedin_connection_status = "connected"
        lead.linkedin_connected_at = datetime.now(tz=UTC)
        tasks = await task_service.create_tasks_for_lead(lead, cadence, session)
        await session.flush()

        connect_step_result = await session.execute(
            select(CadenceStep).where(
                CadenceStep.tenant_id == tenant_id,
                CadenceStep.cadence_id == cadence.id,
                CadenceStep.lead_id == lead.id,
                CadenceStep.step_number == 1,
            )
        )
        connect_step = connect_step_result.scalar_one_or_none()
        if connect_step is not None:
            connect_step.status = StepStatus.SKIPPED

        if tasks:
            tasks[0].generated_text = "Mensagem simulada para revisão manual."
            tasks[0].edited_text = "Mensagem final revisada pelo operador na simulação."
            tasks[0].status = ManualTaskStatus.CONTENT_GENERATED

        if len(tasks) > 1:
            await task_service.mark_done_external(
                tasks[1].id,
                tenant_id=tenant_id,
                notes="Executado fora do sistema durante a simulação.",
                db=session,
            )

        if len(tasks) > 2:
            await task_service.skip(tasks[2].id, tenant_id=tenant_id, db=session)

        await session.commit()

        persisted_tasks_result = await session.execute(
            select(ManualTask)
            .where(ManualTask.tenant_id == tenant_id, ManualTask.cadence_id == cadence.id)
            .order_by(ManualTask.step_number.asc())
        )
        persisted_tasks = list(persisted_tasks_result.scalars().all())

        logger.info(
            "simulate_manual_task_flow.summary",
            tenant_id=str(tenant_id),
            cadence_id=str(cadence.id),
            lead_id=str(lead.id),
            cadence_steps_created=len(steps),
            manual_tasks_created=len(tasks),
        )

        print("\n=== Simulação semi-manual ===")
        print(f"Tenant:   {tenant_id}")
        print(
            f"Lead:     {lead.id} | status={lead.status.value} | connection={lead.linkedin_connection_status}"
        )
        print(f"Cadência: {cadence.id} | mode={cadence.mode}")
        print(f"Steps automáticos criados: {len(steps)}")
        for step in steps:
            print(
                f"  - step #{step.step_number} | channel={step.channel.value} | status={step.status.value}"
            )

        print(f"Manual tasks criadas: {len(persisted_tasks)}")
        for task in persisted_tasks:
            preview = task.edited_text or task.generated_text or task.notes or "(sem conteúdo)"
            print(
                f"  - task #{task.step_number} | channel={task.channel.value} | status={task.status.value} | preview={preview}"
            )

        print("\nPróximos passos sugeridos:")
        print(f"1. Abrir /tarefas e filtrar pela cadência {cadence.id}")
        print(f"2. Conferir o histórico do lead {lead.id} em /leads/{lead.id}")
        print(
            "3. Se quiser validar generate/send real, usar uma task pendente criada nesta simulação como base"
        )


async def main() -> None:
    parser = argparse.ArgumentParser(description="Simula o fluxo semi-manual de cadência.")
    parser.add_argument("--tenant-id", dest="tenant_id", default=None, help="UUID do tenant alvo")
    args = parser.parse_args()

    from core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        tenant = await _resolve_tenant(session, args.tenant_id)

    if tenant is None:
        logger.error(
            "simulate_manual_task_flow.no_tenant",
            detail="Nenhum tenant ativo encontrado para a simulação.",
        )
        sys.exit(1)

    await simulate_manual_task_flow(tenant.id)


if __name__ == "__main__":
    asyncio.run(main())
