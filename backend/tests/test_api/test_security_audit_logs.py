from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.main import app
from api.routes.auth import hash_api_key
from core.security import create_user_token, require_superuser
from integrations.s3_client import S3Client
from models.content_post import ContentPost
from models.security_audit_log import SecurityAuditLog
from models.tenant import Tenant, TenantIntegration
from models.user import User

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def raw_client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


async def test_login_failure_writes_security_audit_log(
    raw_client: AsyncClient,
    db: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    from api.routes import auth as auth_route

    tenant = Tenant(
        id=tenant_id,
        name="Auth Audit",
        slug="auth-audit",
        api_key_hash=hash_api_key("correct-secret-key"),
        is_active=True,
    )
    db.add(tenant)
    db.add(TenantIntegration(tenant_id=tenant.id))
    await db.flush()

    app.dependency_overrides[auth_route._get_raw_session] = lambda: db
    try:
        response = await raw_client.post(
            "/auth/token",
            data={"username": "auth-audit", "password": "wrong-secret-key"},
        )
    finally:
        app.dependency_overrides.pop(auth_route._get_raw_session, None)

    assert response.status_code == 401
    result = await db.execute(
        select(SecurityAuditLog).where(SecurityAuditLog.event_type == "auth.login")
    )
    log = result.scalar_one()
    assert log.status == "failure"
    assert log.scope_tenant_id == tenant.id
    assert log.message == "Credenciais invalidas."


async def test_admin_user_create_writes_security_audit_log(
    raw_client: AsyncClient,
    db: AsyncSession,
    superuser_payload,
) -> None:
    from api.routes import admin_users as admin_users_route

    app.dependency_overrides[admin_users_route._get_raw_session] = lambda: db
    app.dependency_overrides[require_superuser] = lambda: superuser_payload
    try:
        response = await raw_client.post(
            "/admin/users",
            json={"email": "novo-admin@example.com", "name": "Novo Admin", "is_superuser": False},
        )
    finally:
        app.dependency_overrides.pop(admin_users_route._get_raw_session, None)
        app.dependency_overrides.pop(require_superuser, None)

    assert response.status_code == 201
    result = await db.execute(
        select(SecurityAuditLog).where(SecurityAuditLog.event_type == "admin.user_create")
    )
    log = result.scalar_one()
    assert log.actor_user_id == superuser_payload.user_id
    assert log.status == "success"
    assert log.resource_type == "user"


async def test_upload_post_image_writes_security_audit_log(
    client: AsyncClient,
    db: AsyncSession,
    tenant_id: uuid.UUID,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    post = ContentPost(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        title="Post audit",
        body="Texto",
        pillar="case",
        status="draft",
    )
    db.add(post)
    await db.flush()

    def fake_upload_bytes(self: S3Client, data: bytes, key: str, content_type: str) -> str:
        return f"https://example.com/{key}"

    monkeypatch.setattr(S3Client, "upload_bytes", fake_upload_bytes)

    response = await client.post(
        f"/api/content/posts/{post.id}/upload-image",
        files={"file": ("imagem.png", b"\x89PNG\r\n\x1a\nrest", "image/png")},
    )

    assert response.status_code == 200
    result = await db.execute(
        select(SecurityAuditLog).where(
            SecurityAuditLog.event_type == "content.post_image_upload",
            SecurityAuditLog.resource_id == str(post.id),
        )
    )
    log = result.scalar_one()
    assert log.scope_tenant_id == tenant_id
    assert log.status == "success"


async def test_list_security_audit_logs_scopes_to_tenant_user(
    raw_client: AsyncClient,
    db: AsyncSession,
    tenant_admin_user: User,
    tenant_admin_membership,
    tenant_id: uuid.UUID,
) -> None:
    from api.routes import security_audit_logs as security_audit_logs_route

    other_tenant_id = uuid.uuid4()
    db.add(Tenant(id=other_tenant_id, name="Outro", slug="outro-tenant"))
    db.add(TenantIntegration(tenant_id=other_tenant_id))
    await db.flush()

    db.add_all(
        [
            SecurityAuditLog(
                scope_tenant_id=tenant_id,
                actor_user_id=tenant_admin_user.id,
                event_type="tenant.visible",
                resource_type="demo",
                action="inspect",
                status="success",
            ),
            SecurityAuditLog(
                scope_tenant_id=other_tenant_id,
                actor_user_id=None,
                event_type="tenant.hidden",
                resource_type="demo",
                action="inspect",
                status="success",
            ),
        ]
    )
    await db.flush()

    token = create_user_token(
        user_id=tenant_admin_user.id,
        email=tenant_admin_user.email,
        is_superuser=False,
        name=tenant_admin_user.name,
        tenant_id=tenant_id,
    )

    app.dependency_overrides[security_audit_logs_route._get_raw_session] = lambda: db
    try:
        response = await raw_client.get(
            "/security-audit-logs",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app.dependency_overrides.pop(security_audit_logs_route._get_raw_session, None)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["event_type"] == "tenant.visible"