"""
api/routes/analytics.py

Rotas de analytics para o dashboard.

Endpoints:
  GET /analytics/dashboard       — estatísticas gerais
  GET /analytics/channels        — breakdown por canal
  GET /analytics/recent-replies  — respostas recentes
  GET /analytics/intents         — breakdown por intent de respostas
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_effective_tenant_id, get_session_flexible
from models.cadence_step import CadenceStep
from models.enums import InteractionDirection, LeadStatus, StepStatus
from models.interaction import Interaction
from models.lead import Lead

logger = structlog.get_logger()

router = APIRouter(prefix="/analytics", tags=["Analytics"])


# ── Schemas ───────────────────────────────────────────────────────────


class DashboardStatsResponse(BaseModel):
    leads_total: int = 0
    leads_in_cadence: int = 0
    leads_converted: int = 0
    steps_sent_today: int = 0
    steps_sent_week: int = 0
    replies_today: int = 0
    replies_week: int = 0
    conversion_rate: float = 0.0


class ChannelBreakdownItem(BaseModel):
    channel: str
    steps_sent: int = 0
    replies: int = 0
    reply_rate: float = 0.0


class RecentReplyItem(BaseModel):
    lead_id: str
    lead_name: str
    company_name: str | None = None
    intent: str
    replied_at: str
    channel: str


class IntentBreakdownItem(BaseModel):
    intent: str
    count: int = 0
    percentage: float = 0.0


# ── Helpers ───────────────────────────────────────────────────────────


def _utc_start_of_today() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _utc_days_ago(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


# ── Endpoints ─────────────────────────────────────────────────────────


@router.get("/dashboard", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_session_flexible),
    tenant_id: UUID = Depends(get_effective_tenant_id),
) -> DashboardStatsResponse:
    """Retorna estatísticas gerais do dashboard."""
    today_start = _utc_start_of_today()
    week_ago = _utc_days_ago(7)

    # Lead counts via conditional aggregation (single query)
    lead_q = await db.execute(
        select(
            func.count(Lead.id).label("total"),
            func.count(Lead.id).filter(Lead.status == LeadStatus.IN_CADENCE).label("in_cadence"),
            func.count(Lead.id).filter(Lead.status == LeadStatus.CONVERTED).label("converted"),
        ).where(Lead.tenant_id == tenant_id)
    )
    lead_row = lead_q.one()
    leads_total = lead_row.total or 0
    leads_in_cadence = lead_row.in_cadence or 0
    leads_converted = lead_row.converted or 0

    # Steps sent counts (today + week)
    step_q = await db.execute(
        select(
            func.count(CadenceStep.id).filter(CadenceStep.sent_at >= today_start).label("today"),
            func.count(CadenceStep.id).filter(CadenceStep.sent_at >= week_ago).label("week"),
        ).where(
            CadenceStep.tenant_id == tenant_id,
            CadenceStep.status.in_([StepStatus.SENT, StepStatus.REPLIED]),
        )
    )
    step_row = step_q.one()
    steps_sent_today = step_row.today or 0
    steps_sent_week = step_row.week or 0

    # Replies (inbound interactions) counts (today + week)
    reply_q = await db.execute(
        select(
            func.count(Interaction.id).filter(Interaction.created_at >= today_start).label("today"),
            func.count(Interaction.id).filter(Interaction.created_at >= week_ago).label("week"),
        ).where(
            Interaction.tenant_id == tenant_id,
            Interaction.direction == InteractionDirection.INBOUND,
        )
    )
    reply_row = reply_q.one()
    replies_today = reply_row.today or 0
    replies_week = reply_row.week or 0

    conversion_rate = round((leads_converted / leads_total) * 100, 1) if leads_total > 0 else 0.0

    logger.debug("analytics.dashboard", tenant_id=str(tenant_id))
    return DashboardStatsResponse(
        leads_total=leads_total,
        leads_in_cadence=leads_in_cadence,
        leads_converted=leads_converted,
        steps_sent_today=steps_sent_today,
        steps_sent_week=steps_sent_week,
        replies_today=replies_today,
        replies_week=replies_week,
        conversion_rate=conversion_rate,
    )


@router.get("/channels", response_model=list[ChannelBreakdownItem])
async def get_channel_breakdown(
    days: Annotated[int, Query(ge=1, le=365)] = 30,
    db: AsyncSession = Depends(get_session_flexible),
    tenant_id: UUID = Depends(get_effective_tenant_id),
) -> list[ChannelBreakdownItem]:
    """Retorna breakdown de atividade por canal."""
    since = _utc_days_ago(days)

    # Steps sent per channel
    sent_q = await db.execute(
        select(
            CadenceStep.channel,
            func.count(CadenceStep.id).label("sent"),
        )
        .where(
            CadenceStep.tenant_id == tenant_id,
            CadenceStep.status.in_([StepStatus.SENT, StepStatus.REPLIED]),
            CadenceStep.sent_at >= since,
        )
        .group_by(CadenceStep.channel)
    )
    sent_by_channel = {row.channel: row.sent for row in sent_q.all()}

    # Replies (inbound) per channel
    reply_q = await db.execute(
        select(
            Interaction.channel,
            func.count(Interaction.id).label("replies"),
        )
        .where(
            Interaction.tenant_id == tenant_id,
            Interaction.direction == InteractionDirection.INBOUND,
            Interaction.created_at >= since,
        )
        .group_by(Interaction.channel)
    )
    replies_by_channel = {row.channel: row.replies for row in reply_q.all()}

    # Merge channels
    all_channels = set(sent_by_channel.keys()) | set(replies_by_channel.keys())
    result = []
    for ch in sorted(all_channels, key=lambda c: c.value if hasattr(c, "value") else str(c)):
        sent = sent_by_channel.get(ch, 0)
        replies = replies_by_channel.get(ch, 0)
        rate = round((replies / sent) * 100, 1) if sent > 0 else 0.0
        result.append(ChannelBreakdownItem(
            channel=ch.value if hasattr(ch, "value") else str(ch),
            steps_sent=sent,
            replies=replies,
            reply_rate=rate,
        ))

    logger.debug("analytics.channels", tenant_id=str(tenant_id), days=days)
    return result


@router.get("/recent-replies", response_model=list[RecentReplyItem])
async def get_recent_replies(
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
    db: AsyncSession = Depends(get_session_flexible),
    tenant_id: UUID = Depends(get_effective_tenant_id),
) -> list[RecentReplyItem]:
    """Retorna as respostas mais recentes."""
    q = await db.execute(
        select(
            Interaction.id,
            Interaction.channel,
            Interaction.intent,
            Interaction.created_at,
            Lead.id.label("lead_id"),
            Lead.name.label("lead_name"),
            Lead.company.label("company_name"),
        )
        .join(Lead, Interaction.lead_id == Lead.id)
        .where(
            Interaction.tenant_id == tenant_id,
            Interaction.direction == InteractionDirection.INBOUND,
        )
        .order_by(Interaction.created_at.desc())
        .limit(limit)
    )
    rows = q.all()

    result = [
        RecentReplyItem(
            lead_id=str(row.lead_id),
            lead_name=row.lead_name,
            company_name=row.company_name,
            intent=row.intent.value if row.intent else "neutral",
            replied_at=row.created_at.isoformat() if row.created_at else "",
            channel=row.channel.value if hasattr(row.channel, "value") else str(row.channel),
        )
        for row in rows
    ]

    logger.debug("analytics.recent_replies", tenant_id=str(tenant_id), limit=limit)
    return result


@router.get("/intents", response_model=list[IntentBreakdownItem])
async def get_intent_breakdown(
    days: Annotated[int, Query(ge=1, le=365)] = 30,
    db: AsyncSession = Depends(get_session_flexible),
    tenant_id: UUID = Depends(get_effective_tenant_id),
) -> list[IntentBreakdownItem]:
    """Retorna breakdown de intents das respostas recebidas."""
    since = _utc_days_ago(days)

    q = await db.execute(
        select(
            Interaction.intent,
            func.count(Interaction.id).label("cnt"),
        )
        .where(
            Interaction.tenant_id == tenant_id,
            Interaction.direction == InteractionDirection.INBOUND,
            Interaction.intent.is_not(None),
            Interaction.created_at >= since,
        )
        .group_by(Interaction.intent)
    )
    rows = q.all()

    total = sum(row.cnt for row in rows) or 1
    result = [
        IntentBreakdownItem(
            intent=row.intent.value if hasattr(row.intent, "value") else str(row.intent),
            count=row.cnt,
            percentage=round((row.cnt / total) * 100, 1),
        )
        for row in rows
    ]

    logger.debug("analytics.intents", tenant_id=str(tenant_id), days=days)
    return result
