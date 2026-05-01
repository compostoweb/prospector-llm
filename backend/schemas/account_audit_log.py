"""
schemas/account_audit_log.py

Schemas da trilha operacional de contas conectadas.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AccountAuditLogResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    account_type: str
    account_id: uuid.UUID | None = None
    external_account_id: str | None = None
    provider_type: str | None = None
    event_type: str
    actor_user_id: uuid.UUID | None = None
    provider_status: str | None = None
    message: str | None = None
    event_metadata: dict[str, object] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AccountAuditLogListResponse(BaseModel):
    items: list[AccountAuditLogResponse] = Field(default_factory=list)
    total: int = 0
