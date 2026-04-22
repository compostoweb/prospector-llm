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

from datetime import UTC, date, datetime, time, timedelta
from typing import Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import and_, case, func, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_effective_tenant_id, get_session_flexible
from models.cadence import Cadence
from models.cadence_step import CadenceStep
from models.enums import Channel, InteractionDirection, LeadStatus, StepStatus
from models.interaction import Interaction
from models.lead import Lead
from models.lead_email import LeadEmail
from services.cadence_manager import CadenceManager
from services.reply_matching import (
    reliable_reply_interaction_condition,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/analytics", tags=["Analytics"])
_cadence_manager = CadenceManager()

_EMAIL_ONLY_CADENCE_TYPE = "email_only"


# ── Schemas ───────────────────────────────────────────────────────────


class DashboardStatsResponse(BaseModel):
    leads_total: int = 0
    leads_in_cadence: int = 0
    leads_converted: int = 0
    leads_archived: int = 0
    steps_sent_today: int = 0
    steps_sent_week: int = 0
    steps_sent_period: int = 0
    replies_today: int = 0
    replies_week: int = 0
    replies_period: int = 0
    conversion_rate: float = 0.0
    # Trends (variação % vs período anterior)
    leads_total_trend: float = 0.0
    leads_in_cadence_trend: float = 0.0
    leads_converted_trend: float = 0.0
    steps_sent_trend: float = 0.0
    replies_trend: float = 0.0


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


class FunnelItem(BaseModel):
    status: str
    count: int = 0
    percentage: float = 0.0


class CadencePerformanceItem(BaseModel):
    cadence_id: str
    cadence_name: str
    leads_active: int = 0
    steps_sent: int = 0
    replies: int = 0
    reply_rate: float = 0.0


class CadenceOverviewItem(BaseModel):
    cadence_id: str
    total_leads: int = 0
    leads_active: int = 0
    leads_converted: int = 0
    leads_finished: int = 0
    replies: int = 0
    leads_paused: int = 0


class CadenceAnalyticsChannelItem(BaseModel):
    channel: str
    sent: int = 0
    replied: int = 0
    opened: int = 0
    accepted: int = 0
    pending: int = 0
    skipped: int = 0
    failed: int = 0
    open_rate: float = 0.0
    acceptance_rate: float = 0.0
    reply_rate: float = 0.0


class CadenceAnalyticsStepItem(BaseModel):
    step_number: int
    channel: str
    lead_count: int = 0
    sent: int = 0
    replied: int = 0
    opened: int = 0
    bounced: int = 0
    accepted: int = 0
    pending: int = 0
    skipped: int = 0
    failed: int = 0
    open_rate: float = 0.0
    acceptance_rate: float = 0.0
    reply_rate: float = 0.0


class CadenceAnalyticsResponse(BaseModel):
    cadence_id: str
    cadence_name: str
    cadence_type: str
    is_active: bool
    total_leads: int = 0
    leads_active: int = 0
    steps_sent: int = 0
    replies: int = 0
    pending_steps: int = 0
    skipped_steps: int = 0
    failed_steps: int = 0
    reply_rate: float = 0.0
    channel_breakdown: list[CadenceAnalyticsChannelItem] = []
    step_breakdown: list[CadenceAnalyticsStepItem] = []


# ── Helpers ───────────────────────────────────────────────────────────


def _utc_start_of_today() -> datetime:
    now = datetime.now(UTC)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _utc_days_ago(days: int) -> datetime:
    return datetime.now(UTC) - timedelta(days=days)


def _resolve_period_bounds(
    *,
    days: int,
    start_date: date | None = None,
    end_date: date | None = None,
) -> tuple[datetime, datetime]:
    if (start_date is None) != (end_date is None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="start_date e end_date devem ser enviados juntos.",
        )

    if start_date is not None and end_date is not None:
        if end_date < start_date:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="end_date não pode ser anterior a start_date.",
            )

        since = datetime.combine(start_date, time.min, tzinfo=UTC)
        until = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=UTC)
        return since, until

    return _utc_days_ago(days), datetime.now(UTC)


def _previous_period_bounds(since: datetime, until: datetime) -> tuple[datetime, datetime]:
    period_span = until - since
    return since - period_span, since


def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100, 1)


def _cadence_step_period_expr():
    return func.coalesce(CadenceStep.sent_at, CadenceStep.scheduled_at)


def _interaction_matches_cadence_step():
    return CadenceStep.id == Interaction.cadence_step_id


def _reliable_reply_interaction_condition():
    return reliable_reply_interaction_condition()


def _first_reliable_reply_per_cadence_lead_subquery(
    *,
    tenant_id: UUID,
    since: datetime | None = None,
    until: datetime | None = None,
    cadence_id: UUID | None = None,
    cadence_ids: list[UUID] | None = None,
    channel: Channel | None = None,
    cadence_type: str | None = None,
):
    conditions = [
        Interaction.tenant_id == tenant_id,
        CadenceStep.tenant_id == tenant_id,
        _reliable_reply_interaction_condition(),
    ]
    if since is not None:
        conditions.append(Interaction.created_at >= since)
    if until is not None:
        conditions.append(Interaction.created_at < until)
    if cadence_id is not None:
        conditions.append(CadenceStep.cadence_id == cadence_id)
    if cadence_ids:
        conditions.append(CadenceStep.cadence_id.in_(cadence_ids))
    if channel is not None:
        conditions.extend(
            [
                Interaction.channel == channel,
                CadenceStep.channel == channel,
            ]
        )

    ranked_reply_query = select(
        Interaction.id.label("interaction_id"),
        Interaction.lead_id.label("lead_id"),
        Interaction.channel.label("channel"),
        Interaction.created_at.label("replied_at"),
        CadenceStep.cadence_id.label("cadence_id"),
        CadenceStep.step_number.label("step_number"),
        func.row_number()
        .over(
            partition_by=[CadenceStep.cadence_id, Interaction.lead_id],
            order_by=[Interaction.created_at.asc(), Interaction.id.asc()],
        )
        .label("reply_rank"),
    ).join(CadenceStep, CadenceStep.id == Interaction.cadence_step_id)
    if cadence_type is not None:
        ranked_reply_query = ranked_reply_query.join(Cadence, Cadence.id == CadenceStep.cadence_id)
        conditions.append(Cadence.cadence_type == cadence_type)

    ranked_replies_sq = ranked_reply_query.where(*conditions).subquery()

    return (
        select(
            ranked_replies_sq.c.interaction_id,
            ranked_replies_sq.c.lead_id,
            ranked_replies_sq.c.channel,
            ranked_replies_sq.c.replied_at,
            ranked_replies_sq.c.cadence_id,
            ranked_replies_sq.c.step_number,
        )
        .where(ranked_replies_sq.c.reply_rank == 1)
        .subquery()
    )


