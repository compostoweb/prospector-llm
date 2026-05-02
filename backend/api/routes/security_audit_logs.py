from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import AsyncSessionLocal
from core.security import UserPayload, get_current_user_payload
from models.security_audit_log import SecurityAuditLog
from schemas.security_audit_log import SecurityAuditLogListResponse, SecurityAuditLogResponse

router = APIRouter(prefix="/security-audit-logs", tags=["Security Audit Logs"])


async def _get_raw_session():  # type: ignore[return]
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


@router.get("", response_model=SecurityAuditLogListResponse)
async def list_security_audit_logs(
    user: UserPayload = Depends(get_current_user_payload),
    scope_tenant_id: Annotated[uuid.UUID | None, Query()] = None,
    event_type: Annotated[str | None, Query(max_length=120)] = None,
    resource_type: Annotated[str | None, Query(max_length=80)] = None,
    status_filter: Annotated[str | None, Query(alias="status", max_length=30)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: AsyncSession = Depends(_get_raw_session),
) -> SecurityAuditLogListResponse:
    effective_scope_tenant_id = scope_tenant_id
    if not user.is_superuser:
        if user.tenant_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario sem tenant ativo para consultar trilha de auditoria.",
            )
        effective_scope_tenant_id = user.tenant_id

    filters = []
    if effective_scope_tenant_id is not None:
        filters.append(SecurityAuditLog.scope_tenant_id == effective_scope_tenant_id)
    if event_type:
        filters.append(SecurityAuditLog.event_type == event_type)
    if resource_type:
        filters.append(SecurityAuditLog.resource_type == resource_type)
    if status_filter:
        filters.append(SecurityAuditLog.status == status_filter)

    total_result = await db.execute(select(func.count(SecurityAuditLog.id)).where(*filters))
    total = int(total_result.scalar_one() or 0)

    result = await db.execute(
        select(SecurityAuditLog)
        .where(*filters)
        .order_by(SecurityAuditLog.created_at.desc(), SecurityAuditLog.id.desc())
        .offset(offset)
        .limit(limit)
    )
    items = [SecurityAuditLogResponse.model_validate(item) for item in result.scalars().all()]
    return SecurityAuditLogListResponse(items=items, total=total)