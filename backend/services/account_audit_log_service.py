"""
services/account_audit_log_service.py

Helpers para registrar eventos operacionais de contas conectadas.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from models.account_audit_log import AccountAuditLog


async def record_account_audit_log(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    account_type: str,
    event_type: str,
    account_id: uuid.UUID | None = None,
    external_account_id: str | None = None,
    provider_type: str | None = None,
    actor_user_id: uuid.UUID | None = None,
    provider_status: str | None = None,
    message: str | None = None,
    event_metadata: dict[str, Any] | None = None,
) -> AccountAuditLog:
    entry = AccountAuditLog(
        tenant_id=tenant_id,
        account_type=account_type,
        account_id=account_id,
        external_account_id=external_account_id,
        provider_type=provider_type,
        event_type=event_type,
        actor_user_id=actor_user_id,
        provider_status=provider_status,
        message=message,
        event_metadata=event_metadata,
    )
    db.add(entry)
    await db.flush()
    return entry
