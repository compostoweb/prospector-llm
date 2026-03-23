"""
api/routes/ws.py

WebSocket endpoint para eventos em tempo real.

Aceita conexão autenticada via token JWT no query param.
Mantém a conexão aberta com pings periódicos.
Eventos são publicados via Redis pub/sub (implementação futura).

NOTA DE SEGURANÇA — Token no query param:
  Browsers não permitem headers customizados (Authorization) em WebSocket.
  Por isso o JWT é enviado via ?token=. Mitigações adotadas:
    1. Tokens JWT têm expiração curta (minutos)
    2. Token é validado ANTES de aceitar a conexão (rejeita 1008)
    3. Em produção, a conexão é sobre WSS (TLS) — param não vaza em rede
  Alternativa futura: usar cookie httpOnly ou ticket endpoint de uso único.
"""

from __future__ import annotations

import asyncio

import structlog
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from core.security import decode_token

logger = structlog.get_logger()

router = APIRouter()

PING_INTERVAL = 30  # segundos


@router.websocket("/ws/events")
async def ws_events(
    websocket: WebSocket,
    token: str = Query(...),
) -> None:
    """
    WebSocket autenticado para push de eventos em tempo real.
    O token JWT é validado antes de aceitar a conexão.
    """
    # Validar token antes de aceitar
    try:
        payload = decode_token(token)
        if payload.get("type") != "user" and not payload.get("tenant_id"):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

    user_id = payload.get("user_id") or payload.get("tenant_id")
    logger.info("ws.connected", user_id=user_id)

    try:
        while True:
            # Envia ping para manter conexão viva
            await websocket.send_json({"type": "ping"})
            await asyncio.sleep(PING_INTERVAL)
    except WebSocketDisconnect:
        logger.info("ws.disconnected", user_id=user_id)
    except Exception:
        logger.debug("ws.closed", user_id=user_id)
