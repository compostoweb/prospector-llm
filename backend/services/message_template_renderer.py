"""
services/message_template_renderer.py

Helpers para renderização de templates de mensagem e email com dados do lead.

Suporta dois estilos de placeholder:
- steps da cadência: {first_name}, {company}, {job_title}
- templates de e-mail salvos: {{name}}, {{company}}, {{job_title}}
"""

from __future__ import annotations

from models.email_template import EmailTemplate


def build_lead_template_context(lead: object) -> dict[str, str]:
    """Monta contexto textual seguro para renderização de templates."""
    full_name = _get_attr(lead, "name") or "Lead"
    first_name = _get_attr(lead, "first_name") or full_name.split(" ")[0]
    last_name = _get_attr(lead, "last_name") or " ".join(full_name.split(" ")[1:])

    return {
        "lead_name": full_name,
        "name": full_name,
        "first_name": first_name or "Lead",
        "last_name": last_name or "",
        "company": _get_attr(lead, "company") or "Empresa",
        "job_title": _get_attr(lead, "job_title") or "Cargo",
        "industry": _get_attr(lead, "industry") or "Setor",
        "city": _get_attr(lead, "city") or "Cidade",
        "location": _get_attr(lead, "location") or _get_attr(lead, "city") or "Localização",
        "segment": _get_attr(lead, "segment") or _get_attr(lead, "industry") or "Segmento",
        "company_domain": _get_attr(lead, "company_domain") or "empresa.com",
        "website": _get_attr(lead, "website") or "https://empresa.com",
        "email": _get_attr(lead, "email_corporate") or _get_attr(lead, "email_personal") or _get_attr(lead, "email") or "",
    }


def render_message_template(template: str | None, lead: object) -> str | None:
    """Renderiza um template textual usando os dados do lead."""
    if not template:
        return None

    rendered = template
    context = build_lead_template_context(lead)
    replacements: dict[str, str] = {}

    for key, value in context.items():
        replacements[f"{{{key}}}"] = value
        replacements[f"{{{{{key}}}}}"] = value

    for token in sorted(replacements, key=len, reverse=True):
        rendered = rendered.replace(token, replacements[token])

    return rendered


def render_saved_email_template(template: EmailTemplate, lead: object) -> tuple[str, str]:
    """Renderiza subject + body_html de EmailTemplate salvo."""
    subject = render_message_template(template.subject, lead) or template.subject
    body_html = render_message_template(template.body_html, lead) or template.body_html
    return subject, body_html


def _get_attr(obj: object, attr: str) -> str | None:
    value = getattr(obj, attr, None)
    if value is None:
        return None
    return str(value)