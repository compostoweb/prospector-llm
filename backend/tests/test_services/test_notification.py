from __future__ import annotations

import base64
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.content_calculator_result import ContentCalculatorResult
from models.cadence import Cadence
from models.cadence_step import CadenceStep
from models.email_account import EmailAccount
from models.enums import Channel
from models.lead import Lead
from models.tenant import TenantIntegration
from services import notification
from services.content.calculator_report import build_calculator_diagnosis_pdf

pytestmark = pytest.mark.asyncio


async def test_send_calculator_submission_notification_builds_expected_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sent_payload: dict[str, object] = {}

    class FakeEmails:
        @staticmethod
        def send(payload: dict[str, object]) -> None:
            sent_payload.update(payload)

    class FakeResend:
        Emails = FakeEmails

    monkeypatch.setattr(notification, "_get_resend", lambda: FakeResend)
    monkeypatch.setattr(
        notification.settings,
        "CONTENT_CALCULATOR_NOTIFY_EMAIL",
        "adriano@compostoweb.com.br",
        raising=False,
    )
    monkeypatch.setattr(
        notification.settings,
        "CONTENT_CALCULATOR_NOTIFY_FROM_EMAIL",
        "site@compostoweb.com.br",
        raising=False,
    )

    lead_id = uuid.uuid4()
    lm_lead_id = uuid.uuid4()
    result = ContentCalculatorResult(
        tenant_id=uuid.uuid4(),
        pessoas=4,
        horas_semana=18,
        custo_hora=120,
        cargo="gerente",
        retrabalho_pct=15,
        tipo_processo="financeiro",
        company_segment="industria",
        company_size="media",
        process_area_span="2-3",
        custo_mensal=9000,
        custo_retrabalho=2025,
        custo_total_mensal=11025,
        custo_anual=132300,
        investimento_estimado_min=12000,
        investimento_estimado_max=30000,
        roi_estimado=341.2,
        payback_meses=1.9,
        name="Maria Souza",
        email="maria@empresa.com.br",
        company="Empresa XPTO",
        role="Diretora Financeira",
        phone="11999990000",
        converted_to_lead=True,
        lead_id=lead_id,
    )

    sent = await notification.send_calculator_submission_notification(
        result=result,
        lead_magnet_title="Guia de Automação Financeira",
        lm_lead_id=lm_lead_id,
        sendpulse_sync_status="pending",
        diagnosis_email_sent=True,
    )

    assert sent is True
    assert sent_payload["from"] == "site@compostoweb.com.br"
    assert sent_payload["to"] == ["adriano@compostoweb.com.br"]
    assert "Maria Souza" in str(sent_payload["subject"])

    html_payload = str(sent_payload["html"])
    assert "Maria Souza" in html_payload
    assert "maria@empresa.com.br" in html_payload
    assert "Diretora Financeira" in html_payload
    assert "financeiro" in html_payload
    assert "industria" in html_payload
    assert "media" in html_payload
    assert "2-3" in html_payload
    assert "R$ 132.300,00" in html_payload
    assert "341,2%" in html_payload
    assert "1,9 meses" in html_payload
    assert "Guia de Automação Financeira" in html_payload
    assert str(lead_id) in html_payload
    assert str(lm_lead_id) in html_payload
    assert "pending" in html_payload
    assert "Sim" in html_payload
    assert "Composto Web" in html_payload
    assert "Prospector" not in html_payload


async def test_send_calculator_diagnosis_email_builds_attachment_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sent_payload: dict[str, object] = {}

    class FakeEmails:
        @staticmethod
        def send(payload: dict[str, object]) -> None:
            sent_payload.update(payload)

    class FakeResend:
        Emails = FakeEmails

    def fake_build_calculator_diagnosis_pdf(
        result: ContentCalculatorResult,
        lead_magnet_title: str | None = None,
    ) -> tuple[str, bytes]:
        del result, lead_magnet_title
        return ("diagnostico.pdf", b"%PDF-1.4 teste")

    monkeypatch.setattr(notification, "_get_resend", lambda: FakeResend)
    monkeypatch.setattr(
        notification,
        "build_calculator_diagnosis_pdf",
        fake_build_calculator_diagnosis_pdf,
    )
    monkeypatch.setattr(
        notification.settings,
        "CONTENT_CALCULATOR_NOTIFY_EMAIL",
        "adriano@compostoweb.com.br",
        raising=False,
    )
    monkeypatch.setattr(
        notification.settings,
        "CONTENT_CALCULATOR_NOTIFY_FROM_EMAIL",
        "site@compostoweb.com.br",
        raising=False,
    )
    monkeypatch.setattr(
        notification.settings,
        "CONTENT_CALCULATOR_REPLY_TO_EMAIL",
        "contato@compostoweb.com.br",
        raising=False,
    )
    monkeypatch.setattr(
        notification,
        "load_composto_web_logo_primary_white_bg_bytes",
        lambda: b"logo",
    )

    result = ContentCalculatorResult(
        tenant_id=uuid.uuid4(),
        pessoas=3,
        horas_semana=10,
        custo_hora=120,
        cargo="gerente",
        retrabalho_pct=12,
        tipo_processo="financeiro",
        company_segment="clinicas",
        company_size="media",
        process_area_span="2-3",
        custo_mensal=7000,
        custo_retrabalho=1200,
        custo_total_mensal=8200,
        custo_anual=98400,
        investimento_estimado_min=12000,
        investimento_estimado_max=25000,
        roi_estimado=220.5,
        payback_meses=2.1,
        name="João Lima",
        email="joao@clinica.com.br",
        company="Clínica Exemplo",
        role="Diretor",
        phone="11999990000",
    )

    sent = await notification.send_calculator_diagnosis_email(
        result=result,
        lead_magnet_title="Diagnóstico de Processos",
    )

    assert sent is True
    assert sent_payload["from"] == "site@compostoweb.com.br"
    assert sent_payload["to"] == ["joao@clinica.com.br"]
    assert sent_payload["replyTo"] == "contato@compostoweb.com.br"
    assert "Clínica Exemplo" in str(sent_payload["subject"])

    attachments = sent_payload["attachments"]
    assert isinstance(attachments, list)
    assert attachments == [
        {
            "filename": "diagnostico.pdf",
            "content": base64.b64encode(b"%PDF-1.4 teste").decode("ascii"),
            "contentType": "application/pdf",
        },
    ]

    html_payload = str(sent_payload["html"])
    assert "João Lima" in html_payload
    assert 'src="data:image/webp;base64,' in html_payload or 'src="https://' in html_payload
    assert "Seu processo manual está custando" in html_payload
    assert "R$ 98.400,00/ano" in html_payload
    assert "Clínicas" in html_payload
    assert "Média" in html_payload
    assert "2 a 3 áreas" in html_payload
    assert "Diagnóstico de Processos" in html_payload
    assert "Diagnóstico enviado pela equipe da Composto Web." in html_payload
    assert "Prospector" not in html_payload