def _opened_email_interactions_subquery(
    *,
    tenant_id: UUID,
    since: datetime,
    until: datetime | None = None,
    cadence_id: UUID | None = None,
    cadence_ids: list[UUID] | None = None,
    cadence_type: str | None = None,
):
    conditions = [
        Interaction.tenant_id == tenant_id,
        Interaction.channel == Channel.EMAIL,
        Interaction.direction == InteractionDirection.OUTBOUND,
        Interaction.opened.is_(True),
        Interaction.opened_at.is_not(None),
        Interaction.opened_at >= since,
        CadenceStep.tenant_id == tenant_id,
        CadenceStep.channel == Channel.EMAIL,
        CadenceStep.sent_at.is_not(None),
        CadenceStep.sent_at >= since,
    ]
    if until is not None:
        conditions.extend(
            [
                Interaction.opened_at < until,
                CadenceStep.sent_at < until,
            ]
        )
    if cadence_id is not None:
        conditions.append(CadenceStep.cadence_id == cadence_id)
    if cadence_ids:
        conditions.append(CadenceStep.cadence_id.in_(cadence_ids))

    opened_query = select(
        Interaction.id.label("interaction_id"),
        Interaction.lead_id.label("lead_id"),
        Interaction.opened_at.label("opened_at"),
        CadenceStep.cadence_id.label("cadence_id"),
        CadenceStep.step_number.label("step_number"),
        CadenceStep.channel.label("channel"),
    ).join(CadenceStep, CadenceStep.id == Interaction.cadence_step_id)
    if cadence_type is not None:
        opened_query = opened_query.join(Cadence, Cadence.id == CadenceStep.cadence_id)
        conditions.append(Cadence.cadence_type == cadence_type)

    return opened_query.where(*conditions).subquery()


def _latest_email_bounce_step_subquery(
    *,
    tenant_id: UUID,
    since: datetime,
    until: datetime | None = None,
    cadence_id: UUID | None = None,
    cadence_ids: list[UUID] | None = None,
):
    conditions = [
        CadenceStep.tenant_id == tenant_id,
        CadenceStep.channel == Channel.EMAIL,
        CadenceStep.sent_at.is_not(None),
        CadenceStep.sent_at >= since,
        Lead.tenant_id == tenant_id,
        Lead.email_bounced_at.is_not(None),
        Lead.email_bounced_at >= since,
        CadenceStep.sent_at <= Lead.email_bounced_at,
    ]
    if until is not None:
        conditions.extend(
            [
                CadenceStep.sent_at < until,
                Lead.email_bounced_at < until,
            ]
        )

    ranked_bounces_sq = (
        select(
            Lead.id.label("lead_id"),
            CadenceStep.cadence_id.label("cadence_id"),
            CadenceStep.step_number.label("step_number"),
            CadenceStep.channel.label("channel"),
            func.row_number()
            .over(
                partition_by=[Lead.id],
                order_by=[CadenceStep.sent_at.desc(), CadenceStep.id.desc()],
            )
            .label("bounce_rank"),
        )
        .join(Lead, Lead.id == CadenceStep.lead_id)
        .where(*conditions)
        .subquery()
    )

    filtered_bounces = select(
        ranked_bounces_sq.c.lead_id,
        ranked_bounces_sq.c.cadence_id,
        ranked_bounces_sq.c.step_number,
        ranked_bounces_sq.c.channel,
    ).where(ranked_bounces_sq.c.bounce_rank == 1)
    if cadence_id is not None:
        filtered_bounces = filtered_bounces.where(ranked_bounces_sq.c.cadence_id == cadence_id)
    if cadence_ids:
        filtered_bounces = filtered_bounces.where(ranked_bounces_sq.c.cadence_id.in_(cadence_ids))

    return filtered_bounces.subquery()


def _latest_linkedin_accept_step_subquery(
    *,
    tenant_id: UUID,
    since: datetime,
    until: datetime | None = None,
    cadence_id: UUID | None = None,
    cadence_ids: list[UUID] | None = None,
):
    conditions = [
        CadenceStep.tenant_id == tenant_id,
        CadenceStep.channel == Channel.LINKEDIN_CONNECT,
        CadenceStep.sent_at.is_not(None),
        CadenceStep.sent_at >= since,
        Lead.tenant_id == tenant_id,
        Lead.linkedin_connected_at.is_not(None),
        Lead.linkedin_connected_at >= since,
        CadenceStep.sent_at <= Lead.linkedin_connected_at,
    ]
    if until is not None:
        conditions.extend(
            [
                CadenceStep.sent_at < until,
                Lead.linkedin_connected_at < until,
            ]
        )

    ranked_accepts_sq = (
        select(
            Lead.id.label("lead_id"),
            CadenceStep.cadence_id.label("cadence_id"),
            CadenceStep.step_number.label("step_number"),
            CadenceStep.channel.label("channel"),
            func.row_number()
            .over(
                partition_by=[Lead.id],
                order_by=[CadenceStep.sent_at.desc(), CadenceStep.id.desc()],
            )
            .label("accept_rank"),
        )
        .join(Lead, Lead.id == CadenceStep.lead_id)
        .where(*conditions)
        .subquery()
    )

    filtered_accepts = select(
        ranked_accepts_sq.c.lead_id,
        ranked_accepts_sq.c.cadence_id,
        ranked_accepts_sq.c.step_number,
        ranked_accepts_sq.c.channel,
    ).where(ranked_accepts_sq.c.accept_rank == 1)
    if cadence_id is not None:
        filtered_accepts = filtered_accepts.where(ranked_accepts_sq.c.cadence_id == cadence_id)
    if cadence_ids:
        filtered_accepts = filtered_accepts.where(ranked_accepts_sq.c.cadence_id.in_(cadence_ids))

    return filtered_accepts.subquery()


# ── Endpoints ─────────────────────────────────────────────────────────


