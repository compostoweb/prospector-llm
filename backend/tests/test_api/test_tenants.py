"""
tests/test_api/test_tenants.py

Testes de integração para rotas de tenant:
  POST   /tenants                 — onboarding
  GET    /tenants/me              — dados do tenant autenticado
  PUT    /tenants/me/integrations — atualização parcial das integrações

Cobre:
  - Criação com slug único → 201 + api_key plaintext retornada
  - Criação com slug duplicado → 409
  - GET /me retorna dados do tenant autenticado
  - PUT /me/integrations atualiza campos parcialmente
  - Campos sensíveis (api_key_hash) não vazam nas respostas
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from models.cadence import Cadence

pytestmark = pytest.mark.asyncio


# ── POST /tenants ─────────────────────────────────────────────────────


async def test_create_tenant_returns_201_and_api_key(
    raw_client: AsyncClient,
    db,
) -> None:
    """Onboarding de tenant válido retorna 201 com api_key em plaintext."""
    from api.main import app
    from api.routes.auth import _get_raw_session

    app.dependency_overrides[_get_raw_session] = _make_db_override(db)

    resp = await raw_client.post(
        "/tenants",
        json={"name": "Empresa Alfa", "slug": "empresa-alfa"},
    )
    app.dependency_overrides.pop(_get_raw_session, None)

    assert resp.status_code == 201
    body = resp.json()
    assert body["slug"] == "empresa-alfa"
    assert body["name"] == "Empresa Alfa"
    assert body["is_active"] is True
    assert "api_key" in body
    assert len(body["api_key"]) >= 30  # token_urlsafe(32) → ~43 chars
    # api_key_hash nunca deve vazar
    assert "api_key_hash" not in body


async def test_create_tenant_duplicate_slug_returns_409(
    client: AsyncClient,
    db,
) -> None:
    """Slug já em uso retorna 409 Conflict."""
    from api.main import app
    from api.routes.tenants import _get_raw_session

    app.dependency_overrides[_get_raw_session] = _make_db_override(db)

    # Cria o primeiro
    await raw_post_tenant(client, db, slug="dup-slug-test")
    # Tenta criar de novo com o mesmo slug
    resp = await raw_post_tenant(client, db, slug="dup-slug-test")
    app.dependency_overrides.pop(_get_raw_session, None)

    assert resp.status_code == 409
    assert "Slug" in resp.json()["detail"] or "slug" in resp.json()["detail"].lower()


async def test_create_tenant_invalid_slug_returns_422(
    client: AsyncClient,
) -> None:
    """Slug com caracteres maiúsculos/especiais → 422 de validação Pydantic."""
    resp = await client.post(
        "/tenants",
        json={"name": "Empresa", "slug": "Empresa_Com_MAIUSCULA"},
    )
    assert resp.status_code == 422


async def test_create_tenant_short_name_returns_422(
    client: AsyncClient,
) -> None:
    """Nome com menos de 2 chars → 422."""
    resp = await client.post(
        "/tenants",
        json={"name": "X", "slug": "slug-ok"},
    )
    assert resp.status_code == 422


# ── GET /tenants/me ───────────────────────────────────────────────────


async def test_get_me_returns_tenant_data(
    client: AsyncClient,
    tenant,
) -> None:
    """GET /tenants/me retorna dados do tenant autenticado."""
    resp = await client.get("/tenants/me")
    assert resp.status_code == 200
    body = resp.json()
    assert body["slug"] == "tenant-teste"
    assert body["name"] == "Tenant Teste"
    assert body["is_active"] is True
    assert "id" in body
    assert "created_at" in body
    # Campo sensível não deve vazar
    assert "api_key_hash" not in body
    assert "api_key" not in body


async def test_get_me_without_auth_returns_401(
    raw_client: AsyncClient,
) -> None:
    """GET /tenants/me sem token → 401."""
    resp = await raw_client.get("/tenants/me")
    assert resp.status_code == 401


# ── PUT /tenants/me/integrations ─────────────────────────────────────


async def test_update_integrations_pipedrive(
    client: AsyncClient,
    tenant,
) -> None:
    """Atualiza campos Pipedrive — resposta reflete os campos atualizados."""
    resp = await client.put(
        "/tenants/me/integrations",
        json={
            "pipedrive_domain": "minhaempresa",
            "pipedrive_api_token": "tok_123",
            "pipedrive_owner_id": 42,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["pipedrive_domain"] == "minhaempresa"
    assert body["pipedrive_owner_id"] == 42


async def test_update_integrations_rate_limits(
    client: AsyncClient,
    tenant,
) -> None:
    """Atualiza limites de rate — valores refletidos na resposta."""
    resp = await client.put(
        "/tenants/me/integrations",
        json={
            "limit_linkedin_connect": 15,
            "limit_linkedin_dm": 30,
            "limit_email": 200,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["limit_linkedin_connect"] == 15
    assert body["limit_linkedin_dm"] == 30
    assert body["limit_email"] == 200


async def test_update_integrations_partial_only_touches_sent_fields(
    client: AsyncClient,
    tenant,
) -> None:
    """PATCH semântico: campos não enviados permanecem None/default."""
    # Primeiro: define notify_email
    await client.put(
        "/tenants/me/integrations",
        json={"notify_email": "adriano@compostoweb.com.br"},
    )
    # Segundo: atualiza só pipedrive_domain — notify_email não deve mudar
    resp = await client.put(
        "/tenants/me/integrations",
        json={"pipedrive_domain": "composto"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["pipedrive_domain"] == "composto"
    # notify_email foi definido na chamada anterior e deve persistir
    assert body["notify_email"] == "adriano@compostoweb.com.br"


async def test_update_integrations_limit_too_high_returns_422(
    client: AsyncClient,
    tenant,
) -> None:
    """Limite acima do máximo permitido → 422."""
    resp = await client.put(
        "/tenants/me/integrations",
        json={"limit_linkedin_connect": 999},
    )
    assert resp.status_code == 422


async def test_update_integrations_unipile_accounts(
    client: AsyncClient,
    tenant,
) -> None:
    """Atualiza account IDs da Unipile."""
    resp = await client.put(
        "/tenants/me/integrations",
        json={
            "unipile_linkedin_account_id": "li_acc_abc123",
            "unipile_gmail_account_id": "gmail_acc_xyz789",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["unipile_linkedin_account_id"] == "li_acc_abc123"
    assert body["unipile_gmail_account_id"] == "gmail_acc_xyz789"


async def test_update_integrations_propagates_llm_defaults_to_existing_cadences(
    client: AsyncClient,
    db,
    tenant,
) -> None:
    mixed = Cadence(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Cadência Mista",
        cadence_type="mixed",
        llm_provider="openai",
        llm_model="gpt-4o-mini",
        llm_temperature=0.7,
        llm_max_tokens=512,
    )
    cold_email = Cadence(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Campanha E-mail",
        cadence_type="email_only",
        llm_provider="openai",
        llm_model="gpt-4o-mini",
        llm_temperature=0.7,
        llm_max_tokens=512,
    )
    db.add(mixed)
    db.add(cold_email)
    await db.flush()

    resp = await client.put(
        "/tenants/me/integrations",
        json={
            "llm_default_provider": "openai",
            "llm_default_model": "gpt-5.4-mini",
            "llm_default_temperature": 0.3,
            "llm_default_max_tokens": 2048,
            "cold_email_llm_provider": "openai",
            "cold_email_llm_model": "gpt-5.4-mini",
            "cold_email_llm_temperature": 0.2,
            "cold_email_llm_max_tokens": 640,
        },
    )
    assert resp.status_code == 200

    result = await db.execute(select(Cadence).order_by(Cadence.name.asc()))
    cadences = result.scalars().all()
    assert cadences[0].llm_model == "gpt-5.4-mini"
    assert cadences[0].llm_temperature == 0.2
    assert cadences[0].llm_max_tokens == 640
    assert cadences[1].llm_model == "gpt-5.4-mini"
    assert cadences[1].llm_temperature == 0.3
    assert cadences[1].llm_max_tokens == 2048


# ── Helpers ───────────────────────────────────────────────────────────


def _make_db_override(db):
    """Retorna async gen function que FastAPI reconhece como dependency generator."""

    async def _dep():
        yield db

    return _dep


async def raw_post_tenant(client: AsyncClient, db, slug: str):
    """Reutilizável para tentar criar tenants sem override de session."""
    from api.main import app
    from api.routes.tenants import _get_raw_session

    app.dependency_overrides[_get_raw_session] = _make_db_override(db)
    resp = await client.post(
        "/tenants",
        json={"name": "Empresa Teste", "slug": slug},
    )
    app.dependency_overrides.pop(_get_raw_session, None)
    return resp


@pytest.fixture
async def raw_client(db):
    """Cliente HTTP sem headers de autenticação."""
    from httpx import ASGITransport, AsyncClient

    from api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
