"""
scripts/generate_lm_delivery_email_previews.py

Gera arquivos HTML de preview dos 3 templates de email de entrega de lead magnet:
  - pdf     → preview/lm_delivery_email_pdf.html
  - link    → preview/lm_delivery_email_link.html
  - email_sequence → preview/lm_delivery_email_sequence.html

Uso:
    cd backend
    python scripts/generate_lm_delivery_email_previews.py
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from core.branding import (
    COMPOSTO_WEB_LOGO_PRIMARY_TRANSPARENT_PATH,
    COMPOSTO_WEB_SURFACE,
)
from models.content_lead_magnet import ContentLeadMagnet
from models.content_lm_lead import ContentLMLead
from services import notification


def _make_lead_magnet(
    lm_type: str,
    *,
    title: str,
    file_url: str | None = None,
    cta_text: str | None = None,
) -> ContentLeadMagnet:
    lm = ContentLeadMagnet(
        tenant_id=uuid.uuid4(),
        type=lm_type,
        title=title,
        file_url=file_url,
        cta_text=cta_text,
        status="active",
    )
    lm.id = uuid.uuid4()
    return lm


def _make_lm_lead(*, name: str, email: str) -> ContentLMLead:
    lead = ContentLMLead(
        tenant_id=uuid.uuid4(),
        lead_magnet_id=uuid.uuid4(),
        name=name,
        email=email,
        origin="landing_page",
        company="Empresa Exemplo Ltda",
        role="Diretor de Operações",
    )
    lead.id = uuid.uuid4()
    return lead


_SCENARIOS: list[dict[str, object]] = [
    {
        "type": "pdf",
        "output": "lm_delivery_email_pdf.html",
        "lead_magnet": {
            "title": "Guia de Automação de Processos B2B",
            "file_url": "https://cdn.compostoweb.com.br/guia-automacao-2025.pdf",
            "cta_text": "Baixar guia agora",
        },
        "lead": {
            "name": "Mariana Costa",
            "email": "mariana@empresa.com.br",
        },
    },
    {
        "type": "link",
        "output": "lm_delivery_email_link.html",
        "lead_magnet": {
            "title": "Planilha de Controle de Processos Operacionais",
            "file_url": "https://notion.so/composto/planilha-controle-proc",
            "cta_text": None,
        },
        "lead": {
            "name": "Ricardo Oliveira",
            "email": "ricardo@industria.com.br",
        },
    },
    {
        "type": "email_sequence",
        "output": "lm_delivery_email_sequence.html",
        "lead_magnet": {
            "title": "Sequência B2B: Do Lead ao Contrato",
            "file_url": None,
            "cta_text": None,
        },
        "lead": {
            "name": "Fernanda Lima",
            "email": "fernanda@minha-empresa.com.br",
        },
    },
]


async def _build_html_for_scenario(scenario: dict[str, object]) -> str:
    """
    Chama send_lead_magnet_delivery_email com um cliente Resend fake que
    captura o HTML em vez de enviar.
    """
    captured: dict[str, object] = {}

    class FakeEmails:
        @staticmethod
        def send(payload: dict[str, object]) -> None:
            captured.update(payload)

    class FakeResend:
        Emails = FakeEmails

    original_get_resend = notification._get_resend
    original_settings_from = notification.settings.CONTENT_CALCULATOR_NOTIFY_FROM_EMAIL
    original_settings_reply = notification.settings.CONTENT_CALCULATOR_REPLY_TO_EMAIL

    notification._get_resend = lambda: FakeResend  # type: ignore[method-assign]
    notification.settings.CONTENT_CALCULATOR_NOTIFY_FROM_EMAIL = "site@compostoweb.com.br"  # type: ignore[misc]
    notification.settings.CONTENT_CALCULATOR_REPLY_TO_EMAIL = ""  # type: ignore[misc]

    lm_kwargs = scenario["lead_magnet"]
    assert isinstance(lm_kwargs, dict)
    lead_kwargs = scenario["lead"]
    assert isinstance(lead_kwargs, dict)
    lm_type = scenario["type"]
    assert isinstance(lm_type, str)

    lm = _make_lead_magnet(
        lm_type,
        title=str(lm_kwargs["title"]),
        file_url=lm_kwargs.get("file_url") if isinstance(lm_kwargs.get("file_url"), str) else None,
        cta_text=lm_kwargs.get("cta_text") if isinstance(lm_kwargs.get("cta_text"), str) else None,
    )
    lead = _make_lm_lead(
        name=str(lead_kwargs["name"]),
        email=str(lead_kwargs["email"]),
    )

    await notification.send_lead_magnet_delivery_email(lm_lead=lead, lead_magnet=lm)

    notification._get_resend = original_get_resend  # type: ignore[method-assign]
    notification.settings.CONTENT_CALCULATOR_NOTIFY_FROM_EMAIL = original_settings_from  # type: ignore[misc]
    notification.settings.CONTENT_CALCULATOR_REPLY_TO_EMAIL = original_settings_reply  # type: ignore[misc]

    return str(captured.get("html", "<!-- sem HTML capturado -->"))


def _wrap_document(html_body: str, title: str, logo_name: str | None) -> str:
    logo_fix = ""
    if logo_name:
        logo_fix = f"""<script>
    document.addEventListener('DOMContentLoaded', function() {{
        var imgs = document.querySelectorAll('img[src*="compostoweb-logo"]');
        imgs.forEach(function(img) {{ img.setAttribute('src', '{logo_name}'); }});
    }});
    </script>"""

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{title}</title>
    {logo_fix}
</head>
<body style="margin:0;padding:32px;background:{COMPOSTO_WEB_SURFACE};">
    {html_body}
</body>
</html>"""


async def main() -> None:
    output_dir = BACKEND_ROOT / "preview"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Copia logo para preview se existir
    logo_name: str | None = None
    if COMPOSTO_WEB_LOGO_PRIMARY_TRANSPARENT_PATH.exists():
        logo_dest = output_dir / COMPOSTO_WEB_LOGO_PRIMARY_TRANSPARENT_PATH.name
        logo_dest.write_bytes(COMPOSTO_WEB_LOGO_PRIMARY_TRANSPARENT_PATH.read_bytes())
        logo_name = COMPOSTO_WEB_LOGO_PRIMARY_TRANSPARENT_PATH.name

    generated: list[str] = []
    for scenario in _SCENARIOS:
        lm_type = str(scenario["type"])
        output_name = str(scenario["output"])
        lm_kwargs = scenario["lead_magnet"]
        assert isinstance(lm_kwargs, dict)

        print(f"→ Gerando preview para tipo: {lm_type}...")
        html_body = await _build_html_for_scenario(scenario)
        short_title = str(lm_kwargs["title"])
        document = _wrap_document(
            html_body, title=f"Email Preview: {short_title}", logo_name=logo_name
        )

        out_path = output_dir / output_name
        out_path.write_text(document, encoding="utf-8")
        generated.append(str(out_path))
        print(f"  ✓ {out_path}")

    print(f"\nPreviews gerados em: {output_dir}")
    for path in generated:
        print(f"  {path}")


if __name__ == "__main__":
    asyncio.run(main())
