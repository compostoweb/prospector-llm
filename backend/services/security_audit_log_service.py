from __future__ import annotations

import uuid
from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from models.security_audit_log import SecurityAuditLog

_REDACTED = "[REDACTED]"
_SENSITIVE_KEYS = {
    "authorization",
    "api_key",
    "access_token",
    "refresh_token",
    "token",
    "secret",
    "password",
    "grant_code",
    "ticket",
    "code",
    "state",
}


def _normalize_key(key: str) -> str:
    return key.lower().replace("-", "_").replace(" ", "_")


def _sanitize_value(key: str, value: Any) -> Any:
    normalized = _normalize_key(key)
    if normalized in _SENSITIVE_KEYS or normalized.endswith(("_token", "_secret", "_password")):
        return _REDACTED

    if isinstance(value, dict):
        return {
            str(child_key): _sanitize_value(str(child_key), child_value)
            for child_key, child_value in value.items()
        }
    if isinstance(value, list):
        return [_sanitize_value(key, item) for item in value]
    return value


def extract_request_audit_context(request: Request) -> tuple[str | None, str | None]:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        ip_address = forwarded_for.split(",", 1)[0].strip().lower()
    elif request.client and request.client.host:
        ip_address = request.client.host.strip().lower()
    else:
        ip_address = None

    user_agent = request.headers.get("user-agent")
    return ip_address, user_agent


async def record_security_audit_log(
    db: AsyncSession,
    *,
    event_type: str,
    resource_type: str,
    action: str,
    status: str,
    scope_tenant_id: uuid.UUID | None = None,
    actor_user_id: uuid.UUID | None = None,
    resource_id: str | None = None,
    message: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    event_metadata: dict[str, Any] | None = None,
) -> SecurityAuditLog:
    entry = SecurityAuditLog(
        scope_tenant_id=scope_tenant_id,
        actor_user_id=actor_user_id,
        event_type=event_type,
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        status=status,
        message=message,
        ip_address=ip_address,
        user_agent=user_agent[:500] if user_agent else None,
        event_metadata=(
            {
                str(meta_key): _sanitize_value(str(meta_key), meta_value)
                for meta_key, meta_value in event_metadata.items()
            }
            if event_metadata
            else None
        ),
    )
    db.add(entry)
    await db.flush()
    return entry