"""
api/routes/llm_usage_analytics.py

Analytics de consumo de LLM por período, provider/modelo e módulo/tarefa.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_effective_tenant_id, get_session_flexible
from models.llm_usage_hourly import LLMUsageHourlyAggregate

Granularity = Literal["hour", "day", "week", "month"]
BreakdownDimension = Literal["module", "task_type", "provider", "model", "feature"]

router = APIRouter(prefix="/analytics/llm", tags=["Analytics", "LLM"])


class LLMUsageSummaryResponse(BaseModel):
    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    avg_input_tokens_per_request: float = 0.0
    avg_output_tokens_per_request: float = 0.0
    avg_total_tokens_per_request: float = 0.0


class LLMUsageComparisonResponse(BaseModel):
    current: LLMUsageSummaryResponse
    previous: LLMUsageSummaryResponse
    requests_change_pct: float | None = None
    total_tokens_change_pct: float | None = None
    estimated_cost_change_pct: float | None = None
    avg_output_tokens_change_pct: float | None = None


class LLMUsageTimeSeriesPoint(BaseModel):
    bucket_start: str
    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0


class LLMUsageBreakdownItem(BaseModel):
    key: str
    label: str
    provider: str | None = None
    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0


def _utc_days_ago(days: int) -> datetime:
    return datetime.now(UTC) - timedelta(days=days)


def _floor_bucket(value: datetime, granularity: Granularity) -> datetime:
    dt = value.astimezone(UTC).replace(second=0, microsecond=0)
    if granularity == "hour":
        return dt.replace(minute=0)
    if granularity == "day":
        return dt.replace(hour=0, minute=0)
    if granularity == "week":
        start = dt - timedelta(days=dt.weekday())
        return start.replace(hour=0, minute=0)
    return dt.replace(day=1, hour=0, minute=0)


def _advance_bucket(value: datetime, granularity: Granularity) -> datetime:
    if granularity == "hour":
        return value + timedelta(hours=1)
    if granularity == "day":
        return value + timedelta(days=1)
    if granularity == "week":
        return value + timedelta(weeks=1)
    year = value.year + (1 if value.month == 12 else 0)
    month = 1 if value.month == 12 else value.month + 1
    return value.replace(year=year, month=month, day=1)


def _safe_avg(total: int, requests: int) -> float:
    if requests <= 0:
        return 0.0
    return round(total / requests, 1)


def _aggregate_since(days: int) -> datetime:
    return _floor_bucket(_utc_days_ago(days), "hour")


def _percent_change(*, current: int | float, previous: int | float) -> float | None:
    if previous <= 0:
        return None
    return round(((current - previous) / previous) * 100, 1)


async def _query_summary_window(
    *,
    db: AsyncSession,
    tenant_id: UUID,
    since: datetime,
    until: datetime | None = None,
) -> LLMUsageSummaryResponse:
    filters = [
        LLMUsageHourlyAggregate.tenant_id == tenant_id,
        LLMUsageHourlyAggregate.bucket_start >= since,
    ]
    if until is not None:
        filters.append(LLMUsageHourlyAggregate.bucket_start < until)

    result = await db.execute(
        select(
            func.coalesce(func.sum(LLMUsageHourlyAggregate.requests), 0).label("requests"),
            func.coalesce(func.sum(LLMUsageHourlyAggregate.input_tokens), 0).label("input_tokens"),
            func.coalesce(func.sum(LLMUsageHourlyAggregate.output_tokens), 0).label(
                "output_tokens"
            ),
            func.coalesce(func.sum(LLMUsageHourlyAggregate.total_tokens), 0).label("total_tokens"),
            func.coalesce(func.sum(LLMUsageHourlyAggregate.estimated_cost_usd), 0.0).label(
                "estimated_cost_usd"
            ),
        ).where(*filters)
    )
    row = result.one()
    requests = row.requests or 0
    input_tokens = row.input_tokens or 0
    output_tokens = row.output_tokens or 0
    total_tokens = row.total_tokens or 0
    return LLMUsageSummaryResponse(
        requests=requests,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        estimated_cost_usd=round(float(row.estimated_cost_usd or 0.0), 6),
        avg_input_tokens_per_request=_safe_avg(input_tokens, requests),
        avg_output_tokens_per_request=_safe_avg(output_tokens, requests),
        avg_total_tokens_per_request=_safe_avg(total_tokens, requests),
    )


@router.get("/summary", response_model=LLMUsageSummaryResponse)
async def get_llm_usage_summary(
    days: Annotated[int, Query(ge=1, le=365)] = 30,
    db: AsyncSession = Depends(get_session_flexible),
    tenant_id: UUID = Depends(get_effective_tenant_id),
) -> LLMUsageSummaryResponse:
    since = _aggregate_since(days)
    return await _query_summary_window(
        db=db,
        tenant_id=tenant_id,
        since=since,
    )


@router.get("/comparison", response_model=LLMUsageComparisonResponse)
async def get_llm_usage_comparison(
    days: Annotated[int, Query(ge=1, le=365)] = 30,
    db: AsyncSession = Depends(get_session_flexible),
    tenant_id: UUID = Depends(get_effective_tenant_id),
) -> LLMUsageComparisonResponse:
    current_since = _aggregate_since(days)
    previous_since = current_since - timedelta(days=days)

    current = await _query_summary_window(
        db=db,
        tenant_id=tenant_id,
        since=current_since,
    )
    previous = await _query_summary_window(
        db=db,
        tenant_id=tenant_id,
        since=previous_since,
        until=current_since,
    )
    return LLMUsageComparisonResponse(
        current=current,
        previous=previous,
        requests_change_pct=_percent_change(
            current=current.requests,
            previous=previous.requests,
        ),
        total_tokens_change_pct=_percent_change(
            current=current.total_tokens,
            previous=previous.total_tokens,
        ),
        estimated_cost_change_pct=_percent_change(
            current=current.estimated_cost_usd,
            previous=previous.estimated_cost_usd,
        ),
        avg_output_tokens_change_pct=_percent_change(
            current=current.avg_output_tokens_per_request,
            previous=previous.avg_output_tokens_per_request,
        ),
    )


@router.get("/timeseries", response_model=list[LLMUsageTimeSeriesPoint])
async def get_llm_usage_timeseries(
    days: Annotated[int, Query(ge=1, le=365)] = 30,
    granularity: Granularity = Query(default="day"),
    db: AsyncSession = Depends(get_session_flexible),
    tenant_id: UUID = Depends(get_effective_tenant_id),
) -> list[LLMUsageTimeSeriesPoint]:
    since = _aggregate_since(days)
    bucket_expr = (
        LLMUsageHourlyAggregate.bucket_start
        if granularity == "hour"
        else func.date_trunc(granularity, LLMUsageHourlyAggregate.bucket_start)
    )
    result = await db.execute(
        select(
            bucket_expr.label("bucket_start"),
            func.coalesce(func.sum(LLMUsageHourlyAggregate.requests), 0).label("requests"),
            func.coalesce(func.sum(LLMUsageHourlyAggregate.input_tokens), 0).label("input_tokens"),
            func.coalesce(func.sum(LLMUsageHourlyAggregate.output_tokens), 0).label(
                "output_tokens"
            ),
            func.coalesce(func.sum(LLMUsageHourlyAggregate.total_tokens), 0).label("total_tokens"),
            func.coalesce(func.sum(LLMUsageHourlyAggregate.estimated_cost_usd), 0.0).label(
                "estimated_cost_usd"
            ),
        )
        .where(
            LLMUsageHourlyAggregate.tenant_id == tenant_id,
            LLMUsageHourlyAggregate.bucket_start >= since,
        )
        .group_by(bucket_expr)
        .order_by(bucket_expr.asc())
    )
    rows = result.all()
    data_by_bucket = {
        _floor_bucket(row.bucket_start, granularity): row
        for row in rows
        if row.bucket_start is not None
    }

    points: list[LLMUsageTimeSeriesPoint] = []
    cursor = _floor_bucket(since, granularity)
    end = _floor_bucket(datetime.now(UTC), granularity)
    while cursor <= end:
        row = data_by_bucket.get(cursor)
        points.append(
            LLMUsageTimeSeriesPoint(
                bucket_start=cursor.isoformat(),
                requests=(row.requests or 0) if row else 0,
                input_tokens=(row.input_tokens or 0) if row else 0,
                output_tokens=(row.output_tokens or 0) if row else 0,
                total_tokens=(row.total_tokens or 0) if row else 0,
                estimated_cost_usd=round(float((row.estimated_cost_usd or 0.0) if row else 0.0), 6),
            )
        )
        cursor = _advance_bucket(cursor, granularity)

    return points


@router.get("/breakdown", response_model=list[LLMUsageBreakdownItem])
async def get_llm_usage_breakdown(
    days: Annotated[int, Query(ge=1, le=365)] = 30,
    dimension: BreakdownDimension = Query(default="module"),
    limit: Annotated[int, Query(ge=1, le=20)] = 8,
    db: AsyncSession = Depends(get_session_flexible),
    tenant_id: UUID = Depends(get_effective_tenant_id),
) -> list[LLMUsageBreakdownItem]:
    since = _aggregate_since(days)

    if dimension == "model":
        result = await db.execute(
            select(
                LLMUsageHourlyAggregate.provider.label("provider"),
                LLMUsageHourlyAggregate.model.label("key"),
                func.coalesce(func.sum(LLMUsageHourlyAggregate.requests), 0).label("requests"),
                func.coalesce(func.sum(LLMUsageHourlyAggregate.input_tokens), 0).label(
                    "input_tokens"
                ),
                func.coalesce(func.sum(LLMUsageHourlyAggregate.output_tokens), 0).label(
                    "output_tokens"
                ),
                func.coalesce(func.sum(LLMUsageHourlyAggregate.total_tokens), 0).label(
                    "total_tokens"
                ),
                func.coalesce(func.sum(LLMUsageHourlyAggregate.estimated_cost_usd), 0.0).label(
                    "estimated_cost_usd"
                ),
            )
            .where(
                LLMUsageHourlyAggregate.tenant_id == tenant_id,
                LLMUsageHourlyAggregate.bucket_start >= since,
            )
            .group_by(LLMUsageHourlyAggregate.provider, LLMUsageHourlyAggregate.model)
            .order_by(
                func.sum(LLMUsageHourlyAggregate.estimated_cost_usd).desc(),
                func.sum(LLMUsageHourlyAggregate.total_tokens).desc(),
            )
            .limit(limit)
        )
        return [
            LLMUsageBreakdownItem(
                key=row.key,
                label=f"{row.provider} / {row.key}",
                provider=row.provider,
                requests=row.requests or 0,
                input_tokens=row.input_tokens or 0,
                output_tokens=row.output_tokens or 0,
                total_tokens=row.total_tokens or 0,
                estimated_cost_usd=round(float(row.estimated_cost_usd or 0.0), 6),
            )
            for row in result.all()
        ]

    column = {
        "module": LLMUsageHourlyAggregate.module,
        "task_type": LLMUsageHourlyAggregate.task_type,
        "provider": LLMUsageHourlyAggregate.provider,
        "feature": LLMUsageHourlyAggregate.feature,
    }[dimension]
    result = await db.execute(
        select(
            column.label("key"),
            func.coalesce(func.sum(LLMUsageHourlyAggregate.requests), 0).label("requests"),
            func.coalesce(func.sum(LLMUsageHourlyAggregate.input_tokens), 0).label("input_tokens"),
            func.coalesce(func.sum(LLMUsageHourlyAggregate.output_tokens), 0).label(
                "output_tokens"
            ),
            func.coalesce(func.sum(LLMUsageHourlyAggregate.total_tokens), 0).label("total_tokens"),
            func.coalesce(func.sum(LLMUsageHourlyAggregate.estimated_cost_usd), 0.0).label(
                "estimated_cost_usd"
            ),
        )
        .where(
            LLMUsageHourlyAggregate.tenant_id == tenant_id,
            LLMUsageHourlyAggregate.bucket_start >= since,
        )
        .group_by(column)
        .order_by(
            func.sum(LLMUsageHourlyAggregate.estimated_cost_usd).desc(),
            func.sum(LLMUsageHourlyAggregate.total_tokens).desc(),
        )
        .limit(limit)
    )
    return [
        LLMUsageBreakdownItem(
            key=row.key,
            label=row.key or "Sem feature",
            requests=row.requests or 0,
            input_tokens=row.input_tokens or 0,
            output_tokens=row.output_tokens or 0,
            total_tokens=row.total_tokens or 0,
            estimated_cost_usd=round(float(row.estimated_cost_usd or 0.0), 6),
        )
        for row in result.all()
    ]
