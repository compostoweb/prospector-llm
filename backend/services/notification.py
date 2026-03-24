"""
services/notification.py

Serviço de notificações por email via Resend.

Responsabilidades:
  - Enviar email de notificação quando lead responde com interesse/objeção
  - Enviar email de tarefa manual ao admin do tenant
  - Respeitar config de notify_on_interest / notify_on_objection do tenant
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import structlog

from core.config import settings

if TYPE_CHECKING:
    from models.lead import Lead
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()


def _get_resend():
    """Importa e configura o Resend SDK. Retorna None se chave não configurada."""
    if not settings.RESEND_API_KEY:
        logger.warning("notification.resend_not_configured")
        return None
    import resend
    resend.api_key = settings.RESEND_API_KEY
    return resend


async def _get_notify_config(tenant_id: uuid.UUID, db: "AsyncSession") -> dict | None:
    """Busca configurações de notificação do tenant."""
    from sqlalchemy import select
    from models.tenant import TenantIntegration

    result = await db.execute(
        select(
            TenantIntegration.notify_email,
            TenantIntegration.notify_on_interest,
            TenantIntegration.notify_on_objection,
        ).where(TenantIntegration.tenant_id == tenant_id)
    )
    row = result.one_or_none()
    if not row or not row.notify_email:
        return None
    return {
        "email": row.notify_email,
        "on_interest": row.notify_on_interest,
        "on_objection": row.notify_on_objection,
    }


async def send_reply_notification(
    lead: "Lead",
    intent: str,
    reply_text: str,
    tenant_id: uuid.UUID,
    db: "AsyncSession",
) -> bool:
    """
    Envia notificação quando um lead responde (interesse ou objeção).
    Retorna True se enviou com sucesso.
    """
    resend = _get_resend()
    if not resend:
        return False

    config = await _get_notify_config(tenant_id, db)
    if not config:
        return False

    notify_email = config["email"]

    # Respeitar preferências do tenant
    if intent == "interest" and not config["on_interest"]:
        return False
    if intent == "objection" and not config["on_objection"]:
        return False

    intent_label = {
        "interest": "🟢 Interesse",
        "objection": "🟡 Objeção",
        "not_interested": "🔴 Não interessado",
        "neutral": "⚪ Neutro",
        "out_of_office": "🔵 Ausente",
    }.get(intent, intent)

    subject = f"[Prospector] {intent_label} — {lead.name}"
    html = f"""
    <div style="font-family: sans-serif; max-width: 600px;">
      <h2 style="color: #1a1a2e;">{intent_label}</h2>
      <p><strong>Lead:</strong> {lead.name}</p>
      <p><strong>Empresa:</strong> {lead.company or "—"}</p>
      <p><strong>Cargo:</strong> {lead.job_title or "—"}</p>
      <hr style="border: none; border-top: 1px solid #eee;" />
      <p style="white-space: pre-wrap; color: #333;">{reply_text}</p>
      <hr style="border: none; border-top: 1px solid #eee;" />
      <p style="font-size: 12px; color: #888;">
        Email enviado automaticamente pelo Prospector.
      </p>
    </div>
    """

    try:
        resend.Emails.send({
            "from": settings.RESEND_FROM_EMAIL,
            "to": [notify_email],
            "subject": subject,
            "html": html,
        })
        logger.info(
            "notification.reply_sent",
            lead_id=str(lead.id),
            intent=intent,
            to=notify_email,
        )
        return True
    except Exception as exc:
        logger.error("notification.reply_failed", error=str(exc))
        return False


async def send_manual_task_notification(
    lead: "Lead",
    cadence_name: str,
    step_number: int,
    message: str,
    tenant_id: uuid.UUID,
    db: "AsyncSession",
) -> bool:
    """
    Envia notificação de tarefa manual ao admin.
    Retorna True se enviou com sucesso.
    """
    resend = _get_resend()
    if not resend:
        return False

    config = await _get_notify_config(tenant_id, db)
    if not config:
        logger.warning("notification.no_notify_email", tenant_id=str(tenant_id))
        return False

    notify_email = config["email"]

    subject = f"[Prospector] Tarefa manual — {lead.name} (Cadência: {cadence_name})"
    html = f"""
    <div style="font-family: sans-serif; max-width: 600px;">
      <h2 style="color: #1a1a2e;">📋 Tarefa Manual</h2>
      <p><strong>Lead:</strong> {lead.name}</p>
      <p><strong>Empresa:</strong> {lead.company or "—"}</p>
      <p><strong>Cadência:</strong> {cadence_name} — Step {step_number}</p>
      <hr style="border: none; border-top: 1px solid #eee;" />
      <p><strong>Instrução:</strong></p>
      <p style="white-space: pre-wrap; color: #333;">{message}</p>
      <hr style="border: none; border-top: 1px solid #eee;" />
      <p style="font-size: 12px; color: #888;">
        Email enviado automaticamente pelo Prospector.
      </p>
    </div>
    """

    try:
        resend.Emails.send({
            "from": settings.RESEND_FROM_EMAIL,
            "to": [notify_email],
            "subject": subject,
            "html": html,
        })
        logger.info(
            "notification.manual_task_sent",
            lead_id=str(lead.id),
            cadence=cadence_name,
            step=step_number,
            to=notify_email,
        )
        return True
    except Exception as exc:
        logger.error("notification.manual_task_failed", error=str(exc))
        return False
