from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes import sandbox as sandbox_routes
from models.enums import SandboxRunStatus
from models.lead import Lead
from models.sandbox import SandboxRun, SandboxStep
from services.test_email_service import EmailTestSendResult

pytestmark = pytest.mark.asyncio


def _manual_task_cadence_payload(**overrides) -> dict:
    base = {
        "name": "Cadência Sandbox",
        "description": "Cadência criada pausada para testar sandbox",
        "llm": {
            "provider": "openai",
            "model": "gpt-5.4-mini",
            "temperature": 0.7,
            "max_tokens": 256,
        },
        "steps_template": [
            {
                "channel": "manual_task",
                "day_offset": 0,
                "message_template": None,
                "use_voice": False,
                "audio_file_id": None,
                "step_type": None,
            }
        ],
    }
    base.update(overrides)
    return base


async def _create_manual_task_cadence(client: AsyncClient, **overrides) -> dict:
    resp = await client.post("/cadences", json=_manual_task_cadence_payload(**overrides))
    assert resp.status_code == 201, resp.text
    return resp.json()


def _make_lead(tenant_id: uuid.UUID) -> Lead:
    return Lead(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="Lead Sandbox",
        company="Empresa Sandbox",
        job_title="Head de Operações",
    )


async def test_create_sandbox_run_for_paused_cadence(
    client: AsyncClient,
    db: AsyncSession,
    tenant_id: uuid.UUID,
    tenant,
):
    lead = _make_lead(tenant_id)
    db.add(lead)
    await db.flush()

    cadence = await _create_manual_task_cadence(client)
    assert cadence["is_active"] is False

    resp = await client.post(
        f"/cadences/{cadence['id']}/sandbox",
        json={"lead_ids": [str(lead.id)]},
    )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["cadence_id"] == cadence["id"]
    assert body["status"] == "running"
    assert body["lead_source"] == "real"
    assert len(body["steps"]) == 1
    assert body["steps"][0]["lead_name"] == "Lead Sandbox"
    assert body["steps"][0]["lead_company"] == "Empresa Sandbox"
    assert body["steps"][0]["lead_job_title"] == "Head de Operações"


async def test_start_from_sandbox_approved_run_activates_paused_cadence(
    client: AsyncClient,
    db: AsyncSession,
    tenant_id: uuid.UUID,
    tenant,
):
    lead = _make_lead(tenant_id)
    db.add(lead)
    await db.flush()

    cadence = await _create_manual_task_cadence(client)
    sandbox_resp = await client.post(
        f"/cadences/{cadence['id']}/sandbox",
        json={"lead_ids": [str(lead.id)]},
    )
    assert sandbox_resp.status_code == 201, sandbox_resp.text
    run = sandbox_resp.json()

    approve_resp = await client.patch(f"/sandbox/{run['id']}/approve")
    assert approve_resp.status_code == 200, approve_resp.text
    assert approve_resp.json()["status"] == "approved"

    start_resp = await client.post(f"/sandbox/{run['id']}/start")
    assert start_resp.status_code == 200, start_resp.text
    body = start_resp.json()
    assert body["cadence_id"] == cadence["id"]
    assert body["leads_enrolled"] == 1
    assert body["steps_created"] == 1

    cadence_resp = await client.get(f"/cadences/{cadence['id']}")
    assert cadence_resp.status_code == 200
    assert cadence_resp.json()["is_active"] is True


async def test_start_from_sandbox_requires_approved_run(
    client: AsyncClient,
    db: AsyncSession,
    tenant_id: uuid.UUID,
    tenant,
):
    lead = _make_lead(tenant_id)
    db.add(lead)
    await db.flush()

    cadence = await _create_manual_task_cadence(client)
    sandbox_resp = await client.post(
        f"/cadences/{cadence['id']}/sandbox",
        json={"lead_ids": [str(lead.id)]},
    )
    assert sandbox_resp.status_code == 201, sandbox_resp.text
    run_id = sandbox_resp.json()["id"]

    run = await db.get(SandboxRun, uuid.UUID(run_id))
    assert run is not None
    run.status = SandboxRunStatus.COMPLETED
    await db.flush()

    start_resp = await client.post(f"/sandbox/{run_id}/start")
    assert start_resp.status_code == 400
    assert "approved" in start_resp.json()["detail"]

    cadence_resp = await client.get(f"/cadences/{cadence['id']}")
    assert cadence_resp.status_code == 200
    assert cadence_resp.json()["is_active"] is False


async def test_send_test_email_from_sandbox_step_uses_generated_content(
    client: AsyncClient,
    db: AsyncSession,
    tenant_id: uuid.UUID,
    tenant,
    monkeypatch: pytest.MonkeyPatch,
):
    lead = Lead(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="Lead Sandbox",
        company="Empresa Sandbox",
        job_title="Head de Operações",
        email_corporate="lead@sandbox.com",
    )
    db.add(lead)
    await db.flush()

    cadence = await _create_manual_task_cadence(
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
    sandbox_resp = await client.post(
        f"/cadences/{cadence['id']}/sandbox",
        json={"lead_ids": [str(lead.id)]},
    )
    assert sandbox_resp.status_code == 201, sandbox_resp.text
    run = sandbox_resp.json()

    step = await db.get(SandboxStep, uuid.UUID(run["steps"][0]["id"]))
    assert step is not None
    step.message_content = "Teste sandbox renderizado"
    step.email_subject = None
    await db.flush()

    captured: dict[str, object] = {}

    async def _fake_send_test_email(**kwargs):
        captured.update(kwargs)
        return EmailTestSendResult(
            to_email=str(kwargs["to_email"]),
            subject=str(kwargs["subject"]),
            provider_type="unipile_gmail",
            body_is_html=bool(kwargs["body_is_html"]),
        )

    monkeypatch.setattr(sandbox_routes, "send_test_email", _fake_send_test_email)

    resp = await client.post(
        f"/sandbox/steps/{step.id}/send-test-email",
        json={"to_email": "qa@composto.com"},
    )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["to_email"] == "qa@composto.com"
    assert data["provider_type"] == "unipile_gmail"
    assert captured["body"] == "Teste sandbox renderizado"
    assert captured["body_is_html"] is False
    assert captured["subject"] == "Empresa Sandbox: processo manual ou automatizado?"
