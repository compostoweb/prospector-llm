"""
tests/test_api/test_auth.py

Testes de integração para POST /auth/token.

Cobre:
  - Login com slug + api_key válidos → 200 + JWT
  - Slug inexistente → 401
  - Api_key errada → 401
  - Tenant inativo → 401
  - Token JWT gerado contém tenant_id no payload
  - Usando o token em endpoint protegido → 200
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import timedelta

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from api.main import app
from api.routes.auth import hash_api_key
from models.tenant import Tenant, TenantIntegration

pytestmark = pytest.mark.asyncio


# ── Fixture: tenant com api_key conhecida ─────────────────────────────

@pytest.fixture
async def tenant_with_key(db: AsyncSession, tenant_id: uuid.UUID) -> dict[str, str]:
    """
    Cria um Tenant extra com api_key_hash gerado — diferente do `tenant` padrão
    do conftest para evitar conflitos de slug.
    """
    plaintext = "test-api-key-super-secret-32chars!!"
    t = Tenant(
        id=tenant_id,
        name="Auth Teste",
        slug="auth-teste",
        api_key_hash=hash_api_key(plaintext),
        is_active=True,
    )
    db.add(t)
    db.add(TenantIntegration(tenant_id=tenant_id))
    await db.flush()
    return {"slug": "auth-teste", "api_key": plaintext}


@pytest.fixture
async def inactive_tenant(db: AsyncSession) -> dict[str, str]:
    """Cria um Tenant inativo para testar rejeição."""
    plaintext = "inactive-key-32chars-padding-xyz!!"
    t = Tenant(
        id=uuid.uuid4(),
        name="Inactive Tenant",
        slug="inactive-tenant",
        api_key_hash=hash_api_key(plaintext),
        is_active=False,
    )
    db.add(t)
    await db.flush()
    return {"slug": "inactive-tenant", "api_key": plaintext}


# ── Cliente sem auth headers (puro) ───────────────────────────────────

@pytest.fixture
async def raw_client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Cliente HTTP sem headers de autenticação pré-configurados."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


# ── Testes ────────────────────────────────────────────────────────────

async def test_login_returns_bearer_token(
    raw_client: AsyncClient,
    tenant_with_key: dict[str, str],
    db: AsyncSession,
) -> None:
    """Login válido retorna access_token e token_type=bearer."""
    from api.dependencies import get_current_tenant_id, get_session
    from api.routes.auth import _get_raw_session

    # Override a session de auth para usar o db de teste
    app.dependency_overrides[_get_raw_session] = lambda: _override_db(db)

    resp = await raw_client.post(
        "/auth/token",
        data={
            "username": tenant_with_key["slug"],
            "password": tenant_with_key["api_key"],
        },
    )
    app.dependency_overrides.pop(_get_raw_session, None)

    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert len(body["access_token"]) > 20


async def test_login_token_contains_tenant_id(
    raw_client: AsyncClient,
    tenant_with_key: dict[str, str],
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> None:
    """O JWT gerado contém o tenant_id correto no payload."""
    from api.routes.auth import _get_raw_session
    from core.security import decode_token

    app.dependency_overrides[_get_raw_session] = lambda: _override_db(db)

    resp = await raw_client.post(
        "/auth/token",
        data={
            "username": tenant_with_key["slug"],
            "password": tenant_with_key["api_key"],
        },
    )
    app.dependency_overrides.pop(_get_raw_session, None)

    assert resp.status_code == 200
    token = resp.json()["access_token"]
    payload = decode_token(token)
    assert payload["tenant_id"] == str(tenant_id)


async def test_login_wrong_slug_returns_401(
    raw_client: AsyncClient,
    tenant_with_key: dict[str, str],
    db: AsyncSession,
) -> None:
    """Slug inexistente → 401 (sem revelar qual campo está errado)."""
    from api.routes.auth import _get_raw_session

    app.dependency_overrides[_get_raw_session] = lambda: _override_db(db)

    resp = await raw_client.post(
        "/auth/token",
        data={"username": "slug-inexistente", "password": tenant_with_key["api_key"]},
    )
    app.dependency_overrides.pop(_get_raw_session, None)

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Credenciais inválidas."


async def test_login_wrong_api_key_returns_401(
    raw_client: AsyncClient,
    tenant_with_key: dict[str, str],
    db: AsyncSession,
) -> None:
    """Api_key errada → 401."""
    from api.routes.auth import _get_raw_session

    app.dependency_overrides[_get_raw_session] = lambda: _override_db(db)

    resp = await raw_client.post(
        "/auth/token",
        data={"username": tenant_with_key["slug"], "password": "senha-errada"},
    )
    app.dependency_overrides.pop(_get_raw_session, None)

    assert resp.status_code == 401


async def test_login_inactive_tenant_returns_401(
    raw_client: AsyncClient,
    inactive_tenant: dict[str, str],
    db: AsyncSession,
) -> None:
    """Tenant inativo → 401 mesmo com credenciais corretas."""
    from api.routes.auth import _get_raw_session

    app.dependency_overrides[_get_raw_session] = lambda: _override_db(db)

    resp = await raw_client.post(
        "/auth/token",
        data={
            "username": inactive_tenant["slug"],
            "password": inactive_tenant["api_key"],
        },
    )
    app.dependency_overrides.pop(_get_raw_session, None)

    assert resp.status_code == 401


async def test_token_authenticates_protected_endpoint(
    client: AsyncClient,
) -> None:
    """JWT válido permite acesso ao endpoint GET /tenants/me."""
    resp = await client.get("/tenants/me")
    assert resp.status_code == 200


async def test_no_token_returns_401(raw_client: AsyncClient) -> None:
    """Request sem Authorization header → 401."""
    resp = await raw_client.get("/tenants/me")
    assert resp.status_code == 401


async def test_invalid_token_returns_401(raw_client: AsyncClient) -> None:
    """Token JWT malformado → 401."""
    resp = await raw_client.get(
        "/tenants/me",
        headers={"Authorization": "Bearer token.invalido.aqui"},
    )
    assert resp.status_code == 401


# ── Helper ────────────────────────────────────────────────────────────

async def _override_db(db: AsyncSession):
    """Gerador que entrega o db de teste para o override de _get_raw_session."""
    yield db
