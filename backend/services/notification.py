"""
services/notification.py

Serviço de notificações por email via Resend.

Responsabilidades:
  - Enviar email de notificação quando lead responde com interesse/objeção
  - Enviar email de tarefa manual ao admin do tenant
    - Enviar email com PDF do diagnóstico da calculadora ao lead
  - Respeitar config de notify_on_interest / notify_on_objection do tenant
"""

from __future__ import annotations

import base64
import html
import importlib
import re
import uuid
from typing import TYPE_CHECKING, Any, TypedDict, cast

import structlog

from core.branding import (
    COMPOSTO_WEB_ACCENT,
    COMPOSTO_WEB_PRIMARY,
    COMPOSTO_WEB_SECONDARY,
    COMPOSTO_WEB_SURFACE,
    COMPOSTO_WEB_TEXT,
    COMPOSTO_WEB_WHITE,
    load_composto_web_logo_primary_white_bg_bytes,
)
from core.config import settings
from services.content.calculator_report import (
    build_calculator_diagnosis_pdf,
    build_context_summary,
    build_executive_summary,
    build_next_step_recommendation,
    format_brl,
    format_months,
    format_percent,
    get_company_size_label,
    get_process_area_label,
    get_process_label,
    get_role_label,
    get_segment_label,
)

_EXECUTIVE_HIGHLIGHT_RE = re.compile(
    r"(R\$ [\d\.\,]+/ano|retorno estimado de\s+|\d[\d\.\,]*%|\d[\d\.\,]* meses?)",
    flags=re.IGNORECASE,
)
_HIGHLIGHT_DANGER = "#B42318"
_HIGHLIGHT_SUCCESS = "#067647"


def _build_executive_highlight_html(text: str) -> str:
    """Divide o texto da leitura executiva em spans coloridos, igual ao PDF."""
    parts: list[str] = []
    for chunk in _EXECUTIVE_HIGHLIGHT_RE.split(text):
        if not chunk:
            continue
        if _EXECUTIVE_HIGHLIGHT_RE.fullmatch(chunk):
            normalized = chunk.strip().lower()
            color = _HIGHLIGHT_SUCCESS if not normalized.startswith("r$") else _HIGHLIGHT_DANGER
            escaped = html.escape(chunk)
            parts.append(f'<span style="color: {color}; font-weight: 700;">{escaped}</span>')
        else:
            parts.append(html.escape(chunk))
    return "".join(parts)


if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from models.content_calculator_result import ContentCalculatorResult
    from models.content_lead_magnet import ContentLeadMagnet
    from models.content_lm_lead import ContentLMLead
    from models.lead import Lead

logger = structlog.get_logger()


class NotifyConfig(TypedDict):
    email: str
    on_interest: bool
    on_objection: bool


class CalculatorDiagnosisEmailPayload(TypedDict):
    recipient_email: str
    subject: str
    html: str
    attachments: list[dict[str, str]]
    reply_to: str | None


def _get_resend() -> Any | None:
    """Importa e configura o Resend SDK. Retorna None se chave não configurada."""
    if not settings.RESEND_API_KEY:
        logger.warning("notification.resend_not_configured")
        return None

    try:
        resend = cast(Any, importlib.import_module("resend"))
    except ModuleNotFoundError:
        logger.warning("notification.resend_sdk_missing")
        return None
    resend.api_key = settings.RESEND_API_KEY
    return resend


def _escape_value(value: object | None) -> str:
    if value is None:
        return "—"
    text = str(value).strip()
    if not text:
        return "—"
    return html.escape(text)


def _format_brl(value: object | None) -> str:
    return format_brl(value)


def _format_percent(value: object | None) -> str:
    return format_percent(value)


def _format_months(value: object | None) -> str:
    return format_months(value)


def _format_bool_ptbr(value: bool | None) -> str:
    if value is None:
        return "—"
    return "Sim" if value else "Não"


def _build_rows(rows: list[tuple[str, str]]) -> str:
    return "".join(
        f"""
        <tr>
                    <td style=\"padding: 12px 0; width: 208px; vertical-align: middle; color: {COMPOSTO_WEB_PRIMARY}; border-bottom: 1px solid #e4eaf4;\"><strong>{html.escape(label)}</strong></td>
                    <td style=\"padding: 12px 0; vertical-align: middle; color: {COMPOSTO_WEB_TEXT}; border-bottom: 1px solid #e4eaf4;\">{value}</td>
        </tr>
        """
        for label, value in rows
    )


