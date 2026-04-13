from __future__ import annotations

from typing import cast

import pytest
from fastapi import WebSocket

from api.routes import ws as ws_routes

pytestmark = pytest.mark.asyncio


class _FakeWebSocket:
    def __init__(self) -> None:
        self.messages: list[dict] = []

    async def send_json(self, payload: dict) -> None:
        self.messages.append(payload)


async def test_broadcast_event_normalizes_legacy_payload() -> None:
    socket = _FakeWebSocket()
    tenant_id = "tenant-1"
    ws_routes._connections[tenant_id] = {cast(WebSocket, socket)}

    try:
        await ws_routes.broadcast_event(
            tenant_id,
            {
                "type": "new_message",
                "lead_id": "lead-123",
                "channel": "email",
            },
        )
    finally:
        ws_routes._connections.clear()

    assert len(socket.messages) == 1
    payload = socket.messages[0]
    assert payload["type"] == "inbox.new_message"
    assert payload["tenant_id"] == tenant_id
    assert payload["data"] == {"lead_id": "lead-123", "channel": "email"}
    assert isinstance(payload["timestamp"], str)


async def test_broadcast_event_preserves_modern_envelope() -> None:
    socket = _FakeWebSocket()
    tenant_id = "tenant-2"
    timestamp = "2026-04-13T10:00:00+00:00"
    ws_routes._connections[tenant_id] = {cast(WebSocket, socket)}

    try:
        await ws_routes.broadcast_event(
            tenant_id,
            {
                "type": "connection.accepted",
                "data": {"lead_id": "lead-999"},
                "timestamp": timestamp,
            },
        )
    finally:
        ws_routes._connections.clear()

    assert len(socket.messages) == 1
    payload = socket.messages[0]
    assert payload == {
        "type": "connection.accepted",
        "data": {"lead_id": "lead-999"},
        "tenant_id": tenant_id,
        "timestamp": timestamp,
    }
