from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SecurityAuditLogResponse(BaseModel):
    id: uuid.UUID
    scope_tenant_id: uuid.UUID | None = None
    actor_user_id: uuid.UUID | None = None
    event_type: str
    resource_type: str
    resource_id: str | None = None
    action: str
    status: str
    message: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    event_metadata: dict[str, object] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SecurityAuditLogListResponse(BaseModel):
    items: list[SecurityAuditLogResponse] = Field(default_factory=list)
    total: int = 0