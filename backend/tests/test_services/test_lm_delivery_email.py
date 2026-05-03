"""
tests/test_services/test_lm_delivery_email.py

Testes para send_lead_magnet_delivery_email — verifica subject, headline,
CTA, nota e ausência de anexo para cada tipo de lead magnet.
"""

from __future__ import annotations

import uuid

import pytest

from models.content_lead_magnet import ContentLeadMagnet
from models.content_lm_lead import ContentLMLead
from services import notification

pytestmark = pytest.mark.asyncio

# ── Factories ────────────────────────────────────────────────────────────────


def _make_lead_magnet(
    lm_type: str,
    *,
    title: str = "Material de Teste",
    file_url: str | None = "https://cdn.example.com/material.pdf",
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


def _make_lm_lead(
    *,
    name: str = "João Silva",
    email: str = "joao@empresa.com.br",
) -> ContentLMLead:
    lead = ContentLMLead(
        tenant_id=uuid.uuid4(),
        lead_magnet_id=uuid.uuid4(),
        name=name,
        email=email,
        origin="landing_page",
    )
    lead.id = uuid.uuid4()
    return lead


# ── Shared fake Resend ────────────────────────────────────────────────────────


def _patch_resend(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    """Injeta fake Resend que captura o payload enviado."""
    captured: dict[str, object] = {}

    class FakeEmails:
        @staticmethod
        def send(payload: dict[str, object]) -> None:
            captured.update(payload)

    class FakeResend:
        Emails = FakeEmails

    monkeypatch.setattr(notification, "_get_resend", lambda: FakeResend)
    monkeypatch.setattr(
        notification.settings,
        "CONTENT_CALCULATOR_NOTIFY_FROM_EMAIL",
        "site@compostoweb.com.br",
        raising=False,
    )
    monkeypatch.setattr(
        notification.settings,
        "CONTENT_CALCULATOR_REPLY_TO_EMAIL",
        "",
        raising=False,
    )
    monkeypatch.setattr(
        notification,
        "load_composto_web_logo_primary_white_bg_bytes",
        lambda: None,  # sem logo — usa fallback texto
    )
    return captured


# ── Tipo: pdf ────────────────────────────────────────────────────────────────


async def test_pdf_email_subject_and_cta(monkeypatch: pytest.MonkeyPatch) -> None:
    """PDF: subject correto, botão de download presente, sem attachments."""
    captured = _patch_resend(monkeypatch)
    lm = _make_lead_magnet("pdf", title="Guia de Automação Financeira")
    lead = _make_lm_lead(name="Maria Souza", email="maria@empresa.com.br")

    sent = await notification.send_lead_magnet_delivery_email(lm_lead=lead, lead_magnet=lm)

    assert sent is True
    assert captured["to"] == ["maria@empresa.com.br"]
    assert "Guia de Automação Financeira" in str(captured["subject"])
    assert "está pronto" in str(captured["subject"]).lower()

    html_body = str(captured["html"])
    assert "Material disponível" in html_body
    assert "Seu material está pronto para download" in html_body
    assert "Maria Souza" in html_body
    assert "Guia de Automação Financeira" in html_body
    assert "https://cdn.example.com/material.pdf" in html_body
    assert "Baixar material" in html_body
    assert "O link abre o arquivo diretamente" in html_body
    # Sem attachments no email de entrega de PDF — link direto
    assert "attachments" not in captured


async def test_pdf_email_custom_cta_text(monkeypatch: pytest.MonkeyPatch) -> None:
    """PDF com cta_text customizado usa o texto configurado no lead magnet."""
    captured = _patch_resend(monkeypatch)
    lm = _make_lead_magnet("pdf", title="Playbook de Vendas", cta_text="Baixar playbook agora")
    lead = _make_lm_lead()

    await notification.send_lead_magnet_delivery_email(lm_lead=lead, lead_magnet=lm)

    assert "Baixar playbook agora" in str(captured["html"])


# ── Tipo: link ───────────────────────────────────────────────────────────────


async def test_link_email_subject_and_cta(monkeypatch: pytest.MonkeyPatch) -> None:
    """Link: subject com 'Acesse:', botão CTA com URL do file_url."""
    captured = _patch_resend(monkeypatch)
    lm = _make_lead_magnet(
        "link",
        title="Planilha de Controle de Processos",
        file_url="https://notion.so/minha-planilha",
    )
    lead = _make_lm_lead(name="Carlos Mello", email="carlos@empresa.com.br")

    sent = await notification.send_lead_magnet_delivery_email(lm_lead=lead, lead_magnet=lm)

    assert sent is True
    assert captured["to"] == ["carlos@empresa.com.br"]
    subject = str(captured["subject"])
    assert subject.startswith("Acesse:")
    assert "Planilha de Controle de Processos" in subject

    html_body = str(captured["html"])
    assert "Acesso liberado" in html_body
    assert "Seu acesso está liberado" in html_body
    assert "Carlos Mello" in html_body
    assert "https://notion.so/minha-planilha" in html_body
    assert "Acessar agora" in html_body
    assert "O link é pessoal" in html_body
    assert "attachments" not in captured


# ── Tipo: email_sequence ─────────────────────────────────────────────────────


async def test_email_sequence_subject_no_cta(monkeypatch: pytest.MonkeyPatch) -> None:
    """email_sequence: subject correto, sem botão CTA, nota de spam presente."""
    captured = _patch_resend(monkeypatch)
    lm = _make_lead_magnet(
        "email_sequence",
        title="Sequência B2B: Do Lead a Cliente",
        file_url=None,
    )
    lead = _make_lm_lead(name="Ana Torres", email="ana@startup.com.br")

    sent = await notification.send_lead_magnet_delivery_email(lm_lead=lead, lead_magnet=lm)

    assert sent is True
    assert captured["to"] == ["ana@startup.com.br"]
    assert "Você entrou na sequência" in str(captured["subject"])
    assert "Sequência B2B: Do Lead a Cliente" in str(captured["subject"])

    html_body = str(captured["html"])
    assert "Sequência ativada" in html_body
    assert "Você entrou na sequência de emails" in html_body
    assert "Ana Torres" in html_body
    # Sem botão CTA — não tem URL para redirecionar
    assert 'href="' not in html_body or "https://notion.so" not in html_body
    assert "caixa de spam" in html_body
    assert "attachments" not in captured


# ── Tipo: calculator ─────────────────────────────────────────────────────────


async def test_calculator_skips_silently(monkeypatch: pytest.MonkeyPatch) -> None:
    """calculator: função retorna False sem enviar email — tem função própria."""
    captured = _patch_resend(monkeypatch)
    lm = _make_lead_magnet("calculator", title="Calculadora de ROI")
    lead = _make_lm_lead()

    result = await notification.send_lead_magnet_delivery_email(lm_lead=lead, lead_magnet=lm)

    assert result is False
    assert len(captured) == 0  # Resend nunca chamado


# ── Edge cases ───────────────────────────────────────────────────────────────


async def test_sem_resend_retorna_false(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sem Resend configurado, retorna False sem lançar exceção."""
    monkeypatch.setattr(notification, "_get_resend", lambda: None)
    lm = _make_lead_magnet("pdf")
    lead = _make_lm_lead()

    result = await notification.send_lead_magnet_delivery_email(lm_lead=lead, lead_magnet=lm)

    assert result is False


async def test_email_vazio_retorna_false(monkeypatch: pytest.MonkeyPatch) -> None:
    """Lead sem email retorna False e não dispara envio."""
    captured = _patch_resend(monkeypatch)
    lm = _make_lead_magnet("pdf")
    lead = _make_lm_lead(email="")

    result = await notification.send_lead_magnet_delivery_email(lm_lead=lead, lead_magnet=lm)

    assert result is False
    assert len(captured) == 0


async def test_from_email_configurado(monkeypatch: pytest.MonkeyPatch) -> None:
    """O campo 'from' usa CONTENT_CALCULATOR_NOTIFY_FROM_EMAIL quando configurado."""
    captured = _patch_resend(monkeypatch)
    monkeypatch.setattr(
        notification.settings,
        "CONTENT_CALCULATOR_NOTIFY_FROM_EMAIL",
        "noreply@compostoweb.com.br",
        raising=False,
    )
    lm = _make_lead_magnet("link", title="Ferramenta X")
    lead = _make_lm_lead()

    await notification.send_lead_magnet_delivery_email(lm_lead=lead, lead_magnet=lm)

    assert captured["from"] == "noreply@compostoweb.com.br"


async def test_reply_to_incluido_quando_configurado(monkeypatch: pytest.MonkeyPatch) -> None:
    """reply_to é incluído no payload quando há valor em CONTENT_CALCULATOR_REPLY_TO_EMAIL."""
    captured = _patch_resend(monkeypatch)
    monkeypatch.setattr(
        notification.settings,
        "CONTENT_CALCULATOR_REPLY_TO_EMAIL",
        "contato@compostoweb.com.br",
        raising=False,
    )
    lm = _make_lead_magnet("pdf")
    lead = _make_lm_lead()

    await notification.send_lead_magnet_delivery_email(lm_lead=lead, lead_magnet=lm)

    assert captured.get("reply_to") == "contato@compostoweb.com.br"


async def test_logo_inline_base64_quando_localhost(monkeypatch: pytest.MonkeyPatch) -> None:
    """Em localhost, logo vira data URI base64."""
    captured = _patch_resend(monkeypatch)
    monkeypatch.setattr(
        notification,
        "load_composto_web_logo_primary_white_bg_bytes",
        lambda: b"fake-logo-bytes",
    )
    monkeypatch.setattr(
        notification.settings,
        "API_PUBLIC_URL",
        "http://localhost:8000",
        raising=False,
    )
    monkeypatch.setattr(
        notification.settings,
        "COMPOSTO_WEB_LOGO_EMAIL_URL",
        "",
        raising=False,
    )
    lm = _make_lead_magnet("pdf")
    lead = _make_lm_lead()

    await notification.send_lead_magnet_delivery_email(lm_lead=lead, lead_magnet=lm)

    assert "data:image/webp;base64," in str(captured["html"])


async def test_preview_force_inline_logo_ignora_url_remota(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        notification,
        "load_composto_web_logo_primary_white_bg_bytes",
        lambda: b"fake-logo-bytes",
    )
    monkeypatch.setattr(
        notification.settings,
        "COMPOSTO_WEB_LOGO_EMAIL_URL",
        "https://cdn.example.com/logo.webp",
        raising=False,
    )

    built = notification.build_lead_magnet_delivery_email_html(
        lead_magnet_type="pdf",
        lead_magnet_title="Teste",
        lead_magnet_file_url="https://cdn.example.com/material.pdf",
        lead_magnet_cta_text=None,
        force_inline_logo=True,
    )

    assert "data:image/webp;base64," in built["html"]
    assert "https://cdn.example.com/logo.webp" not in built["html"]