def _build_metric_grid(cards: list[tuple[str, str]]) -> str:
    rows_html: list[str] = []
    for index in range(0, len(cards), 2):
        chunk = cards[index : index + 2]
        cells: list[str] = []
        for cell_index, (label, value) in enumerate(chunk):
            padding = "0 8px 14px 0" if cell_index == 0 else "0 0 14px 8px"
            safe_value = value.replace("R$ ", "R$\u00a0")
            cells.append(
                f"""
                <td width=\"50%\" style=\"padding: {padding}; vertical-align: top;\">
                  <table role=\"presentation\" width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" style=\"border-collapse: separate; border: 1px solid #d9dfeb; border-radius: 18px; background: {COMPOSTO_WEB_WHITE};\">
                    <tr>
                                            <td style=\"padding: 20px 20px 18px; vertical-align: middle;\">
                        <div style=\"width: 44px; height: 4px; border-radius: 999px; background: {COMPOSTO_WEB_ACCENT};\"></div>
                        <div style=\"margin-top: 12px; font-size: 12px; line-height: 1.4; color: {COMPOSTO_WEB_SECONDARY}; text-transform: uppercase; letter-spacing: 0.06em; font-weight: 700;\">{html.escape(label)}</div>
                                                <div style=\"margin-top: 10px; font-size: 20px; line-height: 1.3; color: {COMPOSTO_WEB_PRIMARY}; font-weight: 700;\">{safe_value}</div>
                      </td>
                    </tr>
                  </table>
                </td>
                """
            )
        if len(chunk) == 1:
            cells.append('<td width="50%" style="padding: 0 0 14px 8px;">&nbsp;</td>')
        rows_html.append(f"<tr>{''.join(cells)}</tr>")

    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'style="border-collapse: collapse;">' + "".join(rows_html) + "</table>"
    )


def _build_badges(values: list[str]) -> str:
    items = [
        value for value in values if value and value != "—" and value != "Escopo não informado"
    ]
    return "".join(
        (
            '<span style="display: inline-block; margin: 0 8px 8px 0; padding: 8px 12px; '
            f"border-radius: 999px; background: {COMPOSTO_WEB_SURFACE}; color: {COMPOSTO_WEB_PRIMARY}; border: 1px solid #d9dfeb; font-size: 12px; "
            'line-height: 1; font-weight: 700;">'
            f"{html.escape(item)}</span>"
        )
        for item in items
    )


def _build_email_button(label: str, href: str) -> str:
    return (
        f'<a href="{html.escape(href, quote=True)}" '
        'style="display: inline-block; padding: 14px 18px; border-radius: 999px; '
        f"background: {COMPOSTO_WEB_SECONDARY}; color: {COMPOSTO_WEB_WHITE}; text-decoration: none; font-size: 14px; "
        'font-weight: 700;">'
        f"{html.escape(label)}</a>"
    )


async def _get_notify_config(tenant_id: uuid.UUID, db: AsyncSession) -> NotifyConfig | None:
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
        "email": str(row.notify_email),
        "on_interest": bool(row.notify_on_interest),
        "on_objection": bool(row.notify_on_objection),
    }


async def _resolve_reply_notification_recipient(
    *,
    tenant_id: uuid.UUID,
    db: AsyncSession,
    replied_step: Any | None,
) -> str | None:
    """Prefere a caixa remetente da cadência para replies de email; fallback para notify_email."""
    if replied_step is None:
        return None

    from sqlalchemy import select

    from models.cadence import Cadence
    from models.email_account import EmailAccount
    from models.enums import Channel

    if replied_step.channel != Channel.EMAIL:
        return None

    result = await db.execute(
        select(EmailAccount.email_address)
        .join(Cadence, Cadence.email_account_id == EmailAccount.id)
        .where(
            Cadence.id == replied_step.cadence_id,
            Cadence.tenant_id == tenant_id,
            EmailAccount.tenant_id == tenant_id,
            EmailAccount.is_active == True,  # noqa: E712
        )
        .limit(1)
    )
    recipient = result.scalar_one_or_none()
    if recipient is None:
        return None
    return str(recipient)


