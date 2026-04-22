"""
tests/test_api/test_cadences.py

Testes de integração para GET/POST/PATCH/DELETE /cadences.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes import cadences as cadence_routes
from models.cadence_step import CadenceStep
from models.email_template import EmailTemplate
from models.enums import Channel, Intent, InteractionDirection, LeadSource, LeadStatus, StepStatus
from models.interaction import Interaction
from models.lead import Lead
from models.lead_list import LeadList
from models.tenant import TenantIntegration
from services.ai_composer import AIComposer
from services.cadence_delivery_budget import CadenceDeliveryBudgetSnapshot
from services.test_email_service import EmailTestSendResult

pytestmark = pytest.mark.asyncio


# ── Helpers ───────────────────────────────────────────────────────────


def _cadence_payload(**overrides) -> dict:
    base = {
        "name": "Cadência Teste",
        "description": "Cadência criada nos testes",
        "allow_personal_email": False,
        "llm": {
            "provider": "openai",
            "model": "gpt-5.4-mini",
            "temperature": 0.7,
            "max_tokens": 512,
        },
    }
    base.update(overrides)
    return base


async def _create_cadence(client: AsyncClient, **overrides) -> dict:
    resp = await client.post("/cadences", json=_cadence_payload(**overrides))
    assert resp.status_code == 201, resp.text
    return resp.json()


# ── POST /cadences ────────────────────────────────────────────────────


async def test_create_cadence(client: AsyncClient):
    resp = await client.post("/cadences", json=_cadence_payload())
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Cadência Teste"
    assert data["llm_provider"] == "openai"
    assert data["llm_model"] == "gpt-5.4-mini"
    assert data["is_active"] is False
    assert "id" in data


async def test_create_cadence_gemini(client: AsyncClient):
    payload = _cadence_payload(
        name="Cadência Gemini",
        llm={
            "provider": "gemini",
            "model": "gemini-2.5-flash",
            "temperature": 0.5,
            "max_tokens": 1024,
        },
    )
    resp = await client.post("/cadences", json=payload)
    assert resp.status_code == 201
    assert resp.json()["llm_provider"] == "gemini"
    assert resp.json()["llm_model"] == "gemini-2.5-flash"


async def test_create_cadence_uses_tenant_system_default_when_llm_omitted(
    client: AsyncClient,
    db,
    tenant_id,
):
    result = await db.execute(
        select(TenantIntegration).where(TenantIntegration.tenant_id == tenant_id)
    )
    integration = result.scalar_one()
    integration.llm_default_provider = "openai"
    integration.llm_default_model = "gpt-5.4-mini"
    integration.llm_default_temperature = 0.3
    integration.llm_default_max_tokens = 2048
    await db.flush()

    payload = _cadence_payload()
    payload.pop("llm")
    resp = await client.post("/cadences", json=payload)

    assert resp.status_code == 201
    data = resp.json()
    assert data["llm_provider"] == "openai"
    assert data["llm_model"] == "gpt-5.4-mini"
    assert data["llm_temperature"] == 0.3
    assert data["llm_max_tokens"] == 2048


async def test_create_cadence_uses_cold_email_default_when_llm_omitted(
    client: AsyncClient,
    db,
    tenant_id,
):
    result = await db.execute(
        select(TenantIntegration).where(TenantIntegration.tenant_id == tenant_id)
    )
    integration = result.scalar_one()
    integration.cold_email_llm_provider = "openai"
    integration.cold_email_llm_model = "gpt-5.4-mini"
    integration.cold_email_llm_temperature = 0.2
    integration.cold_email_llm_max_tokens = 640
    await db.flush()

    payload = _cadence_payload(cadence_type="email_only")
    payload.pop("llm")
    resp = await client.post("/cadences", json=payload)

    assert resp.status_code == 201
    data = resp.json()
    assert data["llm_provider"] == "openai"
    assert data["llm_model"] == "gpt-5.4-mini"
    assert data["llm_temperature"] == 0.2
    assert data["llm_max_tokens"] == 640


async def test_create_cadence_invalid_provider(client: AsyncClient):
    payload = _cadence_payload(
        llm={
            "provider": "invalid-provider",
            "model": "whatever-model",
            "temperature": 0.5,
            "max_tokens": 512,
        }
    )
    resp = await client.post("/cadences", json=payload)
    assert resp.status_code == 422


async def test_create_cadence_model_wrong_provider(client: AsyncClient):
    """gpt-5.4-mini com provider gemini deve falhar no validator."""
    payload = _cadence_payload(
        llm={"provider": "gemini", "model": "gpt-5.4-mini", "temperature": 0.5, "max_tokens": 512}
    )
    resp = await client.post("/cadences", json=payload)
    assert resp.status_code == 422


# ── GET /cadences ─────────────────────────────────────────────────────


async def test_list_cadences(client: AsyncClient):
    await _create_cadence(client)
    resp = await client.get("/cadences")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) >= 1


# ── GET /cadences/{id} ────────────────────────────────────────────────


async def test_get_cadence(client: AsyncClient):
    created = await _create_cadence(client)
    resp = await client.get(f"/cadences/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


async def test_get_cadence_delivery_budget(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    created = await _create_cadence(
        client,
        steps_template=[
            {
                "channel": "linkedin_post_reaction",
                "day_offset": 0,
                "message_template": None,
                "use_voice": False,
                "audio_file_id": None,
                "step_type": None,
            },
            {
                "channel": "linkedin_post_comment",
                "day_offset": 1,
                "message_template": "Boa leitura, {first_name}.",
                "use_voice": False,
                "audio_file_id": None,
                "step_type": None,
            },
            {
                "channel": "linkedin_inmail",
                "day_offset": 2,
                "message_template": "Assunto: Ideia rápida",
                "use_voice": False,
                "audio_file_id": None,
                "step_type": None,
            },
        ],
    )

    generated_at = datetime(2025, 1, 15, 14, 30, tzinfo=UTC)

    async def _fake_budget_snapshots(*args, **kwargs):
        return [
            CadenceDeliveryBudgetSnapshot(
                channel="linkedin_post_reaction",
                scope_type="linkedin_account",
                scope_label="SDR Ana",
                configured_limit=40,
                daily_budget=34,
                used_today=12,
                remaining_today=22,
                usage_pct=35.3,
                generated_at=generated_at,
            ),
            CadenceDeliveryBudgetSnapshot(
                channel="linkedin_post_comment",
                scope_type="linkedin_account",
                scope_label="SDR Ana",
                configured_limit=40,
                daily_budget=31,
                used_today=29,
                remaining_today=2,
                usage_pct=93.5,
                generated_at=generated_at,
            ),
            CadenceDeliveryBudgetSnapshot(
                channel="linkedin_inmail",
                scope_type="tenant_fallback",
                scope_label="Fallback LinkedIn abcd...9876",
                configured_limit=40,
                daily_budget=28,
                used_today=28,
                remaining_today=0,
                usage_pct=100.0,
                generated_at=generated_at,
            ),
        ]

    monkeypatch.setattr(
        cadence_routes,
        "build_cadence_delivery_budget_snapshots",
        _fake_budget_snapshots,
    )

    resp = await client.get(f"/cadences/{created['id']}/delivery-budget")

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["cadence_id"] == created["id"]
    assert data["generated_at"] == "2025-01-15T14:30:00Z"
    assert [item["channel"] for item in data["items"]] == [
        "linkedin_post_reaction",
        "linkedin_post_comment",
        "linkedin_inmail",
    ]
    assert data["items"][1]["remaining_today"] == 2
    assert data["items"][2]["scope_type"] == "tenant_fallback"


async def test_get_cadence_not_found(client: AsyncClient):
    resp = await client.get(f"/cadences/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_get_cadence_reply_management_returns_replies_and_audit_items(
    client: AsyncClient,
    db: AsyncSession,
    tenant_id,
) -> None:
    created = await _create_cadence(client)
    cadence_id = uuid.UUID(created["id"])

    lead = Lead(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="Lead Respondeu",
        company="Acme",
        job_title="Founder",
        email_corporate="lead@acme.com",
        status=LeadStatus.IN_CADENCE,
        source=LeadSource.MANUAL,
    )
    replied_step = CadenceStep(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        cadence_id=cadence_id,
        lead_id=lead.id,
        channel=Channel.EMAIL,
        step_number=1,
        day_offset=0,
        use_voice=False,
        status=StepStatus.REPLIED,
        scheduled_at=datetime.now(UTC),
        sent_at=datetime.now(UTC),
    )
    pending_step = CadenceStep(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        cadence_id=cadence_id,
        lead_id=lead.id,
        channel=Channel.EMAIL,
        step_number=2,
        day_offset=2,
        use_voice=False,
        status=StepStatus.PENDING,
        scheduled_at=datetime.now(UTC),
    )
    reply_interaction = Interaction(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        lead_id=lead.id,
        cadence_step_id=replied_step.id,
        channel=Channel.EMAIL,
        direction=InteractionDirection.INBOUND,
        content_text="Tenho interesse, vamos conversar.",
        intent=Intent.INTEREST,
        reply_match_status="matched",
        reply_match_source="message_id",
    )
    audit_interaction = Interaction(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        lead_id=lead.id,
        channel=Channel.EMAIL,
        direction=InteractionDirection.INBOUND,
        content_text="Respondi de outro fio.",
        reply_match_status="ambiguous",
        reply_match_source="lead_only",
        reply_match_sent_cadence_count=2,
    )
    low_confidence_interaction = Interaction(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        lead_id=lead.id,
        cadence_step_id=pending_step.id,
        channel=Channel.EMAIL,
        direction=InteractionDirection.INBOUND,
        content_text="Backup realizado com sucesso.",
        reply_match_status="matched",
        reply_match_source="fallback_single_cadence",
    )

    db.add_all(
        [
            lead,
            replied_step,
            pending_step,
            reply_interaction,
            audit_interaction,
            low_confidence_interaction,
        ]
    )
    await db.commit()

    resp = await client.get(f"/cadences/{created['id']}/reply-management")

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data["replies"]) == 1
    assert data["replies"][0]["lead"]["id"] == str(lead.id)
    assert data["replies"][0]["step_number"] == 1
    assert data["replies"][0]["reply_text"] == "Tenho interesse, vamos conversar."

    assert len(data["audit_items"]) == 2
    audit_statuses = {item["reply_match_status"] for item in data["audit_items"]}
    assert audit_statuses == {"ambiguous", "low_confidence"}
    low_confidence_item = next(
        item for item in data["audit_items"] if item["reply_match_status"] == "low_confidence"
    )
    assert low_confidence_item["content_text"] == "Backup realizado com sucesso."


async def test_get_cadence_reply_management_excludes_reviewed_audit_items(
    client: AsyncClient,
    db: AsyncSession,
    tenant_id,
) -> None:
    created = await _create_cadence(client)
    cadence_id = uuid.UUID(created["id"])

    lead = Lead(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="Lead Revisado",
        company="Acme",
        job_title="Founder",
        email_corporate="lead.reviewed@acme.com",
        status=LeadStatus.IN_CADENCE,
        source=LeadSource.MANUAL,
    )
    step = CadenceStep(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        cadence_id=cadence_id,
        lead_id=lead.id,
        channel=Channel.EMAIL,
        step_number=1,
        day_offset=0,
        use_voice=False,
        status=StepStatus.SENT,
        scheduled_at=datetime.now(UTC),
        sent_at=datetime.now(UTC),
    )
    reviewed_audit = Interaction(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        lead_id=lead.id,
        cadence_step_id=step.id,
        channel=Channel.EMAIL,
        direction=InteractionDirection.INBOUND,
        content_text="Reply já tratado.",
        reply_match_status="ambiguous",
        reply_reviewed_at=datetime.now(UTC),
    )

    db.add_all([lead, step, reviewed_audit])
    await db.commit()

    resp = await client.get(f"/cadences/{created['id']}/reply-management")

    assert resp.status_code == 200, resp.text
    assert resp.json()["audit_items"] == []


async def test_list_template_variables(client: AsyncClient):
    resp = await client.get("/cadences/template-variables")
    assert resp.status_code == 200
    data = resp.json()
    assert any(item["token"] == "{first_name}" for item in data)
    assert any(item["token"] == "{company}" for item in data)


async def test_compose_cadence_step_email(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    created = await _create_cadence(
        client,
        steps_template=[
            {
                "channel": "email",
                "day_offset": 0,
                "message_template": None,
                "use_voice": False,
                "audio_file_id": None,
                "step_type": "email_first",
            }
        ],
    )

    async def _fake_compose_email(self, **kwargs):
        return "Assunto {company}", "Olá {first_name}, podemos falar sobre {company}?"

    monkeypatch.setattr(AIComposer, "compose_email", _fake_compose_email)

    resp = await client.post(
        f"/cadences/{created['id']}/steps/0/compose",
        json={"action": "generate"},
    )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["channel"] == "email"
    assert data["subject"] == "Assunto {company}"
    assert data["message_template"] == "Olá {first_name}, podemos falar sobre {company}?"


async def test_create_cadence_accepts_manual_task_metadata(client: AsyncClient):
    created = await _create_cadence(
        client,
        steps_template=[
            {
                "channel": "manual_task",
                "day_offset": 2,
                "message_template": None,
                "use_voice": False,
                "audio_file_id": None,
                "step_type": None,
                "manual_task_type": "call",
                "manual_task_detail": "Ligar no período da manhã e citar o último contato.",
            }
        ],
    )

    step = created["steps_template"][0]
    assert step["manual_task_type"] == "call"
    assert step["manual_task_detail"] == "Ligar no período da manhã e citar o último contato."


async def test_preview_cadence_step_renders_current_draft_with_selected_lead(
    client: AsyncClient,
    db,
    tenant_id,
):
    lead = Lead(
        tenant_id=tenant_id,
        name="Mariana Costa",
        first_name="Mariana",
        last_name="Costa",
        company="Acme Labs",
        job_title="CEO",
        industry="Biotech",
        city="Campinas",
        location="Campinas, SP",
        segment="Saúde",
        company_domain="acme.com",
        website="https://acme.com",
        email_corporate="mariana@acme.com",
        source=LeadSource.MANUAL,
        status=LeadStatus.RAW,
    )
    db.add(lead)
    await db.flush()

    created = await _create_cadence(
        client,
        steps_template=[
            {
                "channel": "email",
                "day_offset": 0,
                "message_template": "Texto salvo {company}",
                "use_voice": False,
                "audio_file_id": None,
                "step_type": "email_first",
            }
        ],
    )

    resp = await client.post(
        f"/cadences/{created['id']}/steps/0/preview",
        json={
            "lead_id": str(lead.id),
            "current_text": "Olá {first_name}, vi a {company} em {city}.",
            "current_subject": "Ideia rápida para {company}",
        },
    )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["lead_name"] == "Mariana Costa"
    assert data["subject"] == "Ideia rápida para Acme Labs"
    assert data["body"] == "Olá Mariana, vi a Acme Labs em Campinas."
    assert data["body_is_html"] is False


async def test_preview_cadence_step_renders_saved_email_template(
    client: AsyncClient,
    db,
    tenant_id,
):
    lead = Lead(
        tenant_id=tenant_id,
        name="Carlos Lima",
        first_name="Carlos",
        company="Orbit",
        email_corporate="carlos@orbit.io",
        source=LeadSource.MANUAL,
        status=LeadStatus.RAW,
    )
    template = EmailTemplate(
        tenant_id=tenant_id,
        name="Template Preview",
        subject="Olá {{first_name}}",
        body_html="<p>Vi a {{company}} e pensei em você.</p>",
        is_active=True,
    )
    db.add_all([lead, template])
    await db.flush()

    created = await _create_cadence(
        client,
        steps_template=[
            {
                "channel": "email",
                "day_offset": 0,
                "message_template": "fallback",
                "use_voice": False,
                "audio_file_id": None,
                "step_type": "email_first",
                "email_template_id": str(template.id),
            }
        ],
    )

    resp = await client.post(
        f"/cadences/{created['id']}/steps/0/preview",
        json={
            "lead_id": str(lead.id),
            "current_email_template_id": str(template.id),
        },
    )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["subject"] == "Olá Carlos"
    assert "Orbit" in data["body"]
    assert data["body_is_html"] is True
    assert data["method"] == "saved_email_template"


async def test_preview_cadence_step_renders_linkedin_comment_variables(
    client: AsyncClient,
    db,
    tenant_id,
):
    lead = Lead(
        tenant_id=tenant_id,
        name="Paula Nogueira",
        first_name="Paula",
        company="Northwind",
        city="Recife",
        source=LeadSource.MANUAL,
        status=LeadStatus.RAW,
    )
    db.add(lead)
    await db.flush()

    created = await _create_cadence(
        client,
        steps_template=[
            {
                "channel": "linkedin_post_comment",
                "day_offset": 0,
                "message_template": "Paula, achei forte o ponto sobre a evolução da {company} em {city}.",
                "use_voice": False,
                "audio_file_id": None,
                "step_type": None,
            }
        ],
    )

    resp = await client.post(
        f"/cadences/{created['id']}/steps/0/preview",
        json={"lead_id": str(lead.id)},
    )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["subject"] is None
    assert data["body"] == "Paula, achei forte o ponto sobre a evolução da Northwind em Recife."
    assert data["method"] == "manual_template"


async def test_preview_cadence_step_renders_linkedin_inmail_json(
    client: AsyncClient,
    db,
    tenant_id,
):
    lead = Lead(
        tenant_id=tenant_id,
        name="Fernanda Alves",
        first_name="Fernanda",
        company="Atlas Bio",
        source=LeadSource.MANUAL,
        status=LeadStatus.RAW,
    )
    db.add(lead)
    await db.flush()

    created = await _create_cadence(
        client,
        steps_template=[
            {
                "channel": "linkedin_inmail",
                "day_offset": 0,
                "message_template": '{"subject":"Ideia para {company}","body":"Fernanda, queria abrir uma conversa objetiva."}',
                "use_voice": False,
                "audio_file_id": None,
                "step_type": None,
            }
        ],
    )

    resp = await client.post(
        f"/cadences/{created['id']}/steps/0/preview",
        json={"lead_id": str(lead.id)},
    )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["subject"] == "Ideia para Atlas Bio"
    assert data["body"] == "Fernanda, queria abrir uma conversa objetiva."
    assert data["method"] == "linkedin_inmail_json"


async def test_send_test_email_from_cadence_step_uses_rendered_draft(
    client: AsyncClient,
    db,
    tenant_id,
    monkeypatch: pytest.MonkeyPatch,
):
    lead = Lead(
        tenant_id=tenant_id,
        name="Mariana Costa",
        first_name="Mariana",
        company="Acme Labs",
        city="Campinas",
        source=LeadSource.MANUAL,
        status=LeadStatus.RAW,
    )
    db.add(lead)
    await db.flush()

    created = await _create_cadence(
        client,
        steps_template=[
            {
                "channel": "email",
                "day_offset": 0,
                "message_template": "Texto salvo {company}",
                "use_voice": False,
                "audio_file_id": None,
                "step_type": "email_first",
            }
        ],
    )

    captured: dict[str, object] = {}

    async def _fake_send_test_email(**kwargs):
        captured.update(kwargs)
        return EmailTestSendResult(
            to_email=str(kwargs["to_email"]),
            subject=str(kwargs["subject"]),
            provider_type="unipile_gmail",
            body_is_html=bool(kwargs["body_is_html"]),
        )

    monkeypatch.setattr(cadence_routes, "send_test_email", _fake_send_test_email)

    resp = await client.post(
        f"/cadences/{created['id']}/steps/0/send-test-email",
        json={
            "to_email": "teste@composto.com",
            "lead_id": str(lead.id),
            "current_text": "Olá {first_name}, vi a {company} em {city}.",
            "current_subject": "Ideia rápida para {company}",
        },
    )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["to_email"] == "teste@composto.com"
    assert data["subject"] == "Ideia rápida para Acme Labs"
    assert data["provider_type"] == "unipile_gmail"
    assert captured["subject"] == "Ideia rápida para Acme Labs"
    assert captured["body"] == "Olá Mariana, vi a Acme Labs em Campinas."
    assert captured["body_is_html"] is False


# ── PATCH /cadences/{id} ──────────────────────────────────────────────


async def test_update_cadence_name(client: AsyncClient):
    created = await _create_cadence(client)
    resp = await client.patch(f"/cadences/{created['id']}", json={"name": "Nome Atualizado"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Nome Atualizado"


async def test_update_cadence_llm(client: AsyncClient):
    created = await _create_cadence(client)
    resp = await client.patch(
        f"/cadences/{created['id']}",
        json={
            "llm": {
                "provider": "gemini",
                "model": "gemini-2.5-flash",
                "temperature": 0.3,
                "max_tokens": 2048,
            }
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["llm_provider"] == "gemini"
    assert data["llm_temperature"] == 0.3


async def test_update_cadence_deactivate(client: AsyncClient):
    created = await _create_cadence(client)
    resp = await client.patch(f"/cadences/{created['id']}", json={"is_active": False})
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


async def test_update_cadence_linking_list_enrolls_existing_members(
    client: AsyncClient,
    db: AsyncSession,
    tenant_id: uuid.UUID,
):
    lead = Lead(
        tenant_id=tenant_id,
        name="Lead Lista",
        first_name="Lead",
        company="Acme",
        linkedin_url="https://linkedin.com/in/lead-lista-cadencia",
        email_corporate="lead@acme.com",
        source=LeadSource.MANUAL,
        status=LeadStatus.RAW,
    )
    lead_list = LeadList(tenant_id=tenant_id, name="Lista da Cadência")
    lead_list.leads.append(lead)
    db.add_all([lead, lead_list])
    await db.commit()

    created = await _create_cadence(
        client,
        steps_template=[
            {
                "channel": "email",
                "day_offset": 0,
                "message_template": "Olá {first_name}",
                "use_voice": False,
                "audio_file_id": None,
                "step_type": "email_first",
            }
        ],
    )

    resp = await client.patch(
        f"/cadences/{created['id']}",
        json={"lead_list_id": str(lead_list.id)},
    )

    assert resp.status_code == 200, resp.text

    steps_result = await db.execute(
        select(CadenceStep).where(CadenceStep.cadence_id == uuid.UUID(created["id"]))
    )
    steps = steps_result.scalars().all()
    assert len(steps) == 1

    refreshed_lead = await db.get(Lead, lead.id)
    assert refreshed_lead is not None
    assert refreshed_lead.status == LeadStatus.IN_CADENCE


async def test_update_cadence_reschedules_pending_steps_when_template_changes(
    client: AsyncClient,
    db: AsyncSession,
    tenant_id: uuid.UUID,
):
    lead = Lead(
        tenant_id=tenant_id,
        name="Lead Reagendado",
        first_name="Lead",
        company="Acme",
        email_corporate="lead@acme.com",
        source=LeadSource.MANUAL,
        status=LeadStatus.ENRICHED,
    )
    db.add(lead)
    await db.commit()

    created = await _create_cadence(
        client,
        cadence_type="email_only",
        steps_template=[
            {
                "channel": "email",
                "day_offset": 0,
                "message_template": "Olá {first_name}",
                "use_voice": False,
                "audio_file_id": None,
                "step_type": "email_first",
            },
            {
                "channel": "email",
                "day_offset": 1,
                "message_template": "Follow-up 1 {first_name}",
                "use_voice": False,
                "audio_file_id": None,
                "step_type": "email_followup",
            },
            {
                "channel": "email",
                "day_offset": 0,
                "message_template": "Breakup {first_name}",
                "use_voice": False,
                "audio_file_id": None,
                "step_type": "email_breakup",
            },
        ],
    )

    activate_resp = await client.patch(
        f"/cadences/{created['id']}",
        json={"is_active": True},
    )
    assert activate_resp.status_code == 200, activate_resp.text

    enroll_resp = await client.post(
        f"/leads/{lead.id}/enroll",
        json={"cadence_id": created["id"]},
    )
    assert enroll_resp.status_code == 200, enroll_resp.text

    before_steps = (
        (
            await db.execute(
                select(CadenceStep)
                .where(
                    CadenceStep.cadence_id == uuid.UUID(created["id"]),
                    CadenceStep.lead_id == lead.id,
                )
                .order_by(CadenceStep.step_number.asc())
            )
        )
        .scalars()
        .all()
    )
    before_scheduled_at = {step.step_number: step.scheduled_at for step in before_steps}

    patch_resp = await client.patch(
        f"/cadences/{created['id']}",
        json={
            "steps_template": [
                {
                    "channel": "email",
                    "day_offset": 0,
                    "message_template": "Olá {first_name}",
                    "use_voice": False,
                    "audio_file_id": None,
                    "step_type": "email_first",
                },
                {
                    "channel": "email",
                    "day_offset": 1,
                    "message_template": "Follow-up 1 {first_name}",
                    "use_voice": False,
                    "audio_file_id": None,
                    "step_type": "email_followup",
                },
                {
                    "channel": "email",
                    "day_offset": 1,
                    "message_template": "Breakup {first_name}",
                    "use_voice": False,
                    "audio_file_id": None,
                    "step_type": "email_breakup",
                },
            ]
        },
    )
    assert patch_resp.status_code == 200, patch_resp.text

    after_steps = (
        (
            await db.execute(
                select(CadenceStep)
                .where(
                    CadenceStep.cadence_id == uuid.UUID(created["id"]),
                    CadenceStep.lead_id == lead.id,
                )
                .order_by(CadenceStep.step_number.asc())
            )
        )
        .scalars()
        .all()
    )
    after_map = {step.step_number: step for step in after_steps}

    assert after_map[1].scheduled_at == before_scheduled_at[1]
    assert after_map[2].scheduled_at == before_scheduled_at[2]
    assert after_map[3].day_offset == 1
    assert after_map[3].scheduled_at == before_scheduled_at[3] + timedelta(days=1)
    assert after_map[3].status == StepStatus.PENDING


# ── DELETE /cadences/{id} ─────────────────────────────────────────────


async def test_deactivate_cadence(client: AsyncClient):
    created = await _create_cadence(client)
    resp = await client.delete(f"/cadences/{created['id']}")
    assert resp.status_code == 204

    # Verifica que a cadência foi removida
    get_resp = await client.get(f"/cadences/{created['id']}")
    assert get_resp.status_code == 404
