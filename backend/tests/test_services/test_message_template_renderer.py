from __future__ import annotations

from types import SimpleNamespace

from services.message_template_renderer import (
    TEMPLATE_VARIABLE_CATALOG,
    build_lead_template_context,
    render_message_template,
)


def test_render_message_template_covers_entire_catalog() -> None:
    lead = SimpleNamespace(
        name="Marina Lopes",
        first_name="Marina",
        last_name="Lopes",
        company="Composto Web",
        job_title="CEO",
        industry="Marketing",
        city="São Paulo",
        location="São Paulo, SP",
        segment="B2B SaaS",
        company_domain="compostoweb.com",
        website="https://compostoweb.com",
        email_corporate="marina@compostoweb.com",
    )

    template = " | ".join(f"{{{key}}}" for key, _ in TEMPLATE_VARIABLE_CATALOG)

    rendered = render_message_template(template, lead)
    context = build_lead_template_context(lead)

    assert rendered == " | ".join(context[key] for key, _ in TEMPLATE_VARIABLE_CATALOG)


def test_render_message_template_supports_double_brace_email_tokens() -> None:
    lead = SimpleNamespace(name="Renato Costa", company="Orbit", job_title="Founder")

    rendered = render_message_template("Olá {{name}}, vi a {{company}}.", lead)

    assert rendered == "Olá Renato Costa, vi a Orbit."