async def send_calculator_submission_notification(
    *,
    result: ContentCalculatorResult,
    lead_magnet_title: str | None = None,
    lm_lead_id: uuid.UUID | None = None,
    sendpulse_sync_status: str | None = None,
    diagnosis_email_sent: bool | None = None,
) -> bool:
    """Envia um resumo comercial da submissão final da calculadora pública."""
    resend = _get_resend()
    if not resend:
        return False

    notify_email = settings.CONTENT_CALCULATOR_NOTIFY_EMAIL.strip()
    if not notify_email:
        logger.warning("notification.calculator_notify_email_missing")
        return False

    subject_ref = result.name or result.email or str(result.id)
    subject = f"[Composto Web] Nova submissão da calculadora — {subject_ref}"
    contact_rows = [
        ("Nome", _escape_value(result.name)),
        ("E-mail", _escape_value(result.email)),
        ("Empresa", _escape_value(result.company)),
        ("Cargo", _escape_value(result.role)),
        ("WhatsApp", _escape_value(result.phone)),
    ]
    process_rows = [
        ("Tipo de processo", _escape_value(result.tipo_processo)),
        ("Cargo do processo", _escape_value(result.cargo)),
        ("Segmento da empresa", _escape_value(result.company_segment)),
        ("Porte da empresa", _escape_value(result.company_size)),
        ("Áreas no processo", _escape_value(result.process_area_span)),
        ("Pessoas envolvidas", _escape_value(result.pessoas)),
        ("Horas por semana", _escape_value(result.horas_semana)),
        ("Retrabalho", _format_percent(result.retrabalho_pct)),
    ]
    metrics_rows = [
        ("Custo anual", _format_brl(result.custo_anual)),
        (
            "Faixa de investimento",
            f"{_format_brl(result.investimento_estimado_min)} a {_format_brl(result.investimento_estimado_max)}",
        ),
        ("ROI estimado", _format_percent(result.roi_estimado)),
        ("Payback", _format_months(result.payback_meses)),
    ]
    operational_rows = [
        ("Lead magnet vinculado", _escape_value(lead_magnet_title)),
        ("lead_id", _escape_value(result.lead_id)),
        ("lm_lead_id", _escape_value(lm_lead_id)),
        ("sendpulse_sync_status", _escape_value(sendpulse_sync_status)),
        ("diagnóstico enviado ao lead", _format_bool_ptbr(diagnosis_email_sent)),
        ("result_id", _escape_value(result.id)),
    ]

    html_body = f"""
    <div style=\"font-family: Arial, sans-serif; max-width: 720px; color: #101828;\">
      <h2 style=\"margin-bottom: 8px;\">Nova submissão da calculadora pública</h2>
      <p style=\"margin-top: 0; color: #475467;\">
        Um visitante enviou o formulário final da calculadora de ROI e abriu o próximo passo comercial.
      </p>

      <section style=\"margin-top: 24px;\">
        <h3 style=\"margin-bottom: 8px;\">Contato</h3>
        <table style=\"width: 100%; border-collapse: collapse;\">{_build_rows(contact_rows)}</table>
      </section>

      <section style=\"margin-top: 24px;\">
        <h3 style=\"margin-bottom: 8px;\">Processo analisado</h3>
        <table style=\"width: 100%; border-collapse: collapse;\">{_build_rows(process_rows)}</table>
      </section>

      <section style=\"margin-top: 24px;\">
        <h3 style=\"margin-bottom: 8px;\">Resultado financeiro</h3>
        <table style=\"width: 100%; border-collapse: collapse;\">{_build_rows(metrics_rows)}</table>
      </section>

      <section style=\"margin-top: 24px;\">
        <h3 style=\"margin-bottom: 8px;\">Contexto operacional</h3>
        <table style=\"width: 100%; border-collapse: collapse;\">{_build_rows(operational_rows)}</table>
      </section>

      <p style=\"margin-top: 24px; font-size: 12px; color: #667085;\">
          Notificação operacional enviada pela Composto Web.
      </p>
    </div>
    """

    try:
        resend.Emails.send(
            {
                "from": settings.CONTENT_CALCULATOR_NOTIFY_FROM_EMAIL or settings.RESEND_FROM_EMAIL,
                "to": [notify_email],
                "subject": subject,
                "html": html_body,
            }
        )
        logger.info(
            "notification.calculator_submission_sent",
            result_id=str(result.id),
            lead_id=str(result.lead_id) if result.lead_id else None,
            lm_lead_id=str(lm_lead_id) if lm_lead_id else None,
            to=notify_email,
        )
        return True
    except Exception as exc:
        logger.error(
            "notification.calculator_submission_failed",
            result_id=str(result.id),
            error=str(exc),
        )
        return False