@router.get("/dashboard", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    days: Annotated[int, Query(ge=1, le=365)] = 30,
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
    db: AsyncSession = Depends(get_session_flexible),
    tenant_id: UUID = Depends(get_effective_tenant_id),
) -> DashboardStatsResponse:
    """Retorna estatísticas gerais do dashboard com trends."""
    today_start = _utc_start_of_today()
    week_ago = _utc_days_ago(7)
    period_start, period_end = _resolve_period_bounds(
        days=days,
        start_date=start_date,
        end_date=end_date,
    )
    prev_period_start, prev_period_end = _previous_period_bounds(period_start, period_end)

    # Lead counts via conditional aggregation (single query)
    lead_q = await db.execute(
        select(
            func.count(Lead.id).label("total"),
            func.count(Lead.id).filter(Lead.status == LeadStatus.IN_CADENCE).label("in_cadence"),
            func.count(Lead.id).filter(Lead.status == LeadStatus.CONVERTED).label("converted"),
            func.count(Lead.id).filter(Lead.status == LeadStatus.ARCHIVED).label("archived"),
        ).where(Lead.tenant_id == tenant_id)
    )
    lead_row = lead_q.one()
    leads_total = lead_row.total or 0
    leads_in_cadence = lead_row.in_cadence or 0
    leads_converted = lead_row.converted or 0
    leads_archived = lead_row.archived or 0

    # Leads created in current period vs previous (for trend)
    lead_trend_q = await db.execute(
        select(
            func.count(Lead.id)
            .filter(Lead.created_at >= period_start, Lead.created_at < period_end)
            .label("current"),
            func.count(Lead.id)
            .filter(
                Lead.created_at >= prev_period_start,
                Lead.created_at < prev_period_end,
            )
            .label("previous"),
        ).where(Lead.tenant_id == tenant_id)
    )
    lead_trend_row = lead_trend_q.one()

    # Steps sent counts (today + week + period + prev period)
    step_q = await db.execute(
        select(
            func.count(CadenceStep.id).filter(CadenceStep.sent_at >= today_start).label("today"),
            func.count(CadenceStep.id).filter(CadenceStep.sent_at >= week_ago).label("week"),
            func.count(CadenceStep.id)
            .filter(CadenceStep.sent_at >= period_start, CadenceStep.sent_at < period_end)
            .label("period"),
            func.count(CadenceStep.id)
            .filter(
                CadenceStep.sent_at >= prev_period_start,
                CadenceStep.sent_at < prev_period_end,
            )
            .label("prev_period"),
        ).where(
            CadenceStep.tenant_id == tenant_id,
            CadenceStep.status.in_([StepStatus.SENT, StepStatus.REPLIED]),
        )
    )
    step_row = step_q.one()
    steps_sent_today = step_row.today or 0
    steps_sent_week = step_row.week or 0
    steps_sent_period = step_row.period or 0
    steps_prev_period = step_row.prev_period or 0

    # Replies (inbound interactions) counts (today + week + period + prev)
    reply_q = await db.execute(
        select(
            func.count(Interaction.id).filter(Interaction.created_at >= today_start).label("today"),
            func.count(Interaction.id).filter(Interaction.created_at >= week_ago).label("week"),
            func.count(Interaction.id)
            .filter(Interaction.created_at >= period_start, Interaction.created_at < period_end)
            .label("period"),
            func.count(Interaction.id)
            .filter(
                Interaction.created_at >= prev_period_start,
                Interaction.created_at < prev_period_end,
            )
            .label("prev_period"),
        ).where(
            Interaction.tenant_id == tenant_id,
            _reliable_reply_interaction_condition(),
        )
    )
    reply_row = reply_q.one()
    replies_today = reply_row.today or 0
    replies_week = reply_row.week or 0
    replies_period = reply_row.period or 0
    replies_prev_period = reply_row.prev_period or 0

    conversion_rate = round((leads_converted / leads_total) * 100, 1) if leads_total > 0 else 0.0

    def _trend(current: int, previous: int) -> float:
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return round(((current - previous) / previous) * 100, 1)

    # Leads enrolled no período atual vs anterior
    # Usa scheduled_at do step 1 (day_offset=0) como proxy da data de enrollment
    enrolled_trend_q = await db.execute(
        select(
            func.count(func.distinct(CadenceStep.lead_id))
            .filter(
                CadenceStep.step_number == 1,
                CadenceStep.scheduled_at >= period_start,
                CadenceStep.scheduled_at < period_end,
            )
            .label("current"),
            func.count(func.distinct(CadenceStep.lead_id))
            .filter(
                CadenceStep.step_number == 1,
                CadenceStep.scheduled_at >= prev_period_start,
                CadenceStep.scheduled_at < prev_period_end,
            )
            .label("previous"),
        ).where(CadenceStep.tenant_id == tenant_id)
    )
    enrolled_trend_row = enrolled_trend_q.one()

    logger.debug("analytics.dashboard", tenant_id=str(tenant_id), days=days)
    return DashboardStatsResponse(
        leads_total=leads_total,
        leads_in_cadence=leads_in_cadence,
        leads_converted=leads_converted,
        leads_archived=leads_archived,
        steps_sent_today=steps_sent_today,
        steps_sent_week=steps_sent_week,
        steps_sent_period=steps_sent_period,
        replies_today=replies_today,
        replies_week=replies_week,
        replies_period=replies_period,
        conversion_rate=conversion_rate,
        leads_total_trend=_trend(lead_trend_row.current or 0, lead_trend_row.previous or 0),
        leads_in_cadence_trend=_trend(
            enrolled_trend_row.current or 0, enrolled_trend_row.previous or 0
        ),
        leads_converted_trend=0.0,
        steps_sent_trend=_trend(steps_sent_period, steps_prev_period),
        replies_trend=_trend(replies_period, replies_prev_period),
    )


@router.get("/channels", response_model=list[ChannelBreakdownItem])
async def get_channel_breakdown(
    days: Annotated[int, Query(ge=1, le=365)] = 30,
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
    db: AsyncSession = Depends(get_session_flexible),
    tenant_id: UUID = Depends(get_effective_tenant_id),
) -> list[ChannelBreakdownItem]:
    """Retorna breakdown de atividade por canal."""
    since, until = _resolve_period_bounds(days=days, start_date=start_date, end_date=end_date)

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
            CadenceStep.sent_at < until,
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
            _reliable_reply_interaction_condition(),
            Interaction.created_at >= since,
            Interaction.created_at < until,
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
        result.append(
            ChannelBreakdownItem(
                channel=ch.value if hasattr(ch, "value") else str(ch),
                steps_sent=sent,
                replies=replies,
                reply_rate=rate,
            )
        )

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
            _reliable_reply_interaction_condition(),
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
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
    db: AsyncSession = Depends(get_session_flexible),
    tenant_id: UUID = Depends(get_effective_tenant_id),
) -> list[IntentBreakdownItem]:
    """Retorna breakdown de intents das respostas recebidas."""
    since, until = _resolve_period_bounds(days=days, start_date=start_date, end_date=end_date)

    q = await db.execute(
        select(
            Interaction.intent,
            func.count(Interaction.id).label("cnt"),
        )
        .where(
            Interaction.tenant_id == tenant_id,
            _reliable_reply_interaction_condition(),
            Interaction.intent.is_not(None),
            Interaction.created_at >= since,
            Interaction.created_at < until,
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


# ── Funnel ────────────────────────────────────────────────────────────


@router.get("/funnel", response_model=list[FunnelItem])
async def get_funnel(
    db: AsyncSession = Depends(get_session_flexible),
    tenant_id: UUID = Depends(get_effective_tenant_id),
) -> list[FunnelItem]:
    """Retorna funil de conversão — contagem de leads por status."""
    q = await db.execute(
        select(
            Lead.status,
            func.count(Lead.id).label("cnt"),
        )
        .where(Lead.tenant_id == tenant_id)
        .group_by(Lead.status)
    )
    rows = q.all()
    total = sum(row.cnt for row in rows) or 1

    # Ordem do funil
    order = [
        LeadStatus.RAW,
        LeadStatus.ENRICHED,
        LeadStatus.IN_CADENCE,
        LeadStatus.CONVERTED,
        LeadStatus.ARCHIVED,
    ]
    counts = {row.status: row.cnt for row in rows}

    result = [
        FunnelItem(
            status=s.value,
            count=counts.get(s, 0),
            percentage=round((counts.get(s, 0) / total) * 100, 1),
        )
        for s in order
    ]

    logger.debug("analytics.funnel", tenant_id=str(tenant_id))
    return result


# ── Performance de cadências ──────────────────────────────────────────


@router.get("/performance", response_model=list[CadencePerformanceItem])
async def get_cadence_performance(
    days: Annotated[int, Query(ge=1, le=365)] = 30,
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=20)] = 5,
    db: AsyncSession = Depends(get_session_flexible),
    tenant_id: UUID = Depends(get_effective_tenant_id),
) -> list[CadencePerformanceItem]:
    """Retorna performance das cadências ativas (top N por steps enviados)."""
    since, until = _resolve_period_bounds(days=days, start_date=start_date, end_date=end_date)

    # Steps sent & replied per cadence
    steps_q = await db.execute(
        select(
            CadenceStep.cadence_id,
            func.count(CadenceStep.id).label("sent"),
        )
        .where(
            CadenceStep.tenant_id == tenant_id,
            CadenceStep.status.in_([StepStatus.SENT, StepStatus.REPLIED]),
            CadenceStep.sent_at >= since,
            CadenceStep.sent_at < until,
        )
        .group_by(CadenceStep.cadence_id)
        .order_by(func.count(CadenceStep.id).desc())
        .limit(limit)
    )
    step_rows = steps_q.all()
    if not step_rows:
        return []

    cadence_ids = [row.cadence_id for row in step_rows]

    # Get cadence names
    cadences_q = await db.execute(
        select(Cadence.id, Cadence.name).where(Cadence.id.in_(cadence_ids))
    )
    name_map = {row.id: row.name for row in cadences_q.all()}

    first_replies_sq = _first_reliable_reply_per_cadence_lead_subquery(
        tenant_id=tenant_id,
        since=since,
        until=until,
        cadence_ids=cadence_ids,
    )
    replies_q = await db.execute(
        select(
            first_replies_sq.c.cadence_id,
            func.count(first_replies_sq.c.interaction_id).label("replied"),
        ).group_by(first_replies_sq.c.cadence_id)
    )
    reply_map = {row.cadence_id: row.replied for row in replies_q.all()}

    # Active leads per cadence (leads currently IN_CADENCE with steps in this cadence)
    active_q = await db.execute(
        select(
            CadenceStep.cadence_id,
            func.count(func.distinct(CadenceStep.lead_id)).label("active"),
        )
        .join(Lead, CadenceStep.lead_id == Lead.id)
        .where(
            CadenceStep.cadence_id.in_(cadence_ids),
            CadenceStep.tenant_id == tenant_id,
            Lead.status == LeadStatus.IN_CADENCE,
        )
        .group_by(CadenceStep.cadence_id)
    )
    active_map = {row.cadence_id: row.active for row in active_q.all()}

    result = []
    for row in step_rows:
        sent = row.sent or 0
        replied = reply_map.get(row.cadence_id, 0)
        rate = round((replied / sent) * 100, 1) if sent > 0 else 0.0
        result.append(
            CadencePerformanceItem(
                cadence_id=str(row.cadence_id),
                cadence_name=name_map.get(row.cadence_id, "—"),
                leads_active=active_map.get(row.cadence_id, 0),
                steps_sent=sent,
                replies=replied,
                reply_rate=rate,
            )
        )

    logger.debug("analytics.performance", tenant_id=str(tenant_id), days=days)
    return result


