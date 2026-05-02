"""
api/routes/ws.py

WebSocket endpoint para eventos em tempo real.

Aceita conexão autenticada preferencialmente via ticket curto single-use no query param.
Mantém compatibilidade temporária com JWT em `token`, mas o frontend principal deve
usar `ticket` emitido pelo backend para evitar expor JWT longo em URL.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from core.redis_client import redis_client
from core.security import decode_token

logger = structlog.get_logger()

router = APIRouter()

PING_INTERVAL = 30  # segundos

_EVENT_TYPE_ALIASES = {
    "new_message": "inbox.new_message",
    "connection_accepted": "connection.accepted",
}

# Registry de conexões ativas — {tenant_id: set of websockets}
_connections: dict[str, set[WebSocket]] = {}
_WS_TICKET_PREFIX = "ws_auth_ticket:"


async def broadcast_event(tenant_id: str, event: dict[str, Any]) -> None:
    """Envia evento normalizado para todos os WebSockets do tenant."""
    sockets = _connections.get(tenant_id, set())
    dead: set[WebSocket] = set()
    payload = _normalize_event_payload(tenant_id, event)
    for ws in sockets:
        try:
            await ws.send_json(payload)
        except Exception:
            dead.add(ws)
    sockets -= dead


async def broadcast_all_tenants(event: dict[str, Any]) -> None:
    """Envia evento para todos os tenants conectados (usado quando não há tenant_id no payload)."""
    for tenant_id in list(_connections.keys()):
        await broadcast_event(tenant_id, event)


def _normalize_event_payload(tenant_id: str, event: dict[str, Any]) -> dict[str, Any]:
    """
    Mantém compatibilidade com emissores legados e entrega o envelope esperado
    pelo frontend: {type, data, tenant_id, timestamp}.
    """
    event_type = str(event.get("type") or "").strip()
    normalized_type = _EVENT_TYPE_ALIASES.get(event_type, event_type)

    if "data" in event and isinstance(event.get("data"), dict):
        data = dict(event["data"])
    else:
        data = {
            key: value
            for key, value in event.items()
            if key not in {"type", "tenant_id", "timestamp"}
        }

    return {
        "type": normalized_type,
        "data": data,
        "tenant_id": tenant_id,
        "timestamp": str(event.get("timestamp") or datetime.now(tz=UTC).isoformat()),
    }


@router.websocket("/ws/events")
async def ws_events(
    websocket: WebSocket,
    ticket: str | None = Query(default=None),
    token: str | None = Query(default=None),
) -> None:
    """
    WebSocket autenticado para push de eventos em tempo real.
    O ticket curto é validado antes de aceitar a conexão.
    """
    try:
        if ticket:
            raw_ticket = await redis_client.get(f"{_WS_TICKET_PREFIX}{ticket}")
            if not raw_ticket:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return
            await redis_client.delete(f"{_WS_TICKET_PREFIX}{ticket}")
            payload = json.loads(raw_ticket)
        elif token:
            payload = decode_token(token)
        else:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        if payload.get("type") != "user" and not payload.get("tenant_id"):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

    user_id = payload.get("user_id") or payload.get("tenant_id")
    tenant_id = str(payload.get("tenant_id", ""))

    # Registra conexão
    if tenant_id not in _connections:
        _connections[tenant_id] = set()
    _connections[tenant_id].add(websocket)

    logger.info("ws.connected", user_id=user_id, tenant_id=tenant_id)

    try:
        while True:
            # Envia ping para manter conexão viva
            await websocket.send_json({"type": "ping"})
            await asyncio.sleep(PING_INTERVAL)
    except WebSocketDisconnect:
        logger.info("ws.disconnected", user_id=user_id)
    except Exception:
        logger.debug("ws.closed", user_id=user_id)
    finally:
        # Remove conexão
        if tenant_id in _connections:
            _connections[tenant_id].discard(websocket)
            if not _connections[tenant_id]:
                del _connections[tenant_id]