async def send_calculator_diagnosis_email(
    *,
    result: ContentCalculatorResult,
    lead_magnet_title: str | None = None,
) -> bool:
    """Envia ao lead o diagnóstico da calculadora com PDF em anexo."""
    resend = _get_resend()
    if not resend:
        return False

    recipient_email = (result.email or "").strip().lower()
    if not recipient_email:
        logger.warning(
            "notification.calculator_diagnosis_missing_recipient",
            result_id=str(result.id),
        )
        return False

    try:
        filename, pdf_bytes = build_calculator_diagnosis_pdf(
            result,
            lead_magnet_title=lead_magnet_title,
        )
    except Exception as exc:
        logger.error(
            "notification.calculator_diagnosis_pdf_failed",
            result_id=str(result.id),
            error=str(exc),
        )
        return False

    built_payload = build_calculator_diagnosis_email_payload(
        result=result,
        lead_magnet_title=lead_magnet_title,
        filename=filename,
        pdf_bytes=pdf_bytes,
    )

    payload: dict[str, object] = {
        "from": settings.CONTENT_CALCULATOR_NOTIFY_FROM_EMAIL or settings.RESEND_FROM_EMAIL,
        "to": [built_payload["recipient_email"]],
        "subject": built_payload["subject"],
        "html": built_payload["html"],
        "attachments": built_payload["attachments"],
    }
    if built_payload["reply_to"]:
        payload["reply_to"] = built_payload["reply_to"]

    try:
        resend.Emails.send(payload)
        logger.info(
            "notification.calculator_diagnosis_sent",
            result_id=str(result.id),
            lead_id=str(result.lead_id) if result.lead_id else None,
            to=recipient_email,
        )
        return True
    except Exception as exc:
        logger.error(
            "notification.calculator_diagnosis_failed",
            result_id=str(result.id),
            error=str(exc),
        )
        return False


