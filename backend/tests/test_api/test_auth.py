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
from urllib.parse import parse_qs, urlparse

import pytest
from httpx import ASGITransport, AsyncClient
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
    from api.routes.auth import _get_raw_session

    # Override a session de auth para usar o db de teste
    app.dependency_overrides[_get_raw_session] = _make_db_override(db)

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

    app.dependency_overrides[_get_raw_session] = _make_db_override(db)

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

    app.dependency_overrides[_get_raw_session] = _make_db_override(db)

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

    app.dependency_overrides[_get_raw_session] = _make_db_override(db)

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

    app.dependency_overrides[_get_raw_session] = _make_db_override(db)

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


async def test_google_callback_redirects_unregistered_email_to_frontend_error(
    raw_client: AsyncClient,
    db: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from api.routes import auth as auth_route

    async def _fake_redis_get(key: str) -> str | None:
        assert key == "google_oauth_state:state-123"
        return "1"

    async def _fake_redis_delete(key: str) -> None:
        assert key == "google_oauth_state:state-123"

    async def _fake_exchange_google_code_for_access_token(*, code: str, redirect_uri: str) -> str:
        assert code == "code-123"
        assert redirect_uri == auth_route.settings.GOOGLE_REDIRECT_URI
        return "google-access-token"

    async def _fake_fetch_google_userinfo(access_token_google: str) -> dict[str, object]:
        assert access_token_google == "google-access-token"
        return {
            "email": "nao-cadastrado@composto.test",
            "verified_email": True,
            "id": "google-user-123",
            "name": "Usuário Ausente",
        }

    app.dependency_overrides[auth_route._get_raw_session] = _make_db_override(db)
    monkeypatch.setattr(auth_route.settings, "FRONTEND_URL", "http://frontend.test")
    monkeypatch.setattr(auth_route.settings, "GOOGLE_CLIENT_ID", "google-client-id")
    monkeypatch.setattr(auth_route.settings, "GOOGLE_CLIENT_SECRET", "google-client-secret")
    monkeypatch.setattr(auth_route.redis_client, "get", _fake_redis_get)
    monkeypatch.setattr(auth_route.redis_client, "delete", _fake_redis_delete)
    monkeypatch.setattr(
        auth_route,
        "_exchange_google_code_for_access_token",
        _fake_exchange_google_code_for_access_token,
    )
    monkeypatch.setattr(auth_route, "_fetch_google_userinfo", _fake_fetch_google_userinfo)

    resp = await raw_client.get(
        "/auth/google/callback",
        params={"code": "code-123", "state": "state-123"},
    )
    app.dependency_overrides.pop(auth_route._get_raw_session, None)

    assert resp.status_code == 302
    location = resp.headers["location"]
    parsed = urlparse(location)
    query = parse_qs(parsed.query)
    assert location.startswith("http://frontend.test/auth/error?")
    assert query["error"] == ["email_not_registered"]
    assert query["message"] == ["Acesso negado. Seu email não está cadastrado no sistema."]


async def test_google_callback_redirects_invalid_state_to_frontend_error(
    raw_client: AsyncClient,
    db: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from api.routes import auth as auth_route

    async def _fake_redis_get(key: str) -> None:
        assert key == "google_oauth_state:state-expired"
        return None

    app.dependency_overrides[auth_route._get_raw_session] = _make_db_override(db)
    monkeypatch.setattr(auth_route.settings, "FRONTEND_URL", "http://frontend.test")
    monkeypatch.setattr(auth_route.settings, "GOOGLE_CLIENT_ID", "google-client-id")
    monkeypatch.setattr(auth_route.settings, "GOOGLE_CLIENT_SECRET", "google-client-secret")
    monkeypatch.setattr(auth_route.redis_client, "get", _fake_redis_get)

    resp = await raw_client.get(
        "/auth/google/callback",
        params={"code": "code-123", "state": "state-expired"},
    )
    app.dependency_overrides.pop(auth_route._get_raw_session, None)

    assert resp.status_code == 302
    location = resp.headers["location"]
    parsed = urlparse(location)
    query = parse_qs(parsed.query)
    assert location.startswith("http://frontend.test/auth/error?")
    assert query["error"] == ["invalid_state"]


async def test_google_callback_redirects_google_access_denied_to_frontend_error(
    raw_client: AsyncClient,
    db: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from api.routes import auth as auth_route

    app.dependency_overrides[auth_route._get_raw_session] = _make_db_override(db)
    monkeypatch.setattr(auth_route.settings, "FRONTEND_URL", "http://frontend.test")

    resp = await raw_client.get(
        "/auth/google/callback",
        params={
            "state": "state-123",
            "error": "access_denied",
            "error_description": "O usuario cancelou a autenticacao.",
        },
    )
    app.dependency_overrides.pop(auth_route._get_raw_session, None)

    assert resp.status_code == 302
    location = resp.headers["location"]
    parsed = urlparse(location)
    query = parse_qs(parsed.query)
    assert location.startswith("http://frontend.test/auth/error?")
    assert query["error"] == ["oauth_access_denied"]


# ── Helper ────────────────────────────────────────────────────────────

def _make_db_override(db: AsyncSession):
    """Retorna async gen function que FastAPI reconhece como dependency generator."""
    async def _dep():
        yield db
    return _dep
