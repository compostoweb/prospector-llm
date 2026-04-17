"""
tests/test_api/test_cadences.py

Testes de integração para GET/POST/PATCH/DELETE /cadences.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from models.tenant import TenantIntegration

pytestmark = pytest.mark.asyncio


# ── Helpers ───────────────────────────────────────────────────────────


def _cadence_payload(**overrides) -> dict:
    base = {
        "name": "Cadência Teste",
        "description": "Cadência criada nos testes",
        "allow_personal_email": False,
        "llm": {
            "provider": "openai",
            "model": "gpt-4o-mini",
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
    assert data["llm_model"] == "gpt-4o-mini"
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
    """gpt-4o-mini com provider gemini deve falhar no validator."""
    payload = _cadence_payload(
        llm={"provider": "gemini", "model": "gpt-4o-mini", "temperature": 0.5, "max_tokens": 512}
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


async def test_get_cadence_not_found(client: AsyncClient):
    resp = await client.get(f"/cadences/{uuid.uuid4()}")
    assert resp.status_code == 404


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


# ── DELETE /cadences/{id} ─────────────────────────────────────────────


async def test_deactivate_cadence(client: AsyncClient):
    created = await _create_cadence(client)
    resp = await client.delete(f"/cadences/{created['id']}")
    assert resp.status_code == 204

    # Verifica que a cadência foi removida
    get_resp = await client.get(f"/cadences/{created['id']}")
    assert get_resp.status_code == 404