def build_calculator_diagnosis_email_payload(
    *,
    result: ContentCalculatorResult,
    lead_magnet_title: str | None = None,
    filename: str,
    pdf_bytes: bytes,
) -> CalculatorDiagnosisEmailPayload:
    recipient_email = (result.email or "").strip().lower()
    contact_name = (result.name or "").strip() or "Olá"
    subject_ref = result.company or result.name or get_process_label(result.tipo_processo)
    segment_label = get_segment_label(result.company_segment)
    company_size_label = get_company_size_label(result.company_size)
    area_label = get_process_area_label(result.process_area_span)
    process_label = get_process_label(result.tipo_processo)
    role_label = get_role_label(result.cargo)
    context_summary = build_context_summary(result)
    executive_summary = build_executive_summary(result)
    next_step = build_next_step_recommendation(result)
    reply_to = settings.CONTENT_CALCULATOR_REPLY_TO_EMAIL.strip() or None
    related_material = _escape_value(lead_magnet_title) or "Diagnóstico da calculadora pública"
    metrics_grid = _build_metric_grid(
        [
            ("Custo anual estimado", _format_brl(result.custo_anual)),
            (
                "Faixa de investimento",
                f"{_format_brl(result.investimento_estimado_min)} a {_format_brl(result.investimento_estimado_max)}",
            ),
            ("ROI estimado", _format_percent(result.roi_estimado)),
            ("Payback", _format_months(result.payback_meses)),
        ]
    )
    badges = _build_badges([process_label, segment_label, company_size_label, area_label])
    reply_cta = ""

    attachments: list[dict[str, str]] = [
        {
            "filename": filename,
            "content": base64.b64encode(pdf_bytes).decode("ascii"),
            "contentType": "application/pdf",
        }
    ]
    logo_markup = f'<div style="font-size: 22px; line-height: 1; color: {COMPOSTO_WEB_PRIMARY}; font-weight: 800; letter-spacing: 0.03em;">COMPOSTO WEB</div>'
    logo_bytes = load_composto_web_logo_primary_white_bg_bytes()
    if logo_bytes:
        if settings.COMPOSTO_WEB_LOGO_EMAIL_URL:
            logo_src: str = settings.COMPOSTO_WEB_LOGO_EMAIL_URL
        else:
            _api_url = settings.API_PUBLIC_URL.rstrip("/")
            _is_local = "localhost" in _api_url or "127.0.0.1" in _api_url
            if _is_local:
                logo_src = f"data:image/webp;base64,{base64.b64encode(logo_bytes).decode('ascii')}"
            else:
                logo_src = f"{_api_url}/assets/branding/compostoweb-logo-primary-transparent.webp"
        logo_markup = (
            f'<img src="{logo_src}" alt="Composto Web" width="220" '
            'style="display: block; width: 220px; max-width: 100%; height: auto;" />'
        )

    context_rows = _build_rows(
        [
            ("Tipo de processo", html.escape(process_label)),
            ("Cargo predominante", html.escape(role_label)),
            ("Segmento", html.escape(segment_label)),
            ("Porte", html.escape(company_size_label)),
            ("Áreas no fluxo", html.escape(area_label)),
            ("Material relacionado", related_material),
        ]
    )

    html_body = f"""
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse; background: {COMPOSTO_WEB_SURFACE}; margin: 0; font-family: Arial, sans-serif;">
      <tr>
        <td align="center" style="padding: 28px 16px;">
                    <table role="presentation" width="760" cellpadding="0" cellspacing="0" style="width: 100%; max-width: 760px; border-collapse: separate; border-spacing: 0; background: {COMPOSTO_WEB_WHITE}; border: 1px solid #d9dfeb; border-radius: 26px; overflow: hidden;">
            <tr>
              <td style="padding: 0; background: {COMPOSTO_WEB_WHITE};">
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse: collapse;">
                  <tr>
                    <td style="padding: 0; height: 6px; background: {COMPOSTO_WEB_ACCENT};"></td>
                  </tr>
                  <tr>
                                        <td style="padding: 30px 38px 10px;">
                      {logo_markup}
                                            <div style="display: inline-block; margin-top: 18px; padding: 8px 14px; border-radius: 999px; background: {COMPOSTO_WEB_SURFACE}; color: {COMPOSTO_WEB_SECONDARY}; font-size: 11px; line-height: 1; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;">Diagnóstico de ROI</div>
                                            <h1 style="margin: 20px 0 12px; font-size: 34px; line-height: 1.12; color: {COMPOSTO_WEB_PRIMARY};">Seu diagnóstico de ROI está pronto</h1>
                                            <p style="margin: 0; max-width: 620px; font-size: 17px; line-height: 1.65; color: {COMPOSTO_WEB_TEXT};">{html.escape(contact_name)}, consolidamos em PDF a leitura executiva do seu cenário para apoiar a próxima decisão comercial e operacional.</p>
                                            <div style="margin-top: 20px;">{badges}</div>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
                            <td style="padding: 1px 38px 36px;">
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse: separate; border: 1px solid #d9dfeb; border-radius: 22px; background: {COMPOSTO_WEB_SURFACE};">
                  <tr>
                                        <td style="padding: 24px 28px;">
                      <div style="width: 54px; height: 4px; border-radius: 999px; background: {COMPOSTO_WEB_ACCENT};"></div>
                      <div style="margin-top: 12px; font-size: 12px; line-height: 1.2; color: {COMPOSTO_WEB_SECONDARY}; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;">Leitura executiva</div>
                                            <div style="margin-top: 10px; font-size: 18px; line-height: 1.55; color: {COMPOSTO_WEB_PRIMARY};">{_build_executive_highlight_html(executive_summary)}</div>
                      <div style="margin-top: 12px; font-size: 14px; line-height: 1.7; color: {COMPOSTO_WEB_TEXT};">{html.escape(context_summary)}</div>
                    </td>
                  </tr>
                </table>
                                <div style="height: 20px; line-height: 20px;">&nbsp;</div>
                {metrics_grid}
                                <div style="height: 10px; line-height: 10px;">&nbsp;</div>
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse: collapse;">
                  <tr>
                                        <td width="55%" style="padding: 0 10px 0 0; vertical-align: top;">
                      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse: separate; border: 1px solid #d9dfeb; border-radius: 20px; background: {COMPOSTO_WEB_WHITE};">
                        <tr>
                                                    <td style="padding: 24px 24px 22px;">
                            <div style="width: 44px; height: 4px; border-radius: 999px; background: {COMPOSTO_WEB_ACCENT};"></div>
                            <h2 style="margin: 12px 0 14px; font-size: 18px; line-height: 1.3; color: {COMPOSTO_WEB_PRIMARY};">Contexto considerado</h2>
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse: collapse;">{context_rows}</table>
                          </td>
                        </tr>
                      </table>
                    </td>
                                        <td width="45%" style="padding: 0 0 0 10px; vertical-align: top;">
                      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse: separate; border: 1px solid #d9dfeb; border-radius: 20px; background: {COMPOSTO_WEB_SURFACE};">
                        <tr>
                                                    <td style="padding: 24px 24px 22px;">
                            <div style="width: 44px; height: 4px; border-radius: 999px; background: {COMPOSTO_WEB_ACCENT};"></div>
                            <h2 style="margin: 12px 0 14px; font-size: 18px; line-height: 1.3; color: {COMPOSTO_WEB_PRIMARY};">Próximo passo recomendado</h2>
                            <p style="margin: 0; font-size: 14px; line-height: 1.7; color: {COMPOSTO_WEB_TEXT};">{html.escape(next_step)}</p>
                            <p style="margin: 16px 0 0; font-size: 14px; line-height: 1.7; color: {COMPOSTO_WEB_TEXT};">Se fizer sentido, responda este email com o processo prioritário. A partir disso, a Composto Web aprofunda o recorte técnico e comercial.</p>
                            {reply_cta}
                          </td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                </table>
                                <div style="height: 22px; line-height: 22px;">&nbsp;</div>
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse: separate; border: 1px solid #d9dfeb; border-radius: 20px; background: {COMPOSTO_WEB_WHITE};">
                  <tr>
                                        <td style="padding: 22px 24px;">
                      <div style="font-size: 12px; line-height: 1.2; color: {COMPOSTO_WEB_SECONDARY}; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;">O que está neste envio</div>
                      <p style="margin: 12px 0 0; font-size: 14px; line-height: 1.7; color: {COMPOSTO_WEB_TEXT};">O anexo traz o resumo financeiro, o enquadramento do cenário analisado e a recomendação inicial da Composto Web para priorização do próximo movimento.</p>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
                            <td style="padding: 0 38px 28px;">
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse: collapse; border-top: 1px solid #d9dfeb;">
                  <tr>
                    <td style="padding-top: 16px; font-size: 12px; line-height: 1.6; color: {COMPOSTO_WEB_SECONDARY};">Diagnóstico enviado pela equipe da Composto Web.</td>
                  </tr>
                </table>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
    """

    return {
        "recipient_email": recipient_email,
        "subject": f"Seu diagnóstico de ROI da automação — {subject_ref}",
        "html": html_body,
        "attachments": attachments,
        "reply_to": reply_to,
    }


