"""
api/routes/email_tracking.py

Rotas PÚBLICAS de rastreamento de e-mail (sem autenticação JWT).

Endpoints:
  GET /track/open/{interaction_id}
      — Marca a interação como aberta, retorna pixel GIF 1×1 transparente.

  GET /track/unsubscribe/{token}
      — Valida o token HMAC, registra descadastro, retorna HTML de confirmação.
"""

from __future__ import annotations

import urllib.parse
import uuid

import structlog
from fastapi import APIRouter, BackgroundTasks, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import AsyncSessionLocal
from models.email_unsubscribe import EmailUnsubscribe
from models.interaction import Interaction
from services.email_footer import TRANSPARENT_GIF_BYTES, verify_unsubscribe_token

logger = structlog.get_logger()

router = APIRouter(prefix="/track", tags=["Email Tracking"])


# ── Helpers de DB (sem RLS — acesso público autenticado por UUID/HMAC) ─

async def _mark_opened(interaction_id: uuid.UUID) -> None:
    """Background task: marca a interaction como aberta se ainda não estava."""
    from datetime import datetime, timezone

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(Interaction).where(Interaction.id == interaction_id)
            )
            interaction = result.scalar_one_or_none()
            if interaction and not interaction.opened:
                interaction.opened = True
                interaction.opened_at = datetime.now(timezone.utc)
                await db.commit()
                logger.info(
                    "email.opened",
                    interaction_id=str(interaction_id),
                    lead_id=str(interaction.lead_id),
                )
        except Exception as exc:
            logger.error("email.open_tracking_error", error=str(exc), interaction_id=str(interaction_id))
            await db.rollback()


async def _record_unsubscribe(tenant_id: uuid.UUID, email: str) -> None:
    """Background task: insere registro de unsubscribe (idempotente)."""
    async with AsyncSessionLocal() as db:
        try:
            # Verifica se já descadastrado
            existing = await db.execute(
                select(EmailUnsubscribe).where(
                    EmailUnsubscribe.tenant_id == tenant_id,
                    EmailUnsubscribe.email == email.lower(),
                )
            )
            if existing.scalar_one_or_none() is None:
                db.add(EmailUnsubscribe(
                    tenant_id=tenant_id,
                    email=email.lower(),
                ))
                await db.commit()
                logger.info("email.unsubscribed", tenant_id=str(tenant_id), email=email)
        except Exception as exc:
            logger.error("email.unsubscribe_error", error=str(exc))
            await db.rollback()


# ── Pixel de abertura ─────────────────────────────────────────────────

@router.get(
    "/open/{interaction_id}",
    summary="Tracking pixel de abertura de e-mail",
    response_class=Response,
    include_in_schema=False,
)
async def track_open(
    interaction_id: uuid.UUID,
    background_tasks: BackgroundTasks,
) -> Response:
    """
    Retorna imagem GIF 1×1 transparente e registra abertura em background.
    Rota pública — sem autenticação JWT.
    """
    background_tasks.add_task(_mark_opened, interaction_id)
    return Response(
        content=TRANSPARENT_GIF_BYTES,
        media_type="image/gif",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


# ── Unsubscribe ───────────────────────────────────────────────────────

@router.get(
    "/unsubscribe/{token}",
    summary="Descadastro de lista de e-mail",
    response_class=Response,
    include_in_schema=False,
)
async def track_unsubscribe(
    token: str,
    background_tasks: BackgroundTasks,
    e: str = Query(..., description="E-mail codificado em URL"),
    t: uuid.UUID = Query(..., description="Tenant ID"),
) -> Response:
    """
    Valida o token HMAC-SHA256 e registra o descadastro.
    Retorna página HTML de confirmação.
    Rota pública — sem autenticação JWT.
    """
    email = urllib.parse.unquote(e).lower().strip()

    if not verify_unsubscribe_token(token, t, email):
        return Response(
            content=_UNSUB_INVALID_HTML,
            media_type="text/html; charset=utf-8",
            status_code=400,
        )

    background_tasks.add_task(_record_unsubscribe, t, email)

    html = _UNSUB_SUCCESS_HTML.replace("{{email}}", email)
    return Response(content=html, media_type="text/html; charset=utf-8")


# ── Templates HTML de resposta ────────────────────────────────────────

_UNSUB_SUCCESS_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Descadastro confirmado</title>
<style>
  body{font-family:Arial,sans-serif;background:#f9fafb;display:flex;align-items:center;
       justify-content:center;min-height:100vh;margin:0}
  .card{background:#fff;border-radius:12px;padding:48px 40px;max-width:480px;
        text-align:center;box-shadow:0 1px 3px rgba(0,0,0,.1)}
  h1{color:#111827;font-size:22px;margin-bottom:12px}
  p{color:#6b7280;font-size:15px;line-height:1.6;margin:0}
  .email{font-weight:600;color:#374151}
</style></head>
<body>
<div class="card">
  <h1>✅ Descadastro confirmado</h1>
  <p>O endereço <span class="email">{{email}}</span> foi removido da nossa lista.<br>
  Você não receberá mais e-mails de prospecção.</p>
</div>
</body></html>"""

_UNSUB_INVALID_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><title>Link inválido</title>
<style>
  body{font-family:Arial,sans-serif;background:#f9fafb;display:flex;align-items:center;
       justify-content:center;min-height:100vh;margin:0}
  .card{background:#fff;border-radius:12px;padding:48px 40px;max-width:480px;
        text-align:center;box-shadow:0 1px 3px rgba(0,0,0,.1)}
  h1{color:#dc2626;font-size:22px;margin-bottom:12px}
  p{color:#6b7280;font-size:15px;margin:0}
</style></head>
<body>
<div class="card">
  <h1>Link inválido ou expirado</h1>
  <p>Este link de descadastro não é válido.<br>
  Se precisar de ajuda, entre em contato conosco.</p>
</div>
</body></html>"""
