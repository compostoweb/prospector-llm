"""
services/content/newsletter_renderer.py

Renderiza payload estruturado da newsletter para Markdown e HTML
prontos para colar no editor LinkedIn Pulse.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from services.content.newsletter_rules import (
    NEWSLETTER_NAME,
    NEWSLETTER_SECTION_SPECS,
    SECTION_MINI_TUTORIAL,
    SECTION_PERGUNTA,
    SECTION_RADAR,
    SECTION_TEMA_QUINZENA,
    SECTION_VISAO_OPINIAO,
)

_FOOTER = "Adriano Valadão | Composto Web — compostoweb.com.br"


# ── Helpers ──────────────────────────────────────────────────────────


def _format_date_pt(d: date | datetime | None) -> str:
    if d is None:
        return ""
    months = [
        "janeiro", "fevereiro", "março", "abril", "maio", "junho",
        "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
    ]
    if isinstance(d, datetime):
        d = d.date()
    return f"{d.day} de {months[d.month - 1]} de {d.year}"


def _section_body_text(payload: dict[str, Any], key: str) -> str:
    section = payload.get(key)
    if not isinstance(section, dict):
        return ""
    heading = (section.get("heading") or "").strip()
    body = (section.get("body") or "").strip()
    if heading and body:
        return f"**{heading}**\n\n{body}"
    return body or heading


def _radar_body_md(radar: dict[str, Any]) -> str:
    parts: list[str] = []
    tool = radar.get("tool")
    if isinstance(tool, dict):
        name = tool.get("name") or ""
        what = tool.get("what") or ""
        when = tool.get("when") or ""
        limitation = tool.get("limitation") or ""
        parts.append(
            f"🔧 **Ferramenta:** **{name}** — {what}. "
            f"Quando usar: {when}. Limitação: {limitation}."
        )

    data = radar.get("data")
    if isinstance(data, dict):
        fact = data.get("fact") or ""
        source = data.get("source") or ""
        context = data.get("context") or ""
        parts.append(f"📊 **Número:** {fact} ({source}). {context}")

    reading = radar.get("reading")
    if isinstance(reading, dict):
        title = reading.get("title") or ""
        url = reading.get("url") or ""
        description = reading.get("description") or ""
        if title and url:
            parts.append(f"🔗 **Leitura:** [{title}]({url}) — {description}")

    return "\n\n".join(parts)


def _pergunta_text(payload: dict[str, Any]) -> str:
    p = payload.get("section_pergunta")
    if isinstance(p, str):
        return p.strip()
    if isinstance(p, dict):
        return (p.get("body") or p.get("text") or "").strip()
    return ""


def _tutorial_body_md(tutorial: dict[str, Any]) -> str:
    parts: list[str] = []
    heading = (tutorial.get("heading") or "").strip()
    if heading:
        parts.append(f"**{heading}**")

    steps = tutorial.get("steps") or []
    if isinstance(steps, list) and steps:
        for i, step in enumerate(steps, start=1):
            if isinstance(step, str) and step.strip():
                parts.append(f"{i}. {step.strip()}")

    example = (tutorial.get("example") or "").strip()
    if example:
        parts.append(f"\n*Exemplo:* {example}")

    impact = (tutorial.get("impact") or "").strip()
    if impact:
        parts.append(f"\n{impact}")

    return "\n".join(parts)


# ── Renderers publicos ────────────────────────────────────────────────


def render_to_markdown(
    payload: dict[str, Any],
    *,
    edition_number: int,
    publish_date: date | datetime | None = None,
) -> str:
    """
    Monta texto Markdown completo da edicao para clipboard.
    """
    title = (payload.get("title") or "").strip()
    subtitle = (payload.get("subtitle") or "").strip()
    opening = (payload.get("opening_line") or "").strip()
    date_str = _format_date_pt(publish_date)

    blocks: list[str] = []

    # Cabecalho
    blocks.append(f"# {NEWSLETTER_NAME} — Edição #{edition_number}")
    if title:
        blocks.append(f"## {title}")
    if subtitle:
        blocks.append(f"*{subtitle}*")
    if date_str or opening:
        header_line = " | ".join(p for p in [date_str, opening] if p)
        blocks.append(header_line)

    # Tema da Quinzena
    spec = NEWSLETTER_SECTION_SPECS[SECTION_TEMA_QUINZENA]
    body = _section_body_text(payload, "section_tema_quinzena")
    if body:
        blocks.append(f"## {spec['label']}\n\n{body}")

    # Visao & Opiniao
    spec = NEWSLETTER_SECTION_SPECS[SECTION_VISAO_OPINIAO]
    body = _section_body_text(payload, "section_visao_opiniao")
    if body:
        blocks.append(f"## {spec['label']}\n\n{body}")

    # Mini Tutorial
    spec = NEWSLETTER_SECTION_SPECS[SECTION_MINI_TUTORIAL]
    tutorial = payload.get("section_mini_tutorial")
    if isinstance(tutorial, dict):
        body = _tutorial_body_md(tutorial)
        if body:
            blocks.append(f"## {spec['label']}\n\n{body}")

    # Radar
    spec = NEWSLETTER_SECTION_SPECS[SECTION_RADAR]
    radar = payload.get("section_radar")
    if isinstance(radar, dict):
        body = _radar_body_md(radar)
        if body:
            blocks.append(f"## {spec['label']}\n\n{body}")

    # Pergunta
    spec = NEWSLETTER_SECTION_SPECS[SECTION_PERGUNTA]
    pergunta = _pergunta_text(payload)
    if pergunta:
        blocks.append(f"## {spec['label']}\n\n{pergunta}")

    # Rodape
    blocks.append(f"---\n\n{_FOOTER}")

    return "\n\n".join(blocks)


def render_to_html(
    payload: dict[str, Any],
    *,
    edition_number: int,
    publish_date: date | datetime | None = None,
) -> str:
    """
    Renderiza versao HTML simples (h1/h2/p/ol/strong/a) para colar no Pulse.
    Sem dependencia de markdown lib — implementacao manual focada nos blocos
    que a edicao realmente usa.
    """
    title = (payload.get("title") or "").strip()
    subtitle = (payload.get("subtitle") or "").strip()
    opening = (payload.get("opening_line") or "").strip()
    date_str = _format_date_pt(publish_date)

    parts: list[str] = []
    parts.append(f"<h1>{NEWSLETTER_NAME} — Edição #{edition_number}</h1>")
    if title:
        parts.append(f"<h2>{title}</h2>")
    if subtitle:
        parts.append(f"<p><em>{subtitle}</em></p>")
    if date_str or opening:
        parts.append(
            "<p><strong>"
            + " | ".join(p for p in [date_str, opening] if p)
            + "</strong></p>"
        )

    # Tema
    spec = NEWSLETTER_SECTION_SPECS[SECTION_TEMA_QUINZENA]
    body = _section_body_text(payload, "section_tema_quinzena")
    if body:
        parts.append(f"<h2>{spec['label']}</h2>")
        parts.append(_paragraphs_to_html(body))

    # Visao
    spec = NEWSLETTER_SECTION_SPECS[SECTION_VISAO_OPINIAO]
    body = _section_body_text(payload, "section_visao_opiniao")
    if body:
        parts.append(f"<h2>{spec['label']}</h2>")
        parts.append(_paragraphs_to_html(body))

    # Tutorial
    spec = NEWSLETTER_SECTION_SPECS[SECTION_MINI_TUTORIAL]
    tutorial = payload.get("section_mini_tutorial")
    if isinstance(tutorial, dict):
        parts.append(f"<h2>{spec['label']}</h2>")
        heading = (tutorial.get("heading") or "").strip()
        if heading:
            parts.append(f"<p><strong>{heading}</strong></p>")
        steps = tutorial.get("steps") or []
        if isinstance(steps, list) and steps:
            li = "".join(
                f"<li>{s}</li>" for s in steps if isinstance(s, str) and s.strip()
            )
            parts.append(f"<ol>{li}</ol>")
        example = (tutorial.get("example") or "").strip()
        if example:
            parts.append(f"<p><em>Exemplo:</em> {example}</p>")
        impact = (tutorial.get("impact") or "").strip()
        if impact:
            parts.append(f"<p>{impact}</p>")

    # Radar
    spec = NEWSLETTER_SECTION_SPECS[SECTION_RADAR]
    radar = payload.get("section_radar")
    if isinstance(radar, dict):
        parts.append(f"<h2>{spec['label']}</h2>")
        tool = radar.get("tool")
        if isinstance(tool, dict):
            parts.append(
                f"<p>🔧 <strong>Ferramenta:</strong> <strong>{tool.get('name','')}</strong> — "
                f"{tool.get('what','')}. Quando usar: {tool.get('when','')}. "
                f"Limitação: {tool.get('limitation','')}.</p>"
            )
        data = radar.get("data")
        if isinstance(data, dict):
            parts.append(
                f"<p>📊 <strong>Número:</strong> {data.get('fact','')} "
                f"({data.get('source','')}). {data.get('context','')}</p>"
            )
        reading = radar.get("reading")
        if isinstance(reading, dict) and reading.get("title") and reading.get("url"):
            parts.append(
                f"<p>🔗 <strong>Leitura:</strong> "
                f"<a href=\"{reading['url']}\">{reading['title']}</a> — "
                f"{reading.get('description','')}</p>"
            )

    # Pergunta
    spec = NEWSLETTER_SECTION_SPECS[SECTION_PERGUNTA]
    pergunta = _pergunta_text(payload)
    if pergunta:
        parts.append(f"<h2>{spec['label']}</h2>")
        parts.append(_paragraphs_to_html(pergunta))

    parts.append("<hr/>")
    parts.append(f"<p><em>{_FOOTER}</em></p>")

    return "\n".join(parts)


def _paragraphs_to_html(text: str) -> str:
    """Converte texto Markdown simples em <p> + <strong> + <em>."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    out: list[str] = []
    for p in paragraphs:
        # bold/italic minimo: **x** -> <strong>, *x* -> <em>
        escaped = p.replace("\n", "<br/>")
        # bold first to avoid em conflict
        escaped = _replace_pairs(escaped, "**", "strong")
        escaped = _replace_pairs(escaped, "*", "em")
        out.append(f"<p>{escaped}</p>")
    return "\n".join(out)


def _replace_pairs(text: str, marker: str, tag: str) -> str:
    """Substitui pares de marker por <tag>...</tag>."""
    parts = text.split(marker)
    if len(parts) < 3:
        return text
    out: list[str] = []
    for i, part in enumerate(parts):
        if i == 0:
            out.append(part)
        elif i % 2 == 1:
            out.append(f"<{tag}>{part}")
        else:
            out.append(f"</{tag}>{part}")
    return "".join(out)