def build_lead_magnet_delivery_email_html(
    *,
    lead_magnet_type: str,
    lead_magnet_title: str,
    lead_magnet_file_url: str | None,
    lead_magnet_cta_text: str | None,
    contact_name: str = "João Silva",
    email_subject_override: str | None = None,
    email_headline_override: str | None = None,
    email_body_text_override: str | None = None,
    email_cta_label_override: str | None = None,
) -> dict[str, str]:
    """Constrói o HTML do email de entrega sem enviar. Usado para preview no hub."""
    title = html.escape(lead_magnet_title or "Material")

    if lead_magnet_type == "pdf":
        subject = f"Seu material está pronto — {lead_magnet_title}"
        tag_label = "Material disponível"
        headline = "Seu material está pronto para download"
        body_text = (
            f"{html.escape(contact_name)}, o material que você solicitou está disponível. "
            "Acesse pelo link abaixo para fazer o download."
        )
        cta_label = lead_magnet_cta_text or "Baixar material"
        cta_href = html.escape(lead_magnet_file_url or "#")
        note = "O link abre o arquivo diretamente no seu navegador."
    elif lead_magnet_type == "link":
        subject = f"Acesse: {lead_magnet_title}"
        tag_label = "Acesso liberado"
        headline = "Seu acesso está liberado"
        body_text = (
            f"{html.escape(contact_name)}, o link que você pediu está pronto. "
            "Clique abaixo para acessar."
        )
        cta_label = lead_magnet_cta_text or "Acessar agora"
        cta_href = html.escape(lead_magnet_file_url or "#")
        note = "O link é pessoal e pode ser usado a qualquer momento."
    else:  # email_sequence
        subject = f"Você entrou na sequência — {lead_magnet_title}"
        tag_label = "Sequência ativada"
        headline = "Você entrou na sequência de emails"
        body_text = (
            f"{html.escape(contact_name)}, seu cadastro foi confirmado. "
            "Nos próximos dias você vai receber os emails da sequência com o material prometido."
        )
        cta_label = None
        cta_href = None
        note = "Caso não receba em até 24h, verifique sua caixa de spam."

    if email_subject_override and email_subject_override.strip():
        subject = email_subject_override.strip()

    if email_headline_override and email_headline_override.strip():
        headline = email_headline_override.strip()

    if email_body_text_override and email_body_text_override.strip():
        body_text = f"{html.escape(contact_name)}, {html.escape(email_body_text_override.strip())}"

    if email_cta_label_override and email_cta_label_override.strip():
        if cta_label is not None:  # não aplica em email_sequence
            cta_label = email_cta_label_override.strip()

    logo_markup = (
        f'<div style="font-size: 22px; line-height: 1; color: {COMPOSTO_WEB_PRIMARY}; '
        'font-weight: 800; letter-spacing: 0.03em;">COMPOSTO WEB</div>'
    )
    logo_bytes = load_composto_web_logo_primary_white_bg_bytes()
    if logo_bytes:
        if settings.COMPOSTO_WEB_LOGO_EMAIL_URL:
            logo_src: str = settings.COMPOSTO_WEB_LOGO_EMAIL_URL
        else:
            _api_url = settings.API_PUBLIC_URL.rstrip("/")
            _is_local = "localhost" in _api_url or "127.0.0.1" in _api_url
            if _is_local:
                logo_src = f"data:image/webp;base64,{base64.b64encode(logo_bytes).decode('ascii')}"
            else:
                logo_src = f"{_api_url}/assets/branding/compostoweb-logo-primary-transparent.webp"
        logo_markup = (
            f'<img src="{logo_src}" alt="Composto Web" width="220" '
            'style="display: block; width: 220px; max-width: 100%; height: auto;" />'
        )

    cta_block = ""
    if cta_label and cta_href:
        cta_block = (
            f'<div style="margin-top: 28px;">'
            f'<a href="{cta_href}" '
            f'style="display: inline-block; padding: 14px 28px; border-radius: 999px; '
            f"background: {COMPOSTO_WEB_ACCENT}; color: {COMPOSTO_WEB_WHITE}; "
            f"font-size: 15px; font-weight: 700; text-decoration: none; "
            f'letter-spacing: 0.01em;">'
            f"{html.escape(cta_label)}</a></div>"
        )

    html_body = f"""
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse; background: {COMPOSTO_WEB_SURFACE}; margin: 0; font-family: Arial, sans-serif;">
      <tr>
        <td align="center" style="padding: 28px 16px;">
          <table role="presentation" width="760" cellpadding="0" cellspacing="0" style="width: 100%; max-width: 760px; border-collapse: separate; border-spacing: 0; background: {COMPOSTO_WEB_WHITE}; border: 1px solid #d9dfeb; border-radius: 26px; overflow: hidden;">
            <tr>
              <td style="padding: 0; background: {COMPOSTO_WEB_WHITE};">
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse: collapse;">
                  <tr>
                    <td style="padding: 0; height: 6px; background: {COMPOSTO_WEB_ACCENT};"></td>
                  </tr>
                  <tr>
                    <td style="padding: 30px 38px 10px;">
                      {logo_markup}
                      <div style="display: inline-block; margin-top: 18px; padding: 8px 14px; border-radius: 999px; background: {COMPOSTO_WEB_SURFACE}; color: {COMPOSTO_WEB_SECONDARY}; font-size: 11px; line-height: 1; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;">{tag_label}</div>
                      <h1 style="margin: 20px 0 12px; font-size: 30px; line-height: 1.15; color: {COMPOSTO_WEB_PRIMARY};">{headline}</h1>
                      <p style="margin: 0 0 8px; font-size: 15px; line-height: 1.65; color: {COMPOSTO_WEB_TEXT};">{body_text}</p>
                      <p style="margin: 8px 0 0; font-size: 14px; line-height: 1.6; color: {COMPOSTO_WEB_SECONDARY};">Material: <strong>{title}</strong></p>
                      {cta_block}
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding: 4px 38px 28px;">
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse: separate; border: 1px solid #d9dfeb; border-radius: 20px; background: {COMPOSTO_WEB_SURFACE};">
                  <tr>
                    <td style="padding: 20px 24px;">
                      <p style="margin: 0; font-size: 13px; line-height: 1.6; color: {COMPOSTO_WEB_SECONDARY};">{html.escape(note)}</p>
                    </td>
                  </tr>
                </table>
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse: collapse; border-top: 1px solid #d9dfeb; margin-top: 20px;">
                  <tr>
                    <td style="padding-top: 16px; font-size: 12px; line-height: 1.6; color: {COMPOSTO_WEB_SECONDARY};">Enviado pela equipe da Composto Web.</td>
                  </tr>
                </table>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
    """

    return {"html": html_body, "subject": subject}