@router.get("/cadences", response_model=list[CadenceOverviewItem])
async def get_cadences_overview(
    db: AsyncSession = Depends(get_session_flexible),
    tenant_id: UUID = Depends(get_effective_tenant_id),
) -> list[CadenceOverviewItem]:
    """Retorna métricas-resumo por cadência para a listagem principal."""
    cadences_q = await db.execute(select(Cadence).where(Cadence.tenant_id == tenant_id))
    cadences = list(cadences_q.scalars().all())
    for cadence in cadences:
        await _sync_cadence_list_members(cadence, db)

    cadence_ids = [cadence.id for cadence in cadences]
    if not cadence_ids:
        return []

    lead_state_sq = (
        select(
            CadenceStep.cadence_id.label("cadence_id"),
            CadenceStep.lead_id.label("lead_id"),
            func.max(
                case(
                    (CadenceStep.status.in_([StepStatus.PENDING, StepStatus.DISPATCHING]), 1),
                    else_=0,
                )
            ).label("has_pending"),
        )
        .where(
            CadenceStep.tenant_id == tenant_id,
            CadenceStep.cadence_id.in_(cadence_ids),
        )
        .group_by(CadenceStep.cadence_id, CadenceStep.lead_id)
        .subquery()
    )

    first_replies_sq = _first_reliable_reply_per_cadence_lead_subquery(
        tenant_id=tenant_id,
        cadence_ids=cadence_ids,
    )
    reply_progress_sq = (
        select(
            first_replies_sq.c.cadence_id.label("cadence_id"),
            first_replies_sq.c.lead_id.label("lead_id"),
            func.count(first_replies_sq.c.interaction_id).label("reply_count"),
        )
        .group_by(first_replies_sq.c.cadence_id, first_replies_sq.c.lead_id)
        .subquery()
    )

    overview_q = await db.execute(
        select(
            lead_state_sq.c.cadence_id,
            func.count(lead_state_sq.c.lead_id).label("total_leads"),
            func.count(
                case(
                    (
                        and_(
                            Lead.status == LeadStatus.IN_CADENCE,
                            lead_state_sq.c.has_pending == 1,
                            func.coalesce(reply_progress_sq.c.reply_count, 0) == 0,
                        ),
                        1,
                    )
                )
            ).label("leads_active"),
            func.count(case((Lead.status == LeadStatus.CONVERTED, 1))).label("leads_converted"),
            func.count(
                case(
                    (
                        and_(
                            lead_state_sq.c.has_pending == 0,
                            func.coalesce(reply_progress_sq.c.reply_count, 0) == 0,
                        ),
                        1,
                    )
                )
            ).label("leads_finished"),
            func.coalesce(func.sum(func.coalesce(reply_progress_sq.c.reply_count, 0)), 0).label(
                "replies"
            ),
            func.count(case((func.coalesce(reply_progress_sq.c.reply_count, 0) > 0, 1))).label(
                "leads_paused"
            ),
        )
        .join(Lead, Lead.id == lead_state_sq.c.lead_id)
        .outerjoin(
            reply_progress_sq,
            and_(
                reply_progress_sq.c.cadence_id == lead_state_sq.c.cadence_id,
                reply_progress_sq.c.lead_id == lead_state_sq.c.lead_id,
            ),
        )
        .where(
            Lead.tenant_id == tenant_id,
        )
        .group_by(lead_state_sq.c.cadence_id)
    )
    metrics_map = {
        row.cadence_id: {
            "total_leads": row.total_leads or 0,
            "leads_active": row.leads_active or 0,
            "leads_converted": row.leads_converted or 0,
            "leads_finished": row.leads_finished or 0,
            "replies": row.replies or 0,
            "leads_paused": row.leads_paused or 0,
        }
        for row in overview_q.all()
    }

    logger.debug("analytics.cadences.overview", tenant_id=str(tenant_id))
    return [
        CadenceOverviewItem(
            cadence_id=str(cadence_id),
            total_leads=metrics_map.get(cadence_id, {}).get("total_leads", 0),
            leads_active=metrics_map.get(cadence_id, {}).get("leads_active", 0),
            leads_converted=metrics_map.get(cadence_id, {}).get("leads_converted", 0),
            leads_finished=metrics_map.get(cadence_id, {}).get("leads_finished", 0),
            replies=metrics_map.get(cadence_id, {}).get("replies", 0),
            leads_paused=metrics_map.get(cadence_id, {}).get("leads_paused", 0),
        )
        for cadence_id in cadence_ids
    ]


