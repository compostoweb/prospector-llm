"""
tests/test_api/test_leads.py

Testes de integração para GET/POST/PATCH/DELETE /leads e sub-rotas.
"""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import LeadStatus


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


# ── POST /leads ───────────────────────────────────────────────────────

async def test_create_lead(client: AsyncClient):
    resp = await client.post("/leads", json=_lead_payload())
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "João Silva"
    assert data["company"] == "Acme Corp"
    assert data["status"] == LeadStatus.RAW.value
    assert "id" in data


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
    await client.post("/leads", json=_lead_payload(linkedin_url="https://linkedin.com/in/filter-test"))
    resp = await client.get("/leads", params={"status": "raw"})
    assert resp.status_code == 200
    data = resp.json()
    assert all(item["status"] == "raw" for item in data["items"])


async def test_list_leads_pagination(client: AsyncClient):
    resp = await client.get("/leads", params={"page": 1, "page_size": 2})
    assert resp.status_code == 200
    assert len(resp.json()["items"]) <= 2


# ── GET /leads/{id} ───────────────────────────────────────────────────

async def test_get_lead(client: AsyncClient):
    created = (await client.post("/leads", json=_lead_payload(linkedin_url="https://linkedin.com/in/get-test"))).json()
    resp = await client.get(f"/leads/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


async def test_get_lead_not_found(client: AsyncClient):
    import uuid
    resp = await client.get(f"/leads/{uuid.uuid4()}")
    assert resp.status_code == 404


# ── PATCH /leads/{id} ────────────────────────────────────────────────

async def test_update_lead(client: AsyncClient):
    created = (await client.post("/leads", json=_lead_payload(linkedin_url="https://linkedin.com/in/update-test"))).json()
    resp = await client.patch(f"/leads/{created['id']}", json={"company": "Nova Empresa Ltda"})
    assert resp.status_code == 200
    assert resp.json()["company"] == "Nova Empresa Ltda"


async def test_update_lead_status(client: AsyncClient):
    created = (await client.post("/leads", json=_lead_payload(linkedin_url="https://linkedin.com/in/status-test"))).json()
    resp = await client.patch(f"/leads/{created['id']}", json={"status": "enriched"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "enriched"


# ── DELETE /leads/{id} ────────────────────────────────────────────────

async def test_archive_lead(client: AsyncClient):
    created = (await client.post("/leads", json=_lead_payload(linkedin_url="https://linkedin.com/in/archive-test"))).json()
    resp = await client.delete(f"/leads/{created['id']}")
    assert resp.status_code == 204

    # Verifica que foi arquivado (não apagado)
    get_resp = await client.get(f"/leads/{created['id']}")
    assert get_resp.status_code == 200
    assert get_resp.json()["status"] == LeadStatus.ARCHIVED.value


# ── POST /leads/{id}/enroll ───────────────────────────────────────────

async def test_enroll_lead_cadence_not_found(client: AsyncClient):
    import uuid
    created = (await client.post("/leads", json=_lead_payload(linkedin_url="https://linkedin.com/in/enroll-test"))).json()
    resp = await client.post(
        f"/leads/{created['id']}/enroll",
        json={"cadence_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 404


async def test_enroll_archived_lead_fails(client: AsyncClient):
    import uuid
    created = (await client.post("/leads", json=_lead_payload(linkedin_url="https://linkedin.com/in/enroll-archived"))).json()
    await client.delete(f"/leads/{created['id']}")
    resp = await client.post(
        f"/leads/{created['id']}/enroll",
        json={"cadence_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 422


# ── GET /leads/{id}/interactions ──────────────────────────────────────

async def test_list_interactions_empty(client: AsyncClient):
    created = (await client.post("/leads", json=_lead_payload(linkedin_url="https://linkedin.com/in/interactions-test"))).json()
    resp = await client.get(f"/leads/{created['id']}/interactions")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0
