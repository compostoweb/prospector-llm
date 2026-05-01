"""
api/routes/account_audit_logs.py

Consulta da trilha operacional de contas conectadas.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_effective_tenant_id, get_session_flexible
from models.account_audit_log import AccountAuditLog
from schemas.account_audit_log import AccountAuditLogListResponse, AccountAuditLogResponse

router = APIRouter(prefix="/account-audit-logs", tags=["Account Audit Logs"])


@router.get("", response_model=AccountAuditLogListResponse)
async def list_account_audit_logs(
    account_type: Annotated[str | None, Query(max_length=30)] = None,
    account_id: Annotated[uuid.UUID | None, Query()] = None,
    event_type: Annotated[str | None, Query(max_length=80)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: AsyncSession = Depends(get_session_flexible),
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
) -> AccountAuditLogListResponse:
    filters = [AccountAuditLog.tenant_id == tenant_id]
    if account_type:
        filters.append(AccountAuditLog.account_type == account_type)
    if account_id:
        filters.append(AccountAuditLog.account_id == account_id)
    if event_type:
        filters.append(AccountAuditLog.event_type == event_type)

    total_result = await db.execute(select(func.count(AccountAuditLog.id)).where(*filters))
    total = int(total_result.scalar_one() or 0)

    result = await db.execute(
        select(AccountAuditLog)
        .where(*filters)
        .order_by(AccountAuditLog.created_at.desc(), AccountAuditLog.id.desc())
        .offset(offset)
        .limit(limit)
    )
    items = [AccountAuditLogResponse.model_validate(item) for item in result.scalars().all()]
    return AccountAuditLogListResponse(items=items, total=total)
