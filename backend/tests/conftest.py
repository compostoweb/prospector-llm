"""
tests/conftest.py

Fixtures centrais para todos os testes do Prospector.

Estratégia:
  - Engine aponta para DATABASE_URL de settings (ou TEST_DATABASE_URL se definido)
  - Tabelas criadas com Base.metadata.create_all (sem RLS — testa a lógica da app)
  - Por teste: conexão wrappada em uma transação que faz rollback ao final
  - FastAPI dependencies são sobrescritas via app.dependency_overrides
  - Requisições HTTP via httpx.AsyncClient com ASGITransport

Variável opcional: TEST_DATABASE_URL (default: settings.DATABASE_URL)
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    AsyncTransaction,
    create_async_engine,
)

# Importa todos os models para garantir que estão no Base.metadata
import models.cadence  # noqa: F401  # pyright: ignore[reportUnusedImport]
import models.cadence_step  # noqa: F401  # pyright: ignore[reportUnusedImport]
import models.content_gallery_image  # noqa: F401  # pyright: ignore[reportUnusedImport]
import models.interaction  # noqa: F401  # pyright: ignore[reportUnusedImport]
import models.lead  # noqa: F401  # pyright: ignore[reportUnusedImport]
import models.lead_email  # noqa: F401  # pyright: ignore[reportUnusedImport]
import models.tenant_user  # noqa: F401  # pyright: ignore[reportUnusedImport]
from api.dependencies import (
    get_current_tenant_id,
    get_effective_tenant_id,
    get_session,
    get_session_flexible,
    get_session_no_auth,
)
from api.main import app
from core.config import settings
from core.security import UserPayload, create_access_token, create_user_token
from models.base import Base
from models.enums import TenantRole
from models.tenant import Tenant, TenantIntegration
from models.tenant_user import TenantUser
from models.user import User

_TEST_DB_URL = os.getenv("TEST_DATABASE_URL", settings.DATABASE_URL)


# ── Engine de teste (scope=session) ──────────────────────────────────


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Cria o engine e garante o schema mínimo necessário para a sessão de testes."""
    engine = create_async_engine(
        _TEST_DB_URL,
        echo=False,
        pool_pre_ping=True,
        connect_args={"timeout": 10},
    )
    async with engine.begin() as conn:
        await conn.execute(text("SET lock_timeout = '10s'"))
        await conn.execute(text("SET statement_timeout = '30s'"))
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


# ── tenant_id fixo por sessão ─────────────────────────────────────────


@pytest.fixture(scope="session")
def tenant_id() -> uuid.UUID:
    return uuid.uuid4()


# ── DB session com rollback por teste ─────────────────────────────────


@pytest_asyncio.fixture
async def db(test_engine: AsyncEngine, tenant_id: uuid.UUID) -> AsyncGenerator[AsyncSession, None]:
    """
    Abre uma conexão e começa uma transação que será revertida ao final.
    Injeta o tenant_id via SET LOCAL para que os selects filtrem corretamente.
    """
    conn: AsyncConnection = await test_engine.connect()
    trans: AsyncTransaction = await conn.begin()
    # Desabilita RLS (se houver) para simplificar testes
    try:
        await conn.execute(text("SET row_security = off"))
    except Exception:
        pass  # PostgreSQL pode não ter RLS configurado no banco de testes
    session = AsyncSession(
        bind=conn,
        expire_on_commit=False,
        autoflush=False,
        join_transaction_mode="create_savepoint",
    )
    yield session
    await session.close()
    await trans.rollback()
    await conn.close()


# ── Tenant de teste ───────────────────────────────────────────────────


@pytest_asyncio.fixture
async def tenant(db: AsyncSession, tenant_id: uuid.UUID) -> Tenant:
    """Cria um Tenant e TenantIntegration no banco dentro da transação de teste."""
    t = Tenant(id=tenant_id, name="Tenant Teste", slug="tenant-teste")
    db.add(t)
    ti = TenantIntegration(tenant_id=tenant_id)
    db.add(ti)
    await db.flush()
    return t


# ── Token JWT e headers ───────────────────────────────────────────────


@pytest.fixture
def access_token(tenant_id: uuid.UUID) -> str:
    return create_access_token({"tenant_id": str(tenant_id)})


@pytest.fixture
def auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


@pytest_asyncio.fixture
async def superuser(db: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        email="admin@composto.test",
        name="Admin Geral",
        is_active=True,
        is_superuser=True,
    )
    db.add(user)
    await db.flush()
    return user


@pytest.fixture
def superuser_payload(superuser: User, tenant_id: uuid.UUID) -> UserPayload:
    return UserPayload(
        user_id=superuser.id,
        email=superuser.email,
        is_superuser=True,
        name=superuser.name,
        tenant_id=tenant_id,
        tenant_role=None,
    )


@pytest.fixture
def superuser_auth_headers(superuser: User, tenant_id: uuid.UUID) -> dict[str, str]:
    token = create_user_token(
        user_id=superuser.id,
        email=superuser.email,
        is_superuser=True,
        name=superuser.name,
        tenant_id=tenant_id,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def tenant_admin_user(db: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        email="tenant-admin@composto.test",
        name="Admin Tenant",
        is_active=True,
        is_superuser=False,
    )
    db.add(user)
    await db.flush()
    return user


@pytest_asyncio.fixture
async def tenant_admin_membership(
    db: AsyncSession,
    tenant: Tenant,
    tenant_admin_user: User,
) -> TenantUser:
    membership = TenantUser(
        tenant_id=tenant.id,
        user_id=tenant_admin_user.id,
        role=TenantRole.TENANT_ADMIN,
        is_active=True,
    )
    db.add(membership)
    await db.flush()
    return membership


@pytest.fixture
def tenant_admin_payload(tenant_admin_user: User, tenant_id: uuid.UUID) -> UserPayload:
    return UserPayload(
        user_id=tenant_admin_user.id,
        email=tenant_admin_user.email,
        is_superuser=False,
        name=tenant_admin_user.name,
        tenant_id=tenant_id,
        tenant_role=TenantRole.TENANT_ADMIN,
    )


# ── Cliente HTTP com overrides de dependências ────────────────────────


@pytest_asyncio.fixture
async def client(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    tenant: Tenant,  # garante que o tenant existe no DB antes do primeiro request
    auth_headers: dict[str, str],
) -> AsyncGenerator[AsyncClient, None]:
    """
    AsyncClient configurado com:
    - get_session sobrescrito para retornar a sessão de teste
    - get_current_tenant_id sobrescrito para retornar o tenant_id fixo
    - headers de autenticação incluídos por padrão
    """

    async def _override_session():
        yield db

    def _override_tenant_id():
        return tenant_id

    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[get_session_flexible] = _override_session
    app.dependency_overrides[get_session_no_auth] = _override_session
    app.dependency_overrides[get_current_tenant_id] = _override_tenant_id
    app.dependency_overrides[get_effective_tenant_id] = _override_tenant_id

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers=auth_headers,
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