async def test_build_calculator_diagnosis_pdf_derives_executive_summary_from_result() -> None:
    result = ContentCalculatorResult(
        tenant_id=uuid.uuid4(),
        pessoas=3,
        horas_semana=10,
        custo_hora=120,
        cargo="gerente",
        retrabalho_pct=12,
        tipo_processo="financeiro",
        company_segment="clinicas",
        company_size="media",
        process_area_span="2-3",
        custo_mensal=7000,
        custo_retrabalho=1200,
        custo_total_mensal=8200,
        custo_anual=98400,
        investimento_estimado_min=12000,
        investimento_estimado_max=25000,
        roi_estimado=220.5,
        payback_meses=2.1,
        name="João Lima",
        email="joao@clinica.com.br",
        company="Clínica Exemplo",
        role="Diretor",
        phone="11999990000",
    )

    filename, pdf_bytes = build_calculator_diagnosis_pdf(
        result,
        lead_magnet_title="Diagnóstico de Processos",
    )

    assert filename.startswith("diagnostico-roi-clinica-exemplo-")
    assert pdf_bytes.startswith(b"%PDF")


async def test_send_reply_notification_prefers_cadence_email_account_recipient(
    db: AsyncSession,
    tenant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sent_payload: dict[str, object] = {}

    class FakeEmails:
        @staticmethod
        def send(payload: dict[str, object]) -> None:
            sent_payload.update(payload)

    class FakeResend:
        Emails = FakeEmails

    account_id = uuid.uuid4()
    cadence_id = uuid.uuid4()
    lead_id = uuid.uuid4()

    account = EmailAccount(
        id=account_id,
        tenant_id=tenant.id,
        display_name="Adriano Gmail",
        email_address="adriano@compostoweb.com.br",
        provider_type="google_oauth",
        is_active=True,
    )
    db.add(account)
    await db.flush()

    cadence = Cadence(
        id=cadence_id,
        tenant_id=tenant.id,
        name="Cadência Email",
        is_active=True,
        llm_provider="openai",
        llm_model="gpt-5.4-mini",
        llm_temperature=0.7,
        llm_max_tokens=256,
        email_account_id=account.id,
    )
    lead = Lead(
        id=lead_id,
        tenant_id=tenant.id,
        name="Adriano",
        company="Pró-video endoscopia",
        email_corporate="adrianovaladao01@gmail.com",
        source="manual",
        status="converted",
    )
    step = CadenceStep(
        tenant_id=tenant.id,
        lead_id=lead_id,
        cadence_id=cadence_id,
        channel=Channel.EMAIL,
        step_number=3,
        day_offset=1,
        scheduled_at=datetime.now(UTC),
        status="replied",
    )
    integration = (
        await db.execute(select(TenantIntegration).where(TenantIntegration.tenant_id == tenant.id))
    ).scalar_one()
    integration.notify_email = "fallback@compostoweb.com.br"
    integration.notify_on_interest = True
    integration.notify_on_objection = True

    db.add_all([cadence, lead, step])
    await db.flush()

    monkeypatch.setattr(notification, "_get_resend", lambda: FakeResend)
    monkeypatch.setattr(
        notification.settings,
        "RESEND_FROM_EMAIL",
        "site@compostoweb.com.br",
        raising=False,
    )

    sent = await notification.send_reply_notification(
        lead=lead,
        intent="interest",
        reply_text="Quero saber mais.",
        tenant_id=tenant.id,
        db=db,
        replied_step=step,
    )

    assert sent is True
    assert sent_payload["from"] == "site@compostoweb.com.br"
    assert sent_payload["to"] == ["adriano@compostoweb.com.br"]
    assert "Quero saber mais." in str(sent_payload["html"])
