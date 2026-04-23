from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.cadence import Cadence
from models.enums import Channel, LeadSource, LeadStatus, ManualTaskStatus
from models.interaction import Interaction
from models.lead import Lead
from models.manual_task import ManualTask
from models.tenant import TenantIntegration

pytestmark = pytest.mark.asyncio


def _make_lead(tenant_id: uuid.UUID, suffix: str) -> Lead:
    return Lead(
        tenant_id=tenant_id,
        name=f"Lead Manual {suffix}",
        company="Acme",
        linkedin_url=f"https://linkedin.com/in/manual-task-api-{suffix}",
        email_corporate=f"manual-{suffix}@acme.test",
        source=LeadSource.MANUAL,
        status=LeadStatus.IN_CADENCE,
    )


def _make_cadence(tenant_id: uuid.UUID, suffix: str) -> Cadence:
    return Cadence(
        tenant_id=tenant_id,
        name=f"Cadência Manual API {suffix}",
        is_active=True,
        mode="semi_manual",
        llm_provider="openai",
        llm_model="gpt-5.4-mini",
    )


async def test_list_manual_tasks_filters_by_cadence_and_returns_nested_lead(
    client: AsyncClient,
    db: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    lead = _make_lead(tenant_id, "list")
    cadence = _make_cadence(tenant_id, "list")
    other_cadence = _make_cadence(tenant_id, "other")
    db.add_all([lead, cadence, other_cadence])
    await db.flush()

    db.add_all(
        [
            ManualTask(
                tenant_id=tenant_id,
                cadence_id=cadence.id,
                lead_id=lead.id,
                channel=Channel.LINKEDIN_DM,
                step_number=2,
                status=ManualTaskStatus.CONTENT_GENERATED,
                generated_text="Mensagem gerada",
            ),
            ManualTask(
                tenant_id=tenant_id,
                cadence_id=other_cadence.id,
                lead_id=lead.id,
                channel=Channel.EMAIL,
                step_number=3,
                status=ManualTaskStatus.PENDING,
            ),
        ]
    )
    await db.commit()

    resp = await client.get(f"/tasks?cadence_id={cadence.id}")

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["step_number"] == 2
    assert data["items"][0]["status"] == ManualTaskStatus.CONTENT_GENERATED.value
    assert data["items"][0]["lead"]["name"] == lead.name


async def test_manual_task_stats_counts_supported_statuses(
    client: AsyncClient,
    db: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    lead = _make_lead(tenant_id, "stats")
    cadence = _make_cadence(tenant_id, "stats")
    db.add_all([lead, cadence])
    await db.flush()

    db.add_all(
        [
            ManualTask(
                tenant_id=tenant_id,
                cadence_id=cadence.id,
                lead_id=lead.id,
                channel=Channel.LINKEDIN_DM,
                step_number=2,
                status=ManualTaskStatus.PENDING,
            ),
            ManualTask(
                tenant_id=tenant_id,
                cadence_id=cadence.id,
                lead_id=lead.id,
                channel=Channel.EMAIL,
                step_number=3,
                status=ManualTaskStatus.CONTENT_GENERATED,
            ),
            ManualTask(
                tenant_id=tenant_id,
                cadence_id=cadence.id,
                lead_id=lead.id,
                channel=Channel.EMAIL,
                step_number=4,
                status=ManualTaskStatus.SENT,
                sent_at=datetime.now(tz=UTC),
            ),
            ManualTask(
                tenant_id=tenant_id,
                cadence_id=cadence.id,
                lead_id=lead.id,
                channel=Channel.LINKEDIN_DM,
                step_number=5,
                status=ManualTaskStatus.DONE_EXTERNAL,
                sent_at=datetime.now(tz=UTC),
            ),
            ManualTask(
                tenant_id=tenant_id,
                cadence_id=cadence.id,
                lead_id=lead.id,
                channel=Channel.EMAIL,
                step_number=6,
                status=ManualTaskStatus.SKIPPED,
            ),
        ]
    )
    await db.commit()

    resp = await client.get("/tasks/stats")

    assert resp.status_code == 200, resp.text
    assert resp.json() == {
        "pending": 1,
        "content_generated": 1,
        "sent": 1,
        "done_external": 1,
        "skipped": 1,
    }


async def test_list_manual_tasks_supports_search_statuses_and_sorting(
    client: AsyncClient,
    db: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    lead_older = _make_lead(tenant_id, "older")
    lead_older.name = "Alpha Prospect"
    lead_newer = _make_lead(tenant_id, "newer")
    lead_newer.name = "Zulu Prospect"
    cadence = _make_cadence(tenant_id, "queue")
    cadence.name = "Cadência Operacional"
    db.add_all([lead_older, lead_newer, cadence])
    await db.flush()

    older_task = ManualTask(
        tenant_id=tenant_id,
        cadence_id=cadence.id,
        lead_id=lead_older.id,
        channel=Channel.EMAIL,
        step_number=2,
        status=ManualTaskStatus.PENDING,
        created_at=datetime(2026, 1, 10, tzinfo=UTC),
    )
    newer_task = ManualTask(
        tenant_id=tenant_id,
        cadence_id=cadence.id,
        lead_id=lead_newer.id,
        channel=Channel.LINKEDIN_DM,
        step_number=3,
        status=ManualTaskStatus.CONTENT_GENERATED,
        generated_text="Mensagem pronta",
        created_at=datetime(2026, 2, 10, tzinfo=UTC),
    )
    sent_task = ManualTask(
        tenant_id=tenant_id,
        cadence_id=cadence.id,
        lead_id=lead_newer.id,
        channel=Channel.EMAIL,
        step_number=4,
        status=ManualTaskStatus.SENT,
        sent_at=datetime(2026, 3, 10, tzinfo=UTC),
        created_at=datetime(2026, 3, 10, tzinfo=UTC),
    )
    db.add_all([older_task, newer_task, sent_task])
    await db.commit()

    resp = await client.get(
        "/tasks",
        params=[
            ("statuses", ManualTaskStatus.PENDING.value),
            ("statuses", ManualTaskStatus.CONTENT_GENERATED.value),
            ("search", "cadência operacional"),
            ("sort_by", "created_at"),
            ("sort_dir", "asc"),
        ],
    )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total"] == 2
    assert [item["id"] for item in data["items"]] == [
        str(older_task.id),
        str(newer_task.id),
    ]
    assert data["items"][0]["cadence_name"] == cadence.name
    assert data["items"][1]["lead"]["name"] == lead_newer.name


async def test_list_manual_tasks_supports_sorting_by_cadence_name(
    client: AsyncClient,
    db: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    lead = _make_lead(tenant_id, "sort-cadence")
    cadence_b = _make_cadence(tenant_id, "beta")
    cadence_b.name = "Beta Cadência"
    cadence_a = _make_cadence(tenant_id, "alpha")
    cadence_a.name = "Alpha Cadência"
    db.add_all([lead, cadence_a, cadence_b])
    await db.flush()

    task_b = ManualTask(
        tenant_id=tenant_id,
        cadence_id=cadence_b.id,
        lead_id=lead.id,
        channel=Channel.EMAIL,
        step_number=2,
        status=ManualTaskStatus.PENDING,
    )
    task_a = ManualTask(
        tenant_id=tenant_id,
        cadence_id=cadence_a.id,
        lead_id=lead.id,
        channel=Channel.LINKEDIN_DM,
        step_number=3,
        status=ManualTaskStatus.PENDING,
    )
    db.add_all([task_b, task_a])
    await db.commit()

    resp = await client.get("/tasks?sort_by=cadence_name&sort_dir=asc")

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert [item["cadence_name"] for item in data["items"][:2]] == [
        cadence_a.name,
        cadence_b.name,
    ]


async def test_list_manual_tasks_supports_sla_filter(
    client: AsyncClient,
    db: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    lead = _make_lead(tenant_id, "sla")
    cadence = _make_cadence(tenant_id, "sla")
    db.add_all([lead, cadence])
    await db.flush()

    db.add_all(
        [
            ManualTask(
                tenant_id=tenant_id,
                cadence_id=cadence.id,
                lead_id=lead.id,
                channel=Channel.EMAIL,
                step_number=2,
                status=ManualTaskStatus.PENDING,
                created_at=datetime.now(tz=UTC) - timedelta(hours=8),
            ),
            ManualTask(
                tenant_id=tenant_id,
                cadence_id=cadence.id,
                lead_id=lead.id,
                channel=Channel.EMAIL,
                step_number=3,
                status=ManualTaskStatus.PENDING,
                created_at=datetime.now(tz=UTC) - timedelta(hours=36),
            ),
            ManualTask(
                tenant_id=tenant_id,
                cadence_id=cadence.id,
                lead_id=lead.id,
                channel=Channel.EMAIL,
                step_number=4,
                status=ManualTaskStatus.PENDING,
                created_at=datetime.now(tz=UTC) - timedelta(hours=96),
            ),
        ]
    )
    await db.commit()

    urgent_resp = await client.get("/tasks?sla=urgent")
    attention_resp = await client.get("/tasks?sla=attention")
    fresh_resp = await client.get("/tasks?sla=fresh")

    assert urgent_resp.status_code == 200, urgent_resp.text
    assert attention_resp.status_code == 200, attention_resp.text
    assert fresh_resp.status_code == 200, fresh_resp.text
    assert [item["step_number"] for item in urgent_resp.json()["items"]] == [4]
    assert [item["step_number"] for item in attention_resp.json()["items"]] == [3]
    assert [item["step_number"] for item in fresh_resp.json()["items"]] == [2]


async def test_list_manual_tasks_supports_created_at_date_range(
    client: AsyncClient,
    db: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    lead = _make_lead(tenant_id, "date-range")
    cadence = _make_cadence(tenant_id, "date-range")
    db.add_all([lead, cadence])
    await db.flush()

    db.add_all(
        [
            ManualTask(
                tenant_id=tenant_id,
                cadence_id=cadence.id,
                lead_id=lead.id,
                channel=Channel.EMAIL,
                step_number=2,
                status=ManualTaskStatus.PENDING,
                created_at=datetime(2026, 4, 10, tzinfo=UTC),
            ),
            ManualTask(
                tenant_id=tenant_id,
                cadence_id=cadence.id,
                lead_id=lead.id,
                channel=Channel.LINKEDIN_DM,
                step_number=3,
                status=ManualTaskStatus.CONTENT_GENERATED,
                created_at=datetime(2026, 4, 22, tzinfo=UTC),
            ),
        ]
    )
    await db.commit()

    resp = await client.get("/tasks?start_date=2026-04-20&end_date=2026-04-23")

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total"] == 1
    assert [item["step_number"] for item in data["items"]] == [3]


async def test_manual_task_stats_support_created_at_date_range(
    client: AsyncClient,
    db: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    lead = _make_lead(tenant_id, "stats-range")
    cadence = _make_cadence(tenant_id, "stats-range")
    db.add_all([lead, cadence])
    await db.flush()

    db.add_all(
        [
            ManualTask(
                tenant_id=tenant_id,
                cadence_id=cadence.id,
                lead_id=lead.id,
                channel=Channel.EMAIL,
                step_number=2,
                status=ManualTaskStatus.PENDING,
                created_at=datetime(2026, 4, 8, tzinfo=UTC),
            ),
            ManualTask(
                tenant_id=tenant_id,
                cadence_id=cadence.id,
                lead_id=lead.id,
                channel=Channel.EMAIL,
                step_number=3,
                status=ManualTaskStatus.DONE_EXTERNAL,
                created_at=datetime(2026, 4, 21, tzinfo=UTC),
            ),
            ManualTask(
                tenant_id=tenant_id,
                cadence_id=cadence.id,
                lead_id=lead.id,
                channel=Channel.LINKEDIN_DM,
                step_number=4,
                status=ManualTaskStatus.SKIPPED,
                created_at=datetime(2026, 4, 22, tzinfo=UTC),
            ),
        ]
    )
    await db.commit()

    resp = await client.get("/tasks/stats?start_date=2026-04-20&end_date=2026-04-23")

    assert resp.status_code == 200, resp.text
    assert resp.json() == {
        "pending": 0,
        "content_generated": 0,
        "sent": 0,
        "done_external": 1,
        "skipped": 1,
    }


async def test_get_manual_task_returns_manual_task_metadata(
    client: AsyncClient,
    db: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    lead = _make_lead(tenant_id, "manual-meta")
    cadence = _make_cadence(tenant_id, "manual-meta")
    cadence.steps_template = [
        {"step_number": 1, "channel": Channel.LINKEDIN_CONNECT.value},
        {
            "step_number": 2,
            "channel": Channel.MANUAL_TASK.value,
            "manual_task_type": "whatsapp",
            "manual_task_detail": "Enviar mensagem curta no WhatsApp e confirmar disponibilidade.",
        },
    ]
    db.add_all([lead, cadence])
    await db.flush()

    task = ManualTask(
        tenant_id=tenant_id,
        cadence_id=cadence.id,
        lead_id=lead.id,
        channel=Channel.MANUAL_TASK,
        step_number=2,
        status=ManualTaskStatus.PENDING,
    )
    db.add(task)
    await db.commit()

    resp = await client.get(f"/tasks/{task.id}")

    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["manual_task_type"] == "whatsapp"
    assert (
        payload["manual_task_detail"]
        == "Enviar mensagem curta no WhatsApp e confirmar disponibilidade."
    )


async def test_update_manual_task_persists_edited_text(
    client: AsyncClient,
    db: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    lead = _make_lead(tenant_id, "update")
    cadence = _make_cadence(tenant_id, "update")
    db.add_all([lead, cadence])
    await db.flush()

    task = ManualTask(
        tenant_id=tenant_id,
        cadence_id=cadence.id,
        lead_id=lead.id,
        channel=Channel.EMAIL,
        step_number=2,
        status=ManualTaskStatus.CONTENT_GENERATED,
        generated_text="Texto gerado originalmente.",
    )
    db.add(task)
    await db.commit()

    resp = await client.patch(
        f"/tasks/{task.id}",
        json={"edited_text": "Texto final revisado pelo operador."},
    )

    assert resp.status_code == 200, resp.text
    assert resp.json()["edited_text"] == "Texto final revisado pelo operador."
    await db.refresh(task)
    assert task.edited_text == "Texto final revisado pelo operador."


async def test_mark_done_external_updates_status_and_notes(
    client: AsyncClient,
    db: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    lead = _make_lead(tenant_id, "done")
    cadence = _make_cadence(tenant_id, "done")
    db.add_all([lead, cadence])
    await db.flush()

    task = ManualTask(
        tenant_id=tenant_id,
        cadence_id=cadence.id,
        lead_id=lead.id,
        channel=Channel.EMAIL,
        step_number=3,
        status=ManualTaskStatus.PENDING,
    )
    db.add(task)
    await db.commit()

    resp = await client.post(
        f"/tasks/{task.id}/done",
        json={"notes": "Executado fora do sistema após contato telefônico."},
    )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == ManualTaskStatus.DONE_EXTERNAL.value
    assert data["notes"] == "Executado fora do sistema após contato telefônico."
    assert data["sent_at"] is not None


async def test_skip_manual_task_updates_status(
    client: AsyncClient,
    db: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    lead = _make_lead(tenant_id, "skip")
    cadence = _make_cadence(tenant_id, "skip")
    db.add_all([lead, cadence])
    await db.flush()

    task = ManualTask(
        tenant_id=tenant_id,
        cadence_id=cadence.id,
        lead_id=lead.id,
        channel=Channel.LINKEDIN_DM,
        step_number=2,
        status=ManualTaskStatus.CONTENT_GENERATED,
        generated_text="Mensagem pronta para envio.",
    )
    db.add(task)
    await db.commit()

    resp = await client.post(f"/tasks/{task.id}/skip")

    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == ManualTaskStatus.SKIPPED.value
    await db.refresh(task)
    assert task.status == ManualTaskStatus.SKIPPED


async def test_reopen_done_external_task_restores_it_to_actionable_queue(
    client: AsyncClient,
    db: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    lead = _make_lead(tenant_id, "reopen")
    cadence = _make_cadence(tenant_id, "reopen")
    db.add_all([lead, cadence])
    await db.flush()

    task = ManualTask(
        tenant_id=tenant_id,
        cadence_id=cadence.id,
        lead_id=lead.id,
        channel=Channel.EMAIL,
        step_number=2,
        status=ManualTaskStatus.DONE_EXTERNAL,
        edited_text="Texto pronto para reenviar.",
        notes="Feita sem querer.",
        sent_at=datetime.now(tz=UTC),
    )
    db.add(task)
    await db.commit()

    resp = await client.post(f"/tasks/{task.id}/reopen")

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == ManualTaskStatus.CONTENT_GENERATED.value
    assert data["sent_at"] is None
    assert data["notes"] is None


async def test_reopen_rejects_non_reopenable_task_status(
    client: AsyncClient,
    db: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    lead = _make_lead(tenant_id, "reopen-invalid")
    cadence = _make_cadence(tenant_id, "reopen-invalid")
    db.add_all([lead, cadence])
    await db.flush()

    task = ManualTask(
        tenant_id=tenant_id,
        cadence_id=cadence.id,
        lead_id=lead.id,
        channel=Channel.EMAIL,
        step_number=2,
        status=ManualTaskStatus.SENT,
        edited_text="Já enviada.",
        sent_at=datetime.now(tz=UTC),
    )
    db.add(task)
    await db.commit()

    resp = await client.post(f"/tasks/{task.id}/reopen")

    assert resp.status_code == 400, resp.text
    assert "podem ser reabertas" in resp.json()["detail"]


async def test_send_manual_task_persists_interaction_with_manual_task_id(
    client: AsyncClient,
    db: AsyncSession,
    tenant_id: uuid.UUID,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lead = _make_lead(tenant_id, "send")
    cadence = _make_cadence(tenant_id, "send")
    db.add_all([lead, cadence])
    await db.flush()

    integration_result = await db.execute(
        select(TenantIntegration).where(TenantIntegration.tenant_id == tenant_id)
    )
    integration = integration_result.scalar_one()
    integration.unipile_gmail_account_id = "gmail-account-test"

    task = ManualTask(
        tenant_id=tenant_id,
        cadence_id=cadence.id,
        lead_id=lead.id,
        channel=Channel.EMAIL,
        step_number=2,
        status=ManualTaskStatus.CONTENT_GENERATED,
        edited_text="Email final revisado.",
    )
    db.add(task)
    await db.commit()

    async def _fake_send_email(**_: object) -> SimpleNamespace:
        return SimpleNamespace(success=True, message_id="manual-task-message-id")

    monkeypatch.setattr(
        "integrations.unipile_client.unipile_client.send_email",
        _fake_send_email,
    )

    resp = await client.post(f"/tasks/{task.id}/send")

    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == ManualTaskStatus.SENT.value

    interaction_result = await db.execute(
        select(Interaction).where(Interaction.manual_task_id == task.id)
    )
    interaction = interaction_result.scalar_one()
    assert interaction.channel == Channel.EMAIL
    assert interaction.unipile_message_id == "manual-task-message-id"