async def send_lead_magnet_delivery_email(
    *,
    lm_lead: ContentLMLead,
    lead_magnet: ContentLeadMagnet,
) -> bool:
    """Envia email de entrega ao lead após captura na LP (exceto calculadora)."""
    if lead_magnet.type == "calculator":
        return False

    resend = _get_resend()
    if not resend:
        return False

    recipient_email = (lm_lead.email or "").strip().lower()
    if not recipient_email:
        logger.warning(
            "notification.lm_delivery_missing_email",
            lm_lead_id=str(lm_lead.id),
        )
        return False

    contact_name = (lm_lead.name or "").strip() or "Olá"
    reply_to = settings.CONTENT_CALCULATOR_REPLY_TO_EMAIL.strip() or None

    built = build_lead_magnet_delivery_email_html(
        lead_magnet_type=lead_magnet.type,
        lead_magnet_title=lead_magnet.title or "Material",
        lead_magnet_file_url=lead_magnet.file_url,
        lead_magnet_cta_text=lead_magnet.cta_text,
        email_subject_override=lead_magnet.email_subject,
        email_headline_override=lead_magnet.email_headline,
        email_body_text_override=lead_magnet.email_body_text,
        email_cta_label_override=lead_magnet.email_cta_label,
        contact_name=contact_name,
    )

    payload: dict[str, object] = {
        "from": settings.CONTENT_CALCULATOR_NOTIFY_FROM_EMAIL or settings.RESEND_FROM_EMAIL,
        "to": [recipient_email],
        "subject": built["subject"],
        "html": built["html"],
    }
    if reply_to:
        payload["reply_to"] = reply_to

    try:
        resend.Emails.send(payload)
        logger.info(
            "notification.lm_delivery_sent",
            lm_lead_id=str(lm_lead.id),
            lead_magnet_id=str(lead_magnet.id),
            lm_type=lead_magnet.type,
            to=recipient_email,
        )
        return True
    except Exception as exc:
        logger.error(
            "notification.lm_delivery_failed",
            lm_lead_id=str(lm_lead.id),
            lead_magnet_id=str(lead_magnet.id),
            error=str(exc),
        )
        return False


