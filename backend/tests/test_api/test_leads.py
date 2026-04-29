"""
tests/test_api/test_leads.py

Testes de integração para GET/POST/PATCH/DELETE /leads e sub-rotas.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.cadence import Cadence
from models.cadence_step import CadenceStep
from models.enums import Channel, Intent, LeadStatus, ManualTaskStatus, StepStatus
from models.interaction import Interaction
from models.lead import Lead
from models.lead_list import LeadList
from models.manual_task import ManualTask

pytestmark = pytest.mark.asyncio


# ── Helpers ───────────────────────────────────────────────────────────


def _lead_payload(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "name": "João Silva",
        "company": "Acme Corp",
        "website": "https://acme.com",
        "linkedin_url": "https://linkedin.com/in/joaosilva",
        "source": "manual",
    }
    base.update(overrides)
    return base


def _email_by_address(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["email"]: item for item in data["emails"]}


# ── POST /leads ───────────────────────────────────────────────────────


async def test_create_lead(client: AsyncClient):
    resp = await client.post("/leads", json=_lead_payload())
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "João Silva"
    assert data["company"] == "Acme Corp"
    assert data["status"] == LeadStatus.RAW.value
    assert "id" in data


async def test_create_lead_with_multiple_emails(client: AsyncClient):
    resp = await client.post(
        "/leads",
        json=_lead_payload(
            linkedin_url="https://linkedin.com/in/multi-email-create",
            email_corporate="contato@acme.com",
            email_personal="joao@gmail.com",
            emails=[
                {"email": "financeiro@acme.com", "email_type": "corporate"},
                {"email": "joao+extra@gmail.com", "email_type": "personal"},
            ],
        ),
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["email_corporate"] == "contato@acme.com"
    assert data["email_personal"] == "joao@gmail.com"
    assert {item["email"] for item in data["emails"]} == {
        "contato@acme.com",
        "joao@gmail.com",
        "financeiro@acme.com",
        "joao+extra@gmail.com",
    }


async def test_create_lead_exposes_contact_points(client: AsyncClient):
    resp = await client.post(
        "/leads",
        json=_lead_payload(
            linkedin_url="https://linkedin.com/in/contact-points-create",
            phone="+55 11 99999-1111",
            emails=[
                {
                    "email": "founder@acme.com",
                    "email_type": "corporate",
                    "verified": True,
                    "quality_bucket": "green",
                    "quality_score": 0.94,
                    "is_primary": True,
                }
            ],
        ),
    )

    assert resp.status_code == 201
    data = resp.json()
    assert {item["kind"] for item in data["contact_points"]} == {"email", "phone"}
    email_point = next(item for item in data["contact_points"] if item["kind"] == "email")
    assert email_point["value"] == "founder@acme.com"
    assert email_point["quality_bucket"] == "green"
    assert email_point["verified"] is True


async def test_create_lead_duplicate_linkedin(client: AsyncClient, db: AsyncSession):
    """Segundo cadastro com mesmo linkedin_url deve retornar 409."""
    payload = _lead_payload(linkedin_url="https://linkedin.com/in/duplicate-test")
    await client.post("/leads", json=payload)
    resp = await client.post("/leads", json=payload)
    assert resp.status_code == 409


async def test_create_lead_invalid_linkedin_url(client: AsyncClient):
    payload = _lead_payload(linkedin_url="https://facebook.com/joao")
    resp = await client.post("/leads", json=payload)
    assert resp.status_code == 422


# ── GET /leads ────────────────────────────────────────────────────────


async def test_list_leads_empty(client: AsyncClient):
    resp = await client.get("/leads")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data


async def test_list_leads_with_filter(client: AsyncClient):
    await client.post(
        "/leads", json=_lead_payload(linkedin_url="https://linkedin.com/in/filter-test")
    )
    resp = await client.get("/leads", params={"status": "raw"})
    assert resp.status_code == 200
    data = resp.json()
    assert all(item["status"] == "raw" for item in data["items"])


async def test_list_leads_pagination(client: AsyncClient):
    resp = await client.get("/leads", params={"page": 1, "page_size": 2})
    assert resp.status_code == 200
    assert len(resp.json()["items"]) <= 2


async def test_list_leads_filters_by_email_quality(client: AsyncClient):
    await client.post(
        "/leads",
        json=_lead_payload(
            linkedin_url="https://linkedin.com/in/filter-email-quality-green",
            emails=[
                {
                    "email": "green@acme.com",
                    "email_type": "corporate",
                    "verified": True,
                    "quality_bucket": "green",
                    "quality_score": 0.95,
                    "is_primary": True,
                }
            ],
        ),
    )
    await client.post(
        "/leads",
        json=_lead_payload(
            linkedin_url="https://linkedin.com/in/filter-email-quality-red",
            emails=[
                {
                    "email": "red@gmail.com",
                    "email_type": "personal",
                    "quality_bucket": "red",
                    "quality_score": 0.18,
                    "is_primary": True,
                }
            ],
        ),
    )

    resp = await client.get("/leads", params={"email_quality": "green"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["linkedin_url"] == "https://linkedin.com/in/filter-email-quality-green"


async def test_list_leads_filters_by_mobile_presence(client: AsyncClient):
    await client.post(
        "/leads",
        json=_lead_payload(
            linkedin_url="https://linkedin.com/in/filter-mobile-yes",
            phone="+55 11 98888-7777",
        ),
    )
    await client.post(
        "/leads",
        json=_lead_payload(linkedin_url="https://linkedin.com/in/filter-mobile-no"),
    )

    resp = await client.get("/leads", params={"has_mobile": "true"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["linkedin_url"] == "https://linkedin.com/in/filter-mobile-yes"


async def test_list_leads_filters_by_linkedin_mismatch(client: AsyncClient, db: AsyncSession):
    created = (
        await client.post(
            "/leads", json=_lead_payload(linkedin_url="https://linkedin.com/in/filter-mismatch")
        )
    ).json()

    lead = await db.get(Lead, uuid.UUID(created["id"]))
    assert lead is not None
    lead.linkedin_current_company = "Outra Empresa"
    lead.linkedin_mismatch = True
    await db.commit()

    resp = await client.get("/leads", params={"linkedin_mismatch": "true"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == created["id"]


# ── GET /leads/{id} ───────────────────────────────────────────────────


async def test_get_lead(client: AsyncClient):
    created = (
        await client.post(
            "/leads", json=_lead_payload(linkedin_url="https://linkedin.com/in/get-test")
        )
    ).json()
    resp = await client.get(f"/leads/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


async def test_get_lead_not_found(client: AsyncClient):
    import uuid

    resp = await client.get(f"/leads/{uuid.uuid4()}")
    assert resp.status_code == 404


# ── PATCH /leads/{id} ────────────────────────────────────────────────


async def test_update_lead(client: AsyncClient):
    created = (
        await client.post(
            "/leads", json=_lead_payload(linkedin_url="https://linkedin.com/in/update-test")
        )
    ).json()
    resp = await client.patch(f"/leads/{created['id']}", json={"company": "Nova Empresa Ltda"})
    assert resp.status_code == 200
    assert resp.json()["company"] == "Nova Empresa Ltda"


async def test_update_lead_status(client: AsyncClient):
    created = (
        await client.post(
            "/leads", json=_lead_payload(linkedin_url="https://linkedin.com/in/status-test")
        )
    ).json()
    resp = await client.patch(f"/leads/{created['id']}", json={"status": "enriched"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "enriched"


async def test_update_lead_replaces_email_collection(client: AsyncClient):
    created = (
        await client.post(
            "/leads",
            json=_lead_payload(
                linkedin_url="https://linkedin.com/in/multi-email-update",
                email_corporate="contato@acme.com",
                emails=[{"email": "ops@acme.com", "email_type": "corporate"}],
            ),
        )
    ).json()

    resp = await client.patch(
        f"/leads/{created['id']}",
        json={
            "email_corporate": "novo@acme.com",
            "email_personal": "joao@gmail.com",
            "emails": [
                {"email": "financeiro@acme.com", "email_type": "corporate"},
                {"email": "joao+extra@gmail.com", "email_type": "personal"},
            ],
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["email_corporate"] == "novo@acme.com"
    assert data["email_personal"] == "joao@gmail.com"
    assert {item["email"] for item in data["emails"]} == {
        "novo@acme.com",
        "joao@gmail.com",
        "financeiro@acme.com",
        "joao+extra@gmail.com",
    }


async def test_update_lead_primary_emails_only_keeps_secondary_and_preserves_ids(
    client: AsyncClient,
):
    created = (
        await client.post(
            "/leads",
            json=_lead_payload(
                linkedin_url="https://linkedin.com/in/primary-only-update",
                email_corporate="contato@acme.com",
                emails=[{"email": "ops@acme.com", "email_type": "corporate"}],
            ),
        )
    ).json()
    initial_emails = _email_by_address(created)

    resp = await client.patch(
        f"/leads/{created['id']}",
        json={
            "email_corporate": "novo@acme.com",
            "email_personal": "joao@gmail.com",
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    emails = _email_by_address(data)
    assert set(emails) == {"novo@acme.com", "joao@gmail.com", "ops@acme.com"}
    assert emails["ops@acme.com"]["id"] == initial_emails["ops@acme.com"]["id"]
    assert "contato@acme.com" not in emails


# ── DELETE /leads/{id} ────────────────────────────────────────────────


async def test_archive_lead(client: AsyncClient):
    created = (
        await client.post(
            "/leads", json=_lead_payload(linkedin_url="https://linkedin.com/in/archive-test")
        )
    ).json()
    resp = await client.delete(f"/leads/{created['id']}")
    assert resp.status_code == 204

    # Verifica que foi arquivado (não apagado)
    get_resp = await client.get(f"/leads/{created['id']}")
    assert get_resp.status_code == 200
    assert get_resp.json()["status"] == LeadStatus.ARCHIVED.value


# ── POST /leads/{id}/enroll ───────────────────────────────────────────


async def test_enroll_lead_cadence_not_found(client: AsyncClient):
    created = (
        await client.post(
            "/leads", json=_lead_payload(linkedin_url="https://linkedin.com/in/enroll-test")
        )
    ).json()
    resp = await client.post(
        f"/leads/{created['id']}/enroll",
        json={"cadence_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 404


async def test_enroll_archived_lead_fails(client: AsyncClient):
    created = (
        await client.post(
            "/leads", json=_lead_payload(linkedin_url="https://linkedin.com/in/enroll-archived")
        )
    ).json()
    await client.delete(f"/leads/{created['id']}")
    resp = await client.post(
        f"/leads/{created['id']}/enroll",
        json={"cadence_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 422


# ── GET /leads/{id}/interactions ──────────────────────────────────────


async def test_list_interactions_empty(client: AsyncClient):
    created = (
        await client.post(
            "/leads", json=_lead_payload(linkedin_url="https://linkedin.com/in/interactions-test")
        )
    ).json()
    resp = await client.get(f"/leads/{created['id']}/interactions")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


async def test_list_interactions_includes_reply_audit_fields(
    client: AsyncClient,
    db: AsyncSession,
):
    created = (
        await client.post(
            "/leads", json=_lead_payload(linkedin_url="https://linkedin.com/in/interactions-audit")
        )
    ).json()

    interaction = Interaction(
        tenant_id=uuid.UUID(created["tenant_id"]),
        lead_id=uuid.UUID(created["id"]),
        channel=Channel.EMAIL,
        direction="inbound",
        content_text="Recebi aqui, mas não sei a qual cadência pertence.",
        reply_match_status="ambiguous",
        reply_match_sent_cadence_count=2,
    )
    db.add(interaction)
    await db.commit()

    resp = await client.get(f"/leads/{created['id']}/interactions")

    assert resp.status_code == 200, resp.text
    item = resp.json()["items"][0]
    assert item["reply_match_status"] == "ambiguous"
    assert item["reply_match_sent_cadence_count"] == 2
    assert item["reply_reviewed_at"] is None


async def test_review_lead_reply_audit_marks_interaction_as_reviewed(
    client: AsyncClient,
    db: AsyncSession,
):
    created = (
        await client.post(
            "/leads", json=_lead_payload(linkedin_url="https://linkedin.com/in/review-reply-audit")
        )
    ).json()

    interaction = Interaction(
        id=uuid.uuid4(),
        tenant_id=uuid.UUID(created["tenant_id"]),
        lead_id=uuid.UUID(created["id"]),
        channel=Channel.EMAIL,
        direction="inbound",
        content_text="Recebi aqui, mas não sei a qual cadência pertence.",
        reply_match_status="ambiguous",
        reply_match_source="ambiguous_reply_hold",
        reply_match_sent_cadence_count=2,
    )
    db.add(interaction)
    await db.flush()

    cadence = Cadence(
        tenant_id=uuid.UUID(created["tenant_id"]),
        name="Cadência Hold Revisão",
        is_active=True,
        llm_provider="openai",
        llm_model="gpt-5.4-mini",
    )
    db.add(cadence)
    await db.flush()
    held_step = CadenceStep(
        tenant_id=uuid.UUID(created["tenant_id"]),
        cadence_id=cadence.id,
        lead_id=uuid.UUID(created["id"]),
        channel=Channel.EMAIL,
        step_number=2,
        day_offset=1,
        use_voice=False,
        status=StepStatus.SKIPPED,
        scheduled_at=datetime.now(tz=UTC),
        reply_hold_interaction_id=interaction.id,
        reply_hold_reason="ambiguous_reply",
        reply_hold_previous_status="pending",
        reply_hold_created_at=datetime.now(tz=UTC),
    )
    db.add(held_step)
    await db.commit()

    resp = await client.post(
        f"/leads/{created['id']}/interactions/{interaction.id}/review-reply-audit"
    )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["id"] == str(interaction.id)
    assert data["reply_reviewed_at"] is not None

    await db.refresh(interaction)
    await db.refresh(held_step)
    assert interaction.reply_reviewed_at is not None
    assert held_step.status == StepStatus.PENDING
    assert held_step.reply_hold_interaction_id is None
    assert held_step.reply_hold_reason is None


async def test_link_lead_reply_audit_links_interaction_and_skips_remaining_steps(
    client: AsyncClient,
    db: AsyncSession,
):
    created = (
        await client.post(
            "/leads", json=_lead_payload(linkedin_url="https://linkedin.com/in/link-reply-audit")
        )
    ).json()

    lead_id = uuid.UUID(created["id"])
    tenant_id = uuid.UUID(created["tenant_id"])

    cadence = Cadence(
        tenant_id=tenant_id,
        name="Cadência Link Manual",
        is_active=True,
        llm_provider="openai",
        llm_model="gpt-5.4-mini",
    )
    db.add(cadence)
    await db.flush()
    other_cadence = Cadence(
        tenant_id=tenant_id,
        name="Cadência Deve Continuar",
        is_active=True,
        llm_provider="openai",
        llm_model="gpt-5.4-mini",
    )
    db.add(other_cadence)
    await db.flush()

    replied_step = CadenceStep(
        tenant_id=tenant_id,
        cadence_id=cadence.id,
        lead_id=lead_id,
        channel=Channel.EMAIL,
        step_number=1,
        day_offset=0,
        use_voice=False,
        status=StepStatus.SENT,
        scheduled_at=datetime.now(tz=UTC),
        sent_at=datetime.now(tz=UTC),
    )
    pending_step = CadenceStep(
        tenant_id=tenant_id,
        cadence_id=cadence.id,
        lead_id=lead_id,
        channel=Channel.EMAIL,
        step_number=2,
        day_offset=1,
        use_voice=False,
        status=StepStatus.PENDING,
        scheduled_at=datetime.now(tz=UTC),
        sent_at=None,
    )
    interaction = Interaction(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        lead_id=lead_id,
        channel=Channel.EMAIL,
        direction="inbound",
        content_text="Sim, quero entender melhor.",
        intent="interest",
        reply_match_status="ambiguous",
        reply_match_source="ambiguous_reply_hold",
        reply_match_sent_cadence_count=2,
    )
    db.add(interaction)
    await db.flush()

    other_held_step = CadenceStep(
        tenant_id=tenant_id,
        cadence_id=other_cadence.id,
        lead_id=lead_id,
        channel=Channel.EMAIL,
        step_number=2,
        day_offset=1,
        use_voice=False,
        status=StepStatus.SKIPPED,
        scheduled_at=datetime.now(tz=UTC),
        sent_at=None,
        reply_hold_interaction_id=interaction.id,
        reply_hold_reason="ambiguous_reply",
        reply_hold_previous_status="pending",
        reply_hold_created_at=datetime.now(tz=UTC),
    )
    db.add_all([replied_step, pending_step, other_held_step])
    await db.commit()

    resp = await client.post(
        f"/leads/{created['id']}/interactions/{interaction.id}/link-reply-audit",
        json={"cadence_step_id": str(replied_step.id)},
    )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["id"] == str(interaction.id)
    assert data["cadence_step_id"] == str(replied_step.id)
    assert data["reply_match_status"] == "matched"
    assert data["reply_match_source"] == "manual_review"
    assert data["reply_reviewed_at"] is not None

    await db.refresh(interaction)
    await db.refresh(replied_step)
    await db.refresh(pending_step)
    await db.refresh(other_held_step)

    lead = await db.get(Lead, lead_id)
    assert lead is not None
    assert interaction.cadence_step_id == replied_step.id
    assert interaction.reply_match_status == "matched"
    assert interaction.reply_match_source == "manual_review"
    assert interaction.reply_reviewed_at is not None
    assert replied_step.status == StepStatus.REPLIED
    assert pending_step.status == StepStatus.SKIPPED
    assert other_held_step.status == StepStatus.PENDING
    assert other_held_step.reply_hold_interaction_id is None
    assert lead.status == LeadStatus.CONVERTED


async def test_list_lead_steps_matches_interactions_by_cadence_step_id(
    client: AsyncClient,
    db: AsyncSession,
):
    created = (
        await client.post(
            "/leads",
            json=_lead_payload(linkedin_url="https://linkedin.com/in/step-correlation-history"),
        )
    ).json()

    lead_id = uuid.UUID(created["id"])
    tenant_id = uuid.UUID(created["tenant_id"])

    cadence = Cadence(
        tenant_id=tenant_id,
        name="Cadência Correlação Timeline",
        is_active=True,
        llm_provider="openai",
        llm_model="gpt-5.4-mini",
    )
    db.add(cadence)
    await db.flush()

    first_step = CadenceStep(
        tenant_id=tenant_id,
        cadence_id=cadence.id,
        lead_id=lead_id,
        channel=Channel.EMAIL,
        step_number=1,
        day_offset=0,
        use_voice=False,
        status=StepStatus.SENT,
        scheduled_at=datetime.now(tz=UTC),
        sent_at=datetime.now(tz=UTC),
    )
    second_step = CadenceStep(
        tenant_id=tenant_id,
        cadence_id=cadence.id,
        lead_id=lead_id,
        channel=Channel.EMAIL,
        step_number=2,
        day_offset=1,
        use_voice=False,
        status=StepStatus.SENT,
        scheduled_at=datetime.now(tz=UTC),
        sent_at=datetime.now(tz=UTC),
    )
    db.add_all([first_step, second_step])
    await db.flush()

    db.add_all(
        [
            Interaction(
                tenant_id=tenant_id,
                lead_id=lead_id,
                cadence_step_id=second_step.id,
                channel=Channel.EMAIL,
                direction="outbound",
                content_text="Segundo email enviado",
            ),
            Interaction(
                tenant_id=tenant_id,
                lead_id=lead_id,
                cadence_step_id=first_step.id,
                channel=Channel.EMAIL,
                direction="outbound",
                content_text="Primeiro email enviado",
            ),
            Interaction(
                tenant_id=tenant_id,
                lead_id=lead_id,
                cadence_step_id=second_step.id,
                channel=Channel.EMAIL,
                direction="inbound",
                content_text="Resposta do segundo step",
            ),
        ]
    )
    await db.commit()

    resp = await client.get(f"/leads/{created['id']}/steps")

    assert resp.status_code == 200, resp.text
    items = resp.json()
    first_item = next(item for item in items if item["step_number"] == 1)
    second_item = next(item for item in items if item["step_number"] == 2)

    assert first_item["message_content"] == "Primeiro email enviado"
    assert first_item["reply_content"] is None
    assert second_item["message_content"] == "Segundo email enviado"
    assert second_item["reply_content"] == "Resposta do segundo step"


async def test_list_lead_steps_ignores_low_confidence_email_reply_without_reliable_inbound(
    client: AsyncClient,
    db: AsyncSession,
):
    created = (
        await client.post(
            "/leads",
            json=_lead_payload(linkedin_url="https://linkedin.com/in/step-low-confidence-history"),
        )
    ).json()

    lead_id = uuid.UUID(created["id"])
    tenant_id = uuid.UUID(created["tenant_id"])

    cadence = Cadence(
        tenant_id=tenant_id,
        name="Cadência Timeline Reply Fraco",
        is_active=True,
        llm_provider="openai",
        llm_model="gpt-5.4-mini",
    )
    db.add(cadence)
    await db.flush()

    step = CadenceStep(
        tenant_id=tenant_id,
        cadence_id=cadence.id,
        lead_id=lead_id,
        channel=Channel.EMAIL,
        step_number=1,
        day_offset=0,
        use_voice=False,
        status=StepStatus.REPLIED,
        scheduled_at=datetime.now(tz=UTC),
        sent_at=datetime.now(tz=UTC),
    )
    db.add(step)
    await db.flush()

    db.add_all(
        [
            Interaction(
                tenant_id=tenant_id,
                lead_id=lead_id,
                cadence_step_id=step.id,
                channel=Channel.EMAIL,
                direction="outbound",
                content_text="Email enviado",
            ),
            Interaction(
                tenant_id=tenant_id,
                lead_id=lead_id,
                cadence_step_id=step.id,
                channel=Channel.EMAIL,
                direction="inbound",
                content_text="Backup Completo N8N",
                reply_match_status="matched",
                reply_match_source="fallback_single_cadence",
            ),
        ]
    )
    await db.commit()

    resp = await client.get(f"/leads/{created['id']}/steps")

    assert resp.status_code == 200, resp.text
    item = resp.json()[0]
    assert item["status"] == StepStatus.SENT.value
    assert item["reply_content"] is None


async def test_list_lead_steps_includes_manual_task_metadata_and_manual_task_history(
    client: AsyncClient,
    db: AsyncSession,
):
    created = (
        await client.post(
            "/leads",
            json=_lead_payload(linkedin_url="https://linkedin.com/in/manual-task-history"),
        )
    ).json()

    lead_id = uuid.UUID(created["id"])
    tenant_id = uuid.UUID(created["tenant_id"])

    cadence = Cadence(
        tenant_id=tenant_id,
        name="Cadência Manual Timeline",
        is_active=True,
        llm_provider="openai",
        llm_model="gpt-5.4-mini",
        steps_template=[
            {
                "step_number": 1,
                "channel": "manual_task",
                "day_offset": 0,
                "message_template": None,
                "use_voice": False,
                "audio_file_id": None,
                "step_type": None,
                "manual_task_type": "call",
                "manual_task_detail": "Ligar para validar interesse e agendar conversa.",
            }
        ],
    )
    db.add(cadence)
    await db.flush()

    cadence_step = CadenceStep(
        tenant_id=tenant_id,
        cadence_id=cadence.id,
        lead_id=lead_id,
        channel=Channel.MANUAL_TASK,
        step_number=1,
        day_offset=0,
        use_voice=False,
        status=StepStatus.SENT,
        scheduled_at=datetime.now(tz=UTC),
        sent_at=datetime.now(tz=UTC),
    )
    db.add(cadence_step)

    manual_task = ManualTask(
        tenant_id=tenant_id,
        cadence_id=cadence.id,
        lead_id=lead_id,
        channel=Channel.EMAIL,
        step_number=2,
        status=ManualTaskStatus.DONE_EXTERNAL,
        notes="Operador enviou email manualmente e registrou follow-up.",
    )
    db.add(manual_task)
    await db.flush()

    resp = await client.get(f"/leads/{created['id']}/steps")

    assert resp.status_code == 200, resp.text
    items = resp.json()
    assert any(
        item["item_kind"] == "manual_task"
        and item["channel"] == "manual_task"
        and item["manual_task_type"] == "call"
        and item["manual_task_detail"] == "Ligar para validar interesse e agendar conversa."
        for item in items
    )
    assert any(
        item["item_kind"] == "manual_task"
        and item["status"] == "done_external"
        and item["notes"] == "Operador enviou email manualmente e registrou follow-up."
        for item in items
    )


async def test_list_lead_steps_includes_sent_manual_task_with_manual_text_priority(
    client: AsyncClient,
    db: AsyncSession,
):
    created = (
        await client.post(
            "/leads",
            json=_lead_payload(
                linkedin_url="https://linkedin.com/in/manual-task-sent-history",
                email_corporate="timeline@acme.com",
            ),
        )
    ).json()

    lead_id = uuid.UUID(created["id"])
    tenant_id = uuid.UUID(created["tenant_id"])

    cadence = Cadence(
        tenant_id=tenant_id,
        name="Cadência Manual Enviada Timeline",
        is_active=True,
        llm_provider="openai",
        llm_model="gpt-5.4-mini",
        steps_template=[
            {
                "step_number": 2,
                "channel": "email",
                "day_offset": 1,
                "message_template": None,
                "use_voice": False,
                "audio_file_id": None,
                "step_type": None,
                "manual_task_type": "whatsapp",
                "manual_task_detail": "Confirmar interesse e pedir melhor horário para retorno.",
            }
        ],
    )
    db.add(cadence)
    await db.flush()

    manual_task = ManualTask(
        tenant_id=tenant_id,
        cadence_id=cadence.id,
        lead_id=lead_id,
        channel=Channel.EMAIL,
        step_number=2,
        status=ManualTaskStatus.SENT,
        generated_text="Texto gerado automaticamente.",
        edited_text="Texto final aprovado pelo operador.",
        sent_at=datetime.now(tz=UTC),
    )
    db.add(manual_task)
    await db.flush()

    resp = await client.get(f"/leads/{created['id']}/steps")

    assert resp.status_code == 200, resp.text
    items = resp.json()
    manual_task_item = next(
        item
        for item in items
        if item["item_kind"] == "manual_task"
        and item["status"] == "sent"
        and item["manual_task_id"] == str(manual_task.id)
    )

    assert manual_task_item["channel"] == "email"
    assert manual_task_item["message_content"] == "Texto final aprovado pelo operador."
    assert manual_task_item["manual_task_type"] == "whatsapp"
    assert (
        manual_task_item["manual_task_detail"]
        == "Confirmar interesse e pedir melhor horário para retorno."
    )


async def test_list_lead_steps_includes_reply_metadata_for_manual_task(
    client: AsyncClient,
    db: AsyncSession,
):
    created = (
        await client.post(
            "/leads",
            json=_lead_payload(
                linkedin_url="https://linkedin.com/in/manual-task-reply-history",
                email_corporate="manual-reply@acme.com",
            ),
        )
    ).json()

    lead_id = uuid.UUID(created["id"])
    tenant_id = uuid.UUID(created["tenant_id"])

    cadence = Cadence(
        tenant_id=tenant_id,
        name="Cadência Manual Reply Timeline",
        is_active=True,
        llm_provider="openai",
        llm_model="gpt-5.4-mini",
        steps_template=[
            {
                "step_number": 2,
                "channel": "email",
                "day_offset": 1,
                "message_template": None,
                "use_voice": False,
                "audio_file_id": None,
                "step_type": None,
                "manual_task_type": "email_followup",
                "manual_task_detail": "Retomar a conversa por email.",
            }
        ],
    )
    db.add(cadence)
    await db.flush()

    manual_task = ManualTask(
        tenant_id=tenant_id,
        cadence_id=cadence.id,
        lead_id=lead_id,
        channel=Channel.EMAIL,
        step_number=2,
        status=ManualTaskStatus.SENT,
        edited_text="Texto final enviado manualmente.",
        sent_at=datetime.now(tz=UTC),
    )
    db.add(manual_task)
    await db.flush()

    db.add_all(
        [
            Interaction(
                tenant_id=tenant_id,
                lead_id=lead_id,
                manual_task_id=manual_task.id,
                channel=Channel.EMAIL,
                direction="outbound",
                content_text="Texto final enviado manualmente.",
            ),
            Interaction(
                tenant_id=tenant_id,
                lead_id=lead_id,
                manual_task_id=manual_task.id,
                channel=Channel.EMAIL,
                direction="inbound",
                content_text="Pode mandar mais detalhes.",
                intent=Intent.INTEREST,
                reply_match_status="matched",
                reply_match_source="email_message_id",
            ),
        ]
    )
    await db.commit()

    resp = await client.get(f"/leads/{created['id']}/steps")

    assert resp.status_code == 200, resp.text
    items = resp.json()
    manual_task_item = next(
        item
        for item in items
        if item["item_kind"] == "manual_task" and item["manual_task_id"] == str(manual_task.id)
    )

    assert manual_task_item["reply_content"] == "Pode mandar mais detalhes."
    assert manual_task_item["reply_manual_task_id"] == str(manual_task.id)
    assert manual_task_item["intent"] == "interest"


async def test_list_leads_accepts_score_min_alias(client: AsyncClient):
    await client.post(
        "/leads",
        json=_lead_payload(
            linkedin_url="https://linkedin.com/in/score-min-low",
            company=None,
            website=None,
        ),
    )
    await client.post(
        "/leads",
        json=_lead_payload(
            linkedin_url="https://linkedin.com/in/score-min-high",
            email_corporate="contato@acme.com",
            segment="SaaS",
            city="São Paulo",
        ),
    )

    resp = await client.get("/leads", params={"score_min": 60})
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["linkedin_url"] == "https://linkedin.com/in/score-min-high"


async def test_list_leads_filters_by_max_score(client: AsyncClient):
    await client.post(
        "/leads",
        json=_lead_payload(
            linkedin_url="https://linkedin.com/in/max-score-low",
            company=None,
            website=None,
        ),
    )
    await client.post(
        "/leads",
        json=_lead_payload(
            linkedin_url="https://linkedin.com/in/max-score-high",
            email_corporate="maria@acme.com",
            segment="SaaS",
            city="São Paulo",
            phone="5511999999999",
        ),
    )

    resp = await client.get("/leads", params={"score_max": 40})
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["linkedin_url"] == "https://linkedin.com/in/max-score-low"


async def test_list_leads_filters_by_cadence_id(client: AsyncClient, db: AsyncSession):
    created = (
        await client.post(
            "/leads",
            json=_lead_payload(linkedin_url="https://linkedin.com/in/cadence-filter-lead"),
        )
    ).json()
    await client.post(
        "/leads",
        json=_lead_payload(linkedin_url="https://linkedin.com/in/cadence-filter-other"),
    )

    cadence = Cadence(
        tenant_id=uuid.UUID(created["tenant_id"]),
        name="Cadência Filtro",
        is_active=True,
        llm_provider="openai",
        llm_model="gpt-5.4-mini",
    )
    db.add(cadence)
    await db.flush()

    enroll_resp = await client.post(
        f"/leads/{created['id']}/enroll",
        json={"cadence_id": str(cadence.id)},
    )
    assert enroll_resp.status_code == 200

    resp = await client.get("/leads", params={"cadence_id": str(cadence.id)})
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == created["id"]


async def test_list_leads_filters_by_segment(client: AsyncClient):
    await client.post(
        "/leads",
        json=_lead_payload(
            linkedin_url="https://linkedin.com/in/segment-filter-match",
            segment="SaaS B2B",
        ),
    )
    await client.post(
        "/leads",
        json=_lead_payload(
            linkedin_url="https://linkedin.com/in/segment-filter-miss",
            segment="Agencia",
        ),
    )

    resp = await client.get("/leads", params={"segment": "saas"})
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["linkedin_url"] == "https://linkedin.com/in/segment-filter-match"


async def test_list_leads_filters_by_list_id(client: AsyncClient, db: AsyncSession):
    created = (
        await client.post(
            "/leads",
            json=_lead_payload(linkedin_url="https://linkedin.com/in/list-filter-match"),
        )
    ).json()
    await client.post(
        "/leads",
        json=_lead_payload(linkedin_url="https://linkedin.com/in/list-filter-miss"),
    )

    lead_result = await db.execute(select(Lead).where(Lead.id == uuid.UUID(created["id"])))
    lead = lead_result.scalar_one()

    lead_list = LeadList(
        tenant_id=uuid.UUID(created["tenant_id"]),
        name="Lista Filtro",
    )
    lead_list.leads.append(lead)
    db.add(lead_list)
    await db.commit()

    resp = await client.get("/leads", params={"list_id": str(lead_list.id)})
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == created["id"]


async def test_generate_import_merge_duplicates_updates_existing_lead_and_preserves_email_id(
    client: AsyncClient,
):
    created = (
        await client.post(
            "/leads",
            json=_lead_payload(
                linkedin_url="https://linkedin.com/in/import-duplicate-match",
                email_corporate="contato@acme.com",
            ),
        )
    ).json()
    initial_emails = _email_by_address(created)

    resp = await client.post(
        "/leads/generate-import",
        json={
            "source": "google_maps",
            "merge_duplicates": True,
            "items": [
                {
                    "preview_id": "preview-1",
                    "name": "João Silva",
                    "company": "Acme Corp",
                    "linkedin_url": "https://linkedin.com/in/import-duplicate-match",
                    "email_corporate": "contato@acme.com",
                    "email_personal": "joao@gmail.com",
                    "source": "manual",
                    "origin_key": "google_maps",
                    "origin_label": "Google Maps (Apify)",
                }
            ],
        },
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["created"] == 0
    assert data["updated"] == 1
    assert data["duplicates"] == 1
    assert data["lead_ids"] == [created["id"]]

    refreshed = (await client.get(f"/leads/{created['id']}")).json()
    refreshed_emails = _email_by_address(refreshed)
    assert set(refreshed_emails) == {"contato@acme.com", "joao@gmail.com"}
    assert refreshed_emails["contato@acme.com"]["id"] == initial_emails["contato@acme.com"]["id"]
    assert {item["kind"] for item in refreshed["contact_points"]} == {"email"}
    assert {item["value"] for item in refreshed["contact_points"]} == {
        "contato@acme.com",
        "joao@gmail.com",
    }
    assert refreshed["score"] is not None


async def test_add_members_to_linked_list_enrolls_lead_even_when_cadence_is_paused(
    client: AsyncClient,
    db: AsyncSession,
    tenant_id: uuid.UUID,
):
    created = (
        await client.post(
            "/leads",
            json=_lead_payload(
                linkedin_url="https://linkedin.com/in/linked-list-auto-enroll",
                email_corporate="linked@acme.com",
            ),
        )
    ).json()

    lead_list = LeadList(tenant_id=tenant_id, name="Lista Vinculada")
    db.add(lead_list)
    await db.flush()

    cadence = Cadence(
        tenant_id=tenant_id,
        name="Cadência com Lista",
        is_active=False,
        llm_provider="openai",
        llm_model="gpt-5.4-mini",
        lead_list_id=lead_list.id,
        steps_template=[
            {
                "step_number": 1,
                "channel": "email",
                "day_offset": 0,
                "message_template": "Olá {first_name}",
                "use_voice": False,
                "audio_file_id": None,
                "step_type": "email_first",
            }
        ],
    )
    db.add(cadence)
    await db.commit()

    resp = await client.post(
        f"/lead-lists/{lead_list.id}/members",
        json={"lead_ids": [created["id"]]},
    )

    assert resp.status_code == 204, resp.text

    steps_result = await db.execute(select(CadenceStep).where(CadenceStep.cadence_id == cadence.id))
    steps = steps_result.scalars().all()
    assert len(steps) == 1

    refreshed_lead = await db.get(Lead, uuid.UUID(created["id"]))
    assert refreshed_lead is not None
    assert refreshed_lead.status == LeadStatus.IN_CADENCE


async def test_quick_create_lead_from_inbox_returns_loaded_email_collection(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    from api.routes import inbox as inbox_route

    attendee = SimpleNamespace(
        id="attendee-123",
        name="Maria Silva",
        profile_url="https://linkedin.com/in/mariasilva",
        profile_picture_url="https://cdn.example.com/maria.png",
        headline="CEO",
        company="Acme Corp",
        websites=["https://acme.com"],
        email="maria@acme.com",
    )
    chat = SimpleNamespace(attendees=[attendee])

    async def _fake_get_chat(chat_id: str) -> SimpleNamespace:
        assert chat_id == "chat-123"
        return chat

    async def _fake_find_lead_by_attendees(*args: Any, **kwargs: Any) -> None:
        return None

    monkeypatch.setattr(inbox_route.unipile_client, "get_chat", _fake_get_chat)
    monkeypatch.setattr(inbox_route, "_find_lead_by_attendees", _fake_find_lead_by_attendees)

    resp = await client.post(
        "/inbox/conversations/chat-123/create-lead",
        json={
            "name": "Maria Silva",
            "linkedin_url": "https://linkedin.com/in/mariasilva",
            "linkedin_profile_id": "attendee-123",
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["has_lead"] is True
    assert data["email_corporate"] == "maria@acme.com"
    assert data["emails"] == [
        {
            "id": data["emails"][0]["id"],
            "email": "maria@acme.com",
            "email_type": "corporate",
            "source": "unipile",
            "verified": False,
            "is_primary": True,
        }
    ]