@router.get("/cadences/{cadence_id}", response_model=CadenceAnalyticsResponse)
async def get_cadence_analytics(
    cadence_id: UUID,
    days: Annotated[int, Query(ge=1, le=365)] = 30,
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
    db: AsyncSession = Depends(get_session_flexible),
    tenant_id: UUID = Depends(get_effective_tenant_id),
) -> CadenceAnalyticsResponse:
    """Retorna analytics operacionais de uma cadência específica."""
    since, until = _resolve_period_bounds(days=days, start_date=start_date, end_date=end_date)
    period_expr = _cadence_step_period_expr()

    cadence_q = await db.execute(
        select(Cadence).where(
            Cadence.id == cadence_id,
            Cadence.tenant_id == tenant_id,
        )
    )
    cadence = cadence_q.scalar_one_or_none()
    if cadence is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cadência não encontrada.",
        )

    await _sync_cadence_list_members(cadence, db)

    lead_counts_q = await db.execute(
        select(func.count(func.distinct(CadenceStep.lead_id))).where(
            CadenceStep.tenant_id == tenant_id,
            CadenceStep.cadence_id == cadence_id,
        )
    )
    total_leads = lead_counts_q.scalar() or 0

    active_leads_q = await db.execute(
        select(func.count(func.distinct(CadenceStep.lead_id)))
        .join(Lead, Lead.id == CadenceStep.lead_id)
        .where(
            CadenceStep.tenant_id == tenant_id,
            CadenceStep.cadence_id == cadence_id,
            Lead.status == LeadStatus.IN_CADENCE,
        )
    )
    leads_active = active_leads_q.scalar() or 0

    step_summary_q = await db.execute(
        select(
            func.count(CadenceStep.id)
            .filter(
                CadenceStep.status.in_([StepStatus.SENT, StepStatus.REPLIED]),
                period_expr >= since,
                period_expr < until,
            )
            .label("sent"),
            func.count(CadenceStep.id)
            .filter(CadenceStep.status.in_([StepStatus.PENDING, StepStatus.DISPATCHING]))
            .label("pending"),
            func.count(CadenceStep.id)
            .filter(
                CadenceStep.status == StepStatus.SKIPPED,
                period_expr >= since,
                period_expr < until,
            )
            .label("skipped"),
            func.count(CadenceStep.id)
            .filter(
                CadenceStep.status == StepStatus.FAILED,
                period_expr >= since,
                period_expr < until,
            )
            .label("failed"),
        ).where(
            CadenceStep.tenant_id == tenant_id,
            CadenceStep.cadence_id == cadence_id,
        )
    )
    step_summary = step_summary_q.one()

    first_replies_sq = _first_reliable_reply_per_cadence_lead_subquery(
        tenant_id=tenant_id,
        since=since,
        until=until,
        cadence_id=cadence_id,
    )
    opened_email_sq = _opened_email_interactions_subquery(
        tenant_id=tenant_id,
        since=since,
        until=until,
        cadence_id=cadence_id,
    )
    bounced_email_sq = _latest_email_bounce_step_subquery(
        tenant_id=tenant_id,
        since=since,
        until=until,
        cadence_id=cadence_id,
    )
    linkedin_accepts_sq = _latest_linkedin_accept_step_subquery(
        tenant_id=tenant_id,
        since=since,
        until=until,
        cadence_id=cadence_id,
    )
    reply_summary_q = await db.execute(
        select(func.count(first_replies_sq.c.interaction_id).label("replied"))
    )
    reply_summary = reply_summary_q.one()

    steps_sent = step_summary.sent or 0
    replies = reply_summary.replied or 0
    pending_steps = step_summary.pending or 0
    skipped_steps = step_summary.skipped or 0
    failed_steps = step_summary.failed or 0

    channel_step_q = await db.execute(
        select(
            CadenceStep.channel,
            func.count(CadenceStep.id)
            .filter(
                CadenceStep.status.in_([StepStatus.SENT, StepStatus.REPLIED]),
                period_expr >= since,
                period_expr < until,
            )
            .label("sent"),
            func.count(CadenceStep.id)
            .filter(CadenceStep.status.in_([StepStatus.PENDING, StepStatus.DISPATCHING]))
            .label("pending"),
            func.count(CadenceStep.id)
            .filter(
                CadenceStep.status == StepStatus.SKIPPED,
                period_expr >= since,
                period_expr < until,
            )
            .label("skipped"),
            func.count(CadenceStep.id)
            .filter(
                CadenceStep.status == StepStatus.FAILED,
                period_expr >= since,
                period_expr < until,
            )
            .label("failed"),
        )
        .where(
            CadenceStep.tenant_id == tenant_id,
            CadenceStep.cadence_id == cadence_id,
        )
        .group_by(CadenceStep.channel)
        .order_by(CadenceStep.channel.asc())
    )
    channel_rows = channel_step_q.all()
    channel_reply_q = await db.execute(
        select(
            first_replies_sq.c.channel,
            func.count(first_replies_sq.c.interaction_id).label("replied"),
        ).group_by(first_replies_sq.c.channel)
    )
    channel_open_q = await db.execute(
        select(
            opened_email_sq.c.channel,
            func.count(opened_email_sq.c.interaction_id).label("opened"),
        ).group_by(opened_email_sq.c.channel)
    )
    channel_accept_q = await db.execute(
        select(
            linkedin_accepts_sq.c.channel,
            func.count(linkedin_accepts_sq.c.lead_id).label("accepted"),
        ).group_by(linkedin_accepts_sq.c.channel)
    )
    channel_reply_map = {row.channel: row.replied for row in channel_reply_q.all()}
    channel_open_map = {row.channel: row.opened for row in channel_open_q.all()}
    channel_accept_map = {row.channel: row.accepted for row in channel_accept_q.all()}
    channel_stats_map = {row.channel: row for row in channel_rows}
    channel_breakdown = []
    for channel in sorted(
        channel_stats_map.keys()
        | channel_reply_map.keys()
        | channel_open_map.keys()
        | channel_accept_map.keys(),
        key=lambda item: item.value,
    ):
        row = channel_stats_map.get(channel)
        sent = row.sent if row is not None else 0
        replied = channel_reply_map.get(channel, 0)
        opened = channel_open_map.get(channel, 0)
        accepted = channel_accept_map.get(channel, 0)
        pending = row.pending if row is not None else 0
        skipped = row.skipped if row is not None else 0
        failed = row.failed if row is not None else 0
        channel_breakdown.append(
            CadenceAnalyticsChannelItem(
                channel=channel.value if hasattr(channel, "value") else str(channel),
                sent=sent or 0,
                replied=replied or 0,
                opened=opened or 0,
                accepted=accepted or 0,
                pending=pending or 0,
                skipped=skipped or 0,
                failed=failed or 0,
                open_rate=_safe_rate(opened or 0, sent or 0),
                acceptance_rate=_safe_rate(accepted or 0, sent or 0),
                reply_rate=_safe_rate(replied or 0, sent or 0),
            )
        )

    step_stats_q = await db.execute(
        select(
            CadenceStep.step_number,
            CadenceStep.channel,
            func.count(CadenceStep.id)
            .filter(
                CadenceStep.status.in_([StepStatus.SENT, StepStatus.REPLIED]),
                period_expr >= since,
                period_expr < until,
            )
            .label("sent"),
            func.count(CadenceStep.id)
            .filter(CadenceStep.status.in_([StepStatus.PENDING, StepStatus.DISPATCHING]))
            .label("pending"),
            func.count(CadenceStep.id)
            .filter(
                CadenceStep.status == StepStatus.SKIPPED,
                period_expr >= since,
                period_expr < until,
            )
            .label("skipped"),
            func.count(CadenceStep.id)
            .filter(
                CadenceStep.status == StepStatus.FAILED,
                period_expr >= since,
                period_expr < until,
            )
            .label("failed"),
        )
        .where(
            CadenceStep.tenant_id == tenant_id,
            CadenceStep.cadence_id == cadence_id,
        )
        .group_by(CadenceStep.step_number, CadenceStep.channel)
        .order_by(CadenceStep.step_number.asc(), CadenceStep.channel.asc())
    )
    step_rows = step_stats_q.all()
    step_reply_q = await db.execute(
        select(
            first_replies_sq.c.step_number,
            first_replies_sq.c.channel,
            func.count(first_replies_sq.c.interaction_id).label("replied"),
        ).group_by(first_replies_sq.c.step_number, first_replies_sq.c.channel)
    )
    step_open_q = await db.execute(
        select(
            opened_email_sq.c.step_number,
            opened_email_sq.c.channel,
            func.count(opened_email_sq.c.interaction_id).label("opened"),
        ).group_by(opened_email_sq.c.step_number, opened_email_sq.c.channel)
    )
    step_bounce_q = await db.execute(
        select(
            bounced_email_sq.c.step_number,
            bounced_email_sq.c.channel,
            func.count(bounced_email_sq.c.lead_id).label("bounced"),
        ).group_by(bounced_email_sq.c.step_number, bounced_email_sq.c.channel)
    )
    step_accept_q = await db.execute(
        select(
            linkedin_accepts_sq.c.step_number,
            linkedin_accepts_sq.c.channel,
            func.count(linkedin_accepts_sq.c.lead_id).label("accepted"),
        ).group_by(linkedin_accepts_sq.c.step_number, linkedin_accepts_sq.c.channel)
    )
    step_reply_map = {(row.step_number, row.channel): row.replied for row in step_reply_q.all()}
    step_open_map = {(row.step_number, row.channel): row.opened for row in step_open_q.all()}
    step_bounce_map = {(row.step_number, row.channel): row.bounced for row in step_bounce_q.all()}
    step_accept_map = {(row.step_number, row.channel): row.accepted for row in step_accept_q.all()}
    step_stats_map = {(row.step_number, row.channel): row for row in step_rows}
    step_breakdown = []
    for step_number, channel in sorted(
        step_stats_map.keys()
        | step_reply_map.keys()
        | step_open_map.keys()
        | step_bounce_map.keys()
        | step_accept_map.keys(),
        key=lambda item: (item[0], item[1].value),
    ):
        step_row = step_stats_map.get((step_number, channel))
        sent = step_row.sent if step_row is not None else 0
        replied = step_reply_map.get((step_number, channel), 0)
        opened = step_open_map.get((step_number, channel), 0)
        bounced = step_bounce_map.get((step_number, channel), 0)
        accepted = step_accept_map.get((step_number, channel), 0)
        pending = step_row.pending if step_row is not None else 0
        skipped = step_row.skipped if step_row is not None else 0
        failed = step_row.failed if step_row is not None else 0
        lead_count = (sent or 0) + (pending or 0) + (skipped or 0) + (failed or 0)
        step_breakdown.append(
            CadenceAnalyticsStepItem(
                step_number=step_number,
                channel=channel.value if hasattr(channel, "value") else str(channel),
                lead_count=lead_count,
                sent=sent or 0,
                replied=replied or 0,
                opened=opened or 0,
                bounced=bounced or 0,
                accepted=accepted or 0,
                pending=pending or 0,
                skipped=skipped or 0,
                failed=failed or 0,
                open_rate=_safe_rate(opened or 0, sent or 0),
                acceptance_rate=_safe_rate(accepted or 0, sent or 0),
                reply_rate=_safe_rate(replied or 0, sent or 0),
            )
        )

    logger.debug(
        "analytics.cadence.detail",
        tenant_id=str(tenant_id),
        cadence_id=str(cadence_id),
        days=days,
    )
    return CadenceAnalyticsResponse(
        cadence_id=str(cadence.id),
        cadence_name=cadence.name,
        cadence_type=cadence.cadence_type,
        is_active=cadence.is_active,
        total_leads=total_leads,
        leads_active=leads_active,
        steps_sent=steps_sent,
        replies=replies,
        pending_steps=pending_steps,
        skipped_steps=skipped_steps,
        failed_steps=failed_steps,
        reply_rate=_safe_rate(replies, steps_sent),
        channel_breakdown=channel_breakdown,
        step_breakdown=step_breakdown,
    )