async def send_reply_notification(
    lead: Lead,
    intent: str,
    reply_text: str,
    tenant_id: uuid.UUID,
    db: AsyncSession,
    replied_step: Any | None = None,
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

    notify_email = (
        await _resolve_reply_notification_recipient(
            tenant_id=tenant_id,
            db=db,
            replied_step=replied_step,
        )
        or config["email"]
    )

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

    subject = f"[Composto Web] {intent_label} — {html.escape(lead.name or '')}"
    html_body = f"""
    <div style="font-family: sans-serif; max-width: 600px;">
      <h2 style="color: #1a1a2e;">{intent_label}</h2>
      <p><strong>Lead:</strong> {html.escape(lead.name or '')}</p>
      <p><strong>Empresa:</strong> {html.escape(lead.company or '—')}</p>
      <p><strong>Cargo:</strong> {html.escape(lead.job_title or '—')}</p>
      <hr style="border: none; border-top: 1px solid #eee;" />
      <p style="white-space: pre-wrap; color: #333;">{html.escape(reply_text)}</p>
      <hr style="border: none; border-top: 1px solid #eee;" />
      <p style="font-size: 12px; color: #888;">
        Mensagem enviada pela Composto Web.
      </p>
    </div>
    """

    try:
        resend.Emails.send(
            {
                "from": settings.RESEND_FROM_EMAIL,
                "to": [notify_email],
                "subject": subject,
                "html": html_body,
            }
        )
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
    lead: Lead,
    cadence_name: str,
    step_number: int,
    message: str,
    tenant_id: uuid.UUID,
    db: AsyncSession,
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

    subject = f"[Composto Web] Tarefa manual — {html.escape(lead.name or '')} (Cadência: {html.escape(cadence_name)})"
    html_body = f"""
    <div style="font-family: sans-serif; max-width: 600px;">
      <h2 style="color: #1a1a2e">📋 Tarefa Manual</h2>
      <p><strong>Lead:</strong> {html.escape(lead.name or '')}</p>
      <p><strong>Empresa:</strong> {html.escape(lead.company or '—')}</p>
      <p><strong>Cadência:</strong> {html.escape(cadence_name)} — Step {step_number}</p>
      <hr style="border: none; border-top: 1px solid #eee;" />
      <p><strong>Instrução:</strong></p>
      <p style="white-space: pre-wrap; color: #333;">{html.escape(message)}</p>
      <hr style="border: none; border-top: 1px solid #eee;" />
      <p style="font-size: 12px; color: #888;">
        Mensagem enviada pela Composto Web.
      </p>
    </div>
    """

    try:
        resend.Emails.send(
            {
                "from": settings.RESEND_FROM_EMAIL,
                "to": [notify_email],
                "subject": subject,
                "html": html_body,
            }
        )
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
