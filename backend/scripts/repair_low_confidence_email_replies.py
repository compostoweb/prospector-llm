from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from core.config import settings
from models.cadence_step import CadenceStep
from models.enums import Channel, InteractionDirection, StepStatus
from models.interaction import Interaction
from services.reply_matching import (
    LOW_CONFIDENCE_EMAIL_REPLY_SOURCE,
    reliable_reply_interaction_condition,
)

logger = structlog.get_logger()


@dataclass
class RepairPlan:
    lead_id: UUID
    cadence_id: UUID
    fallback_interaction_ids: list[UUID]
    step_ids_to_reset: list[UUID]
    step_ids_to_requeue: list[UUID]
    reliable_reply_count: int
    earliest_suspicious_reply_at: datetime | None


async def _build_repair_plan(
    lead_id: UUID,
    cadence_id: UUID,
    tenant_id: UUID | None,
) -> RepairPlan:
    engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with session_factory() as db:
            fallback_stmt = (
                select(Interaction)
                .join(CadenceStep, CadenceStep.id == Interaction.cadence_step_id)
                .where(
                    Interaction.channel == Channel.EMAIL,
                    Interaction.direction == InteractionDirection.INBOUND,
                    Interaction.reply_match_source == LOW_CONFIDENCE_EMAIL_REPLY_SOURCE,
                    Interaction.lead_id == lead_id,
                    Interaction.cadence_step_id.is_not(None),
                    CadenceStep.cadence_id == cadence_id,
                )
            )
            if tenant_id is not None:
                fallback_stmt = fallback_stmt.where(
                    Interaction.tenant_id == tenant_id,
                    CadenceStep.tenant_id == tenant_id,
                )
            fallback_rows = (await db.execute(fallback_stmt)).scalars().all()

            reliable_stmt = (
                select(Interaction.id)
                .join(CadenceStep, CadenceStep.id == Interaction.cadence_step_id)
                .where(
                    Interaction.lead_id == lead_id,
                    CadenceStep.cadence_id == cadence_id,
                    reliable_reply_interaction_condition(),
                )
            )
            if tenant_id is not None:
                reliable_stmt = reliable_stmt.where(
                    Interaction.tenant_id == tenant_id,
                    CadenceStep.tenant_id == tenant_id,
                )
            reliable_reply_ids = [row[0] for row in (await db.execute(reliable_stmt)).all()]

            steps_stmt = select(CadenceStep).where(
                CadenceStep.lead_id == lead_id,
                CadenceStep.cadence_id == cadence_id,
            )
            if tenant_id is not None:
                steps_stmt = steps_stmt.where(CadenceStep.tenant_id == tenant_id)
            steps = (
                (await db.execute(steps_stmt.order_by(CadenceStep.step_number.asc())))
                .scalars()
                .all()
            )

            reliable_step_ids = {
                row[0]
                for row in (
                    await db.execute(
                        select(Interaction.cadence_step_id)
                        .join(CadenceStep, CadenceStep.id == Interaction.cadence_step_id)
                        .where(
                            Interaction.lead_id == lead_id,
                            CadenceStep.cadence_id == cadence_id,
                            reliable_reply_interaction_condition(),
                        )
                    )
                ).all()
                if row[0] is not None
            }

            earliest_suspicious_reply_at = min(
                (interaction.created_at for interaction in fallback_rows),
                default=None,
            )

            step_ids_to_reset = [
                step.id
                for step in steps
                if step.status == StepStatus.REPLIED and step.id not in reliable_step_ids
            ]
            step_ids_to_requeue = [
                step.id
                for step in steps
                if step.status == StepStatus.SKIPPED
                and step.sent_at is None
                and earliest_suspicious_reply_at is not None
                and step.scheduled_at >= earliest_suspicious_reply_at
            ]

            return RepairPlan(
                lead_id=lead_id,
                cadence_id=cadence_id,
                fallback_interaction_ids=[interaction.id for interaction in fallback_rows],
                step_ids_to_reset=step_ids_to_reset,
                step_ids_to_requeue=step_ids_to_requeue,
                reliable_reply_count=len(reliable_reply_ids),
                earliest_suspicious_reply_at=earliest_suspicious_reply_at,
            )
    finally:
        await engine.dispose()


async def _apply_repair(plan: RepairPlan, tenant_id: UUID | None) -> None:
    engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with session_factory() as db:
            if plan.fallback_interaction_ids:
                stmt = select(Interaction).where(Interaction.id.in_(plan.fallback_interaction_ids))
                if tenant_id is not None:
                    stmt = stmt.where(Interaction.tenant_id == tenant_id)
                interactions = (await db.execute(stmt)).scalars().all()
                for interaction in interactions:
                    interaction.cadence_step_id = None
                    interaction.reply_match_status = "unmatched"

            if plan.step_ids_to_reset:
                stmt = select(CadenceStep).where(CadenceStep.id.in_(plan.step_ids_to_reset))
                if tenant_id is not None:
                    stmt = stmt.where(CadenceStep.tenant_id == tenant_id)
                steps = (await db.execute(stmt)).scalars().all()
                for step in steps:
                    step.status = StepStatus.SENT

            if plan.step_ids_to_requeue:
                stmt = select(CadenceStep).where(CadenceStep.id.in_(plan.step_ids_to_requeue))
                if tenant_id is not None:
                    stmt = stmt.where(CadenceStep.tenant_id == tenant_id)
                steps = (await db.execute(stmt)).scalars().all()
                for step in steps:
                    step.status = StepStatus.PENDING

            await db.commit()
    finally:
        await engine.dispose()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Repara replies de email low-confidence associados por fallback_single_cadence.",
    )
    parser.add_argument("--lead-id", required=True, type=UUID)
    parser.add_argument("--cadence-id", required=True, type=UUID)
    parser.add_argument("--tenant-id", type=UUID)
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


def _log_plan(plan: RepairPlan) -> None:
    logger.info(
        "repair_low_confidence_email_replies.plan",
        lead_id=str(plan.lead_id),
        cadence_id=str(plan.cadence_id),
        fallback_interactions=[str(item) for item in plan.fallback_interaction_ids],
        step_ids_to_reset=[str(item) for item in plan.step_ids_to_reset],
        step_ids_to_requeue=[str(item) for item in plan.step_ids_to_requeue],
        reliable_reply_count=plan.reliable_reply_count,
        earliest_suspicious_reply_at=(
            plan.earliest_suspicious_reply_at.isoformat()
            if plan.earliest_suspicious_reply_at is not None
            else None
        ),
    )


async def _main() -> int:
    args = _parse_args()
    plan = await _build_repair_plan(args.lead_id, args.cadence_id, args.tenant_id)
    _log_plan(plan)

    if plan.reliable_reply_count > 0:
        logger.warning(
            "repair_low_confidence_email_replies.skipped_reliable_reply_present",
            lead_id=str(plan.lead_id),
            cadence_id=str(plan.cadence_id),
            reliable_reply_count=plan.reliable_reply_count,
        )
        return 0

    if not args.apply:
        logger.info("repair_low_confidence_email_replies.dry_run_complete")
        return 0

    await _apply_repair(plan, args.tenant_id)
    logger.info("repair_low_confidence_email_replies.applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