async def _sync_cadence_list_members(cadence: Cadence, db: AsyncSession) -> int:
    if cadence.lead_list_id is None:
        return 0
    return await _cadence_manager.auto_enroll_list_members(cadence, db)


# ── Email Analytics ───────────────────────────────────────────────────


class EmailStatsResponse(BaseModel):
    sent: int = 0
    opened: int = 0
    replied: int = 0
    unsubscribed: int = 0
    bounced: int = 0
    open_rate: float = 0.0
    reply_rate: float = 0.0
    bounce_rate: float = 0.0
    unsubscribe_rate: float = 0.0


class EmailCadenceItem(BaseModel):
    cadence_id: str
    cadence_name: str
    sent: int = 0
    opened: int = 0
    replied: int = 0
    bounced: int = 0
    open_rate: float = 0.0
    reply_rate: float = 0.0


class EmailOverTimeItem(BaseModel):
    date: str
    sent: int = 0
    opened: int = 0
    replied: int = 0


class EmailABResultItem(BaseModel):
    subject: str
    sent: int = 0
    opened: int = 0
    open_rate: float = 0.0


@router.get("/email/stats", response_model=EmailStatsResponse)
async def get_email_stats(
    days: Annotated[int, Query(ge=1, le=365)] = 30,
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
    db: AsyncSession = Depends(get_session_flexible),
    tenant_id: UUID = Depends(get_effective_tenant_id),
) -> EmailStatsResponse:
    """Estatísticas gerais de e-mail: enviados, abertos, respondidos, descadastros."""
    from models.email_unsubscribe import EmailUnsubscribe  # noqa: PLC0415

    since, until = _resolve_period_bounds(days=days, start_date=start_date, end_date=end_date)

    # Enviados (outbound EMAIL) apenas de cadências email_only
    sent_q = await db.execute(
        select(func.count(CadenceStep.id))
        .join(Cadence, Cadence.id == CadenceStep.cadence_id)
        .where(
            CadenceStep.tenant_id == tenant_id,
            CadenceStep.channel == Channel.EMAIL,
            CadenceStep.status.in_([StepStatus.SENT, StepStatus.REPLIED]),
            CadenceStep.sent_at >= since,
            CadenceStep.sent_at < until,
            Cadence.cadence_type == _EMAIL_ONLY_CADENCE_TYPE,
        )
    )
    sent = sent_q.scalar() or 0

    opened_email_sq = _opened_email_interactions_subquery(
        tenant_id=tenant_id,
        since=since,
        until=until,
        cadence_type=_EMAIL_ONLY_CADENCE_TYPE,
    )

    # Abertos apenas de cadências email_only
    opened_q = await db.execute(select(func.count(opened_email_sq.c.interaction_id)))
    opened = opened_q.scalar() or 0

    first_email_replies_sq = _first_reliable_reply_per_cadence_lead_subquery(
        tenant_id=tenant_id,
        since=since,
        until=until,
        channel=Channel.EMAIL,
        cadence_type=_EMAIL_ONLY_CADENCE_TYPE,
    )

    # Respondidos (primeira resposta confiável por lead) apenas de cadências email_only
    replied_q = await db.execute(select(func.count(first_email_replies_sq.c.interaction_id)))
    replied = replied_q.scalar() or 0

    # Descadastros associados a leads em cadências email_only
    unsub_q = await db.execute(
        select(func.count(func.distinct(EmailUnsubscribe.id)))
        .join(LeadEmail, func.lower(LeadEmail.email) == func.lower(EmailUnsubscribe.email))
        .join(Lead, Lead.id == LeadEmail.lead_id)
        .join(CadenceStep, CadenceStep.lead_id == Lead.id)
        .join(Cadence, Cadence.id == CadenceStep.cadence_id)
        .where(
            EmailUnsubscribe.tenant_id == tenant_id,
            EmailUnsubscribe.unsubscribed_at >= since,
            EmailUnsubscribe.unsubscribed_at < until,
            LeadEmail.tenant_id == tenant_id,
            CadenceStep.tenant_id == tenant_id,
            CadenceStep.channel == Channel.EMAIL,
            Cadence.cadence_type == _EMAIL_ONLY_CADENCE_TYPE,
        )
    )
    unsubscribed = unsub_q.scalar() or 0

    # Bounces detectados no período para leads em cadências email_only
    bounced_q = await db.execute(
        select(func.count(func.distinct(Lead.id)))
        .join(CadenceStep, CadenceStep.lead_id == Lead.id)
        .join(Cadence, Cadence.id == CadenceStep.cadence_id)
        .where(
            Lead.tenant_id == tenant_id,
            Lead.email_bounced_at >= since,
            Lead.email_bounced_at < until,
            CadenceStep.tenant_id == tenant_id,
            CadenceStep.channel == Channel.EMAIL,
            Cadence.cadence_type == _EMAIL_ONLY_CADENCE_TYPE,
        )
    )
    bounced = bounced_q.scalar() or 0

    open_rate = round((opened / sent) * 100, 1) if sent > 0 else 0.0
    reply_rate = round((replied / sent) * 100, 1) if sent > 0 else 0.0
    bounce_rate = round((bounced / sent) * 100, 1) if sent > 0 else 0.0
    unsubscribe_rate = round((unsubscribed / sent) * 100, 1) if sent > 0 else 0.0

    logger.debug("analytics.email.stats", tenant_id=str(tenant_id), days=days)
    return EmailStatsResponse(
        sent=sent,
        opened=opened,
        replied=replied,
        unsubscribed=unsubscribed,
        bounced=bounced,
        open_rate=open_rate,
        reply_rate=reply_rate,
        bounce_rate=bounce_rate,
        unsubscribe_rate=unsubscribe_rate,
    )


@router.get("/email/cadences", response_model=list[EmailCadenceItem])
async def get_email_cadences_stats(
    days: Annotated[int, Query(ge=1, le=365)] = 30,
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
    db: AsyncSession = Depends(get_session_flexible),
    tenant_id: UUID = Depends(get_effective_tenant_id),
) -> list[EmailCadenceItem]:
    """Performance por cadência: enviados, abertos, taxa de abertura e resposta."""
    since, until = _resolve_period_bounds(days=days, start_date=start_date, end_date=end_date)

    # Steps EMAIL enviados por cadência email_only
    steps_q = await db.execute(
        select(
            CadenceStep.cadence_id,
            func.count(CadenceStep.id).label("sent"),
        )
        .join(Cadence, Cadence.id == CadenceStep.cadence_id)
        .where(
            CadenceStep.tenant_id == tenant_id,
            CadenceStep.channel == Channel.EMAIL,
            CadenceStep.status.in_([StepStatus.SENT, StepStatus.REPLIED]),
            CadenceStep.sent_at >= since,
            CadenceStep.sent_at < until,
            Cadence.cadence_type == _EMAIL_ONLY_CADENCE_TYPE,
        )
        .group_by(CadenceStep.cadence_id)
        .order_by(func.count(CadenceStep.id).desc())
    )
    step_rows = steps_q.all()
    if not step_rows:
        return []

    cadence_ids = [row.cadence_id for row in step_rows]

    cadences_q = await db.execute(
        select(Cadence.id, Cadence.name).where(Cadence.id.in_(cadence_ids))
    )
    name_map = {row.id: row.name for row in cadences_q.all()}

    opened_email_sq = _opened_email_interactions_subquery(
        tenant_id=tenant_id,
        since=since,
        until=until,
        cadence_ids=cadence_ids,
        cadence_type=_EMAIL_ONLY_CADENCE_TYPE,
    )

    # Abertos por cadência
    opened_q = await db.execute(
        select(
            opened_email_sq.c.cadence_id,
            func.count(opened_email_sq.c.interaction_id).label("opened"),
        ).group_by(opened_email_sq.c.cadence_id)
    )
    opened_map = {row.cadence_id: row.opened for row in opened_q.all()}

    first_email_replies_sq = _first_reliable_reply_per_cadence_lead_subquery(
        tenant_id=tenant_id,
        since=since,
        until=until,
        cadence_ids=cadence_ids,
        channel=Channel.EMAIL,
        cadence_type=_EMAIL_ONLY_CADENCE_TYPE,
    )

    # Respondidos por cadência (primeira resposta confiável por lead)
    replied_q = await db.execute(
        select(
            first_email_replies_sq.c.cadence_id,
            func.count(first_email_replies_sq.c.interaction_id).label("replied"),
        ).group_by(first_email_replies_sq.c.cadence_id)
    )
    replied_map = {row.cadence_id: row.replied for row in replied_q.all()}

    # Bounces por cadência (via CadenceStep.lead_id + Lead)
    bounced_q = await db.execute(
        select(
            CadenceStep.cadence_id,
            func.count(func.distinct(Lead.id)).label("bounced"),
        )
        .join(Lead, Lead.id == CadenceStep.lead_id)
        .join(Cadence, Cadence.id == CadenceStep.cadence_id)
        .where(
            CadenceStep.cadence_id.in_(cadence_ids),
            CadenceStep.tenant_id == tenant_id,
            CadenceStep.channel == Channel.EMAIL,
            Lead.email_bounced_at.is_not(None),
            Lead.email_bounced_at >= since,
            Lead.email_bounced_at < until,
            Cadence.cadence_type == _EMAIL_ONLY_CADENCE_TYPE,
        )
        .group_by(CadenceStep.cadence_id)
    )
    bounced_map = {row.cadence_id: row.bounced for row in bounced_q.all()}

    result = []
    for row in step_rows:
        sent = row.sent or 0
        opened = opened_map.get(row.cadence_id, 0)
        replied = replied_map.get(row.cadence_id, 0)
        bounced = bounced_map.get(row.cadence_id, 0)
        result.append(
            EmailCadenceItem(
                cadence_id=str(row.cadence_id),
                cadence_name=name_map.get(row.cadence_id, "—"),
                sent=sent,
                opened=opened,
                replied=replied,
                bounced=bounced,
                open_rate=round((opened / sent) * 100, 1) if sent > 0 else 0.0,
                reply_rate=round((replied / sent) * 100, 1) if sent > 0 else 0.0,
            )
        )

    logger.debug("analytics.email.cadences", tenant_id=str(tenant_id), days=days)
    return result


@router.get("/email/over-time", response_model=list[EmailOverTimeItem])
async def get_email_over_time(
    days: Annotated[int, Query(ge=1, le=365)] = 30,
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
    db: AsyncSession = Depends(get_session_flexible),
    tenant_id: UUID = Depends(get_effective_tenant_id),
) -> list[EmailOverTimeItem]:
    """Série temporal diária de e-mails enviados, abertos e respondidos."""
    since, until = _resolve_period_bounds(days=days, start_date=start_date, end_date=end_date)
    sent_step_day_expr = func.date_trunc(literal_column("'day'"), CadenceStep.sent_at)

    # Enviados por dia apenas de cadências email_only
    sent_q = await db.execute(
        select(
            sent_step_day_expr.label("day"),
            func.count(CadenceStep.id).label("cnt"),
        )
        .join(Cadence, Cadence.id == CadenceStep.cadence_id)
        .where(
            CadenceStep.tenant_id == tenant_id,
            CadenceStep.channel == Channel.EMAIL,
            CadenceStep.status.in_([StepStatus.SENT, StepStatus.REPLIED]),
            CadenceStep.sent_at >= since,
            CadenceStep.sent_at < until,
            Cadence.cadence_type == _EMAIL_ONLY_CADENCE_TYPE,
        )
        .group_by(sent_step_day_expr)
    )
    sent_map: dict[str, int] = {}
    for row in sent_q.all():
        sent_map[row.day.strftime("%Y-%m-%d")] = row.cnt

    # Abertos por dia apenas de cadências email_only
    opened_email_sq = _opened_email_interactions_subquery(
        tenant_id=tenant_id,
        since=since,
        until=until,
        cadence_type=_EMAIL_ONLY_CADENCE_TYPE,
    )
    opened_q = await db.execute(
        select(
            func.date_trunc(literal_column("'day'"), opened_email_sq.c.opened_at).label("day"),
            func.count(opened_email_sq.c.interaction_id).label("cnt"),
        ).group_by(func.date_trunc(literal_column("'day'"), opened_email_sq.c.opened_at))
    )
    opened_map: dict[str, int] = {}
    for row in opened_q.all():
        opened_map[row.day.strftime("%Y-%m-%d")] = row.cnt

    first_email_replies_sq = _first_reliable_reply_per_cadence_lead_subquery(
        tenant_id=tenant_id,
        since=since,
        until=until,
        channel=Channel.EMAIL,
        cadence_type=_EMAIL_ONLY_CADENCE_TYPE,
    )

    # Respondidos por dia (primeira resposta confiável por lead) apenas de cadências email_only
    replied_q = await db.execute(
        select(
            func.date_trunc(literal_column("'day'"), first_email_replies_sq.c.replied_at).label(
                "day"
            ),
            func.count(first_email_replies_sq.c.interaction_id).label("cnt"),
        ).group_by(func.date_trunc(literal_column("'day'"), first_email_replies_sq.c.replied_at))
    )
    replied_map: dict[str, int] = {}
    for row in replied_q.all():
        replied_map[row.day.strftime("%Y-%m-%d")] = row.cnt

    all_days = sorted(set(sent_map) | set(opened_map) | set(replied_map))
    result = [
        EmailOverTimeItem(
            date=d,
            sent=sent_map.get(d, 0),
            opened=opened_map.get(d, 0),
            replied=replied_map.get(d, 0),
        )
        for d in all_days
    ]

    logger.debug("analytics.email.over_time", tenant_id=str(tenant_id), days=days)
    return result


@router.get("/email/ab-results", response_model=list[EmailABResultItem])
async def get_email_ab_results(
    cadence_id: UUID = Query(..., description="ID da cadência"),
    step_number: int = Query(..., ge=1, description="Número do step"),
    days: Annotated[int, Query(ge=1, le=365)] = 30,
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
    db: AsyncSession = Depends(get_session_flexible),
    tenant_id: UUID = Depends(get_effective_tenant_id),
) -> list[EmailABResultItem]:
    """Resultados A/B por variante de assunto para um step específico."""
    since, until = _resolve_period_bounds(days=days, start_date=start_date, end_date=end_date)

    # Busca steps agrupados por subject_used
    q = await db.execute(
        select(
            CadenceStep.subject_used,
            func.count(CadenceStep.id).label("sent"),
        )
        .join(Cadence, Cadence.id == CadenceStep.cadence_id)
        .where(
            CadenceStep.tenant_id == tenant_id,
            CadenceStep.cadence_id == cadence_id,
            CadenceStep.step_number == step_number,
            CadenceStep.channel == Channel.EMAIL,
            CadenceStep.status.in_([StepStatus.SENT, StepStatus.REPLIED]),
            CadenceStep.subject_used.is_not(None),
            CadenceStep.sent_at >= since,
            CadenceStep.sent_at < until,
            Cadence.cadence_type == _EMAIL_ONLY_CADENCE_TYPE,
        )
        .group_by(CadenceStep.subject_used)
        .order_by(func.count(CadenceStep.id).desc())
    )
    rows = q.all()
    if not rows:
        return []

    # Abertos por subject_used via join com Interaction
    opened_q = await db.execute(
        select(
            CadenceStep.subject_used,
            func.count(func.distinct(Interaction.id)).label("opened"),
        )
        .join(Interaction, Interaction.cadence_step_id == CadenceStep.id)
        .join(Cadence, Cadence.id == CadenceStep.cadence_id)
        .where(
            CadenceStep.tenant_id == tenant_id,
            CadenceStep.cadence_id == cadence_id,
            CadenceStep.step_number == step_number,
            CadenceStep.channel == Channel.EMAIL,
            CadenceStep.subject_used.is_not(None),
            CadenceStep.sent_at >= since,
            CadenceStep.sent_at < until,
            Interaction.channel == Channel.EMAIL,
            Interaction.direction == InteractionDirection.OUTBOUND,
            Interaction.opened.is_(True),
            Interaction.opened_at >= since,
            Interaction.opened_at < until,
            Cadence.cadence_type == _EMAIL_ONLY_CADENCE_TYPE,
        )
        .group_by(CadenceStep.subject_used)
    )
    opened_map: dict[str | None, int] = {row.subject_used: row.opened for row in opened_q.all()}

    result = [
        EmailABResultItem(
            subject=row.subject_used or "(sem assunto)",
            sent=row.sent,
            opened=opened_map.get(row.subject_used, 0),
            open_rate=round((opened_map.get(row.subject_used, 0) / row.sent) * 100, 1)
            if row.sent > 0
            else 0.0,
        )
        for row in rows
    ]

    logger.debug(
        "analytics.email.ab_results",
        tenant_id=str(tenant_id),
        cadence_id=str(cadence_id),
        step_number=step_number,
        days=days,
    )
    return result
