"""
core/database.py

Engine async SQLAlchemy + session factory para PostgreSQL.

Responsabilidades:
  - Criar o AsyncEngine com a DATABASE_URL de settings
  - Criar a AsyncSession factory
  - Prover get_session(tenant_id) como async generator com injeção de tenant via RLS
  - Prover init_db() para verificar a conexão no startup da API

Uso:
    async for session in get_session(tenant_id=uuid):
        result = await session.execute(select(Lead))
"""

from __future__ import annotations

import uuid
from typing import AsyncGenerator

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import settings

logger = structlog.get_logger()

# Engine assíncrono — pool padrão do SQLAlchemy (5 conns, max_overflow=10)
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_session(tenant_id: uuid.UUID) -> AsyncGenerator[AsyncSession, None]:
    """
    Async generator que abre uma sessão, injeta o tenant via RLS
    (SET LOCAL app.current_tenant_id) e garante commit/rollback/close.

    Uso com Depends():
        db: AsyncSession = Depends(lambda: get_session(tenant_id))
    """
    async with AsyncSessionLocal() as session:
        try:
            # Injeta o tenant_id no contexto da transação para o RLS do PostgreSQL.
            # SET LOCAL não aceita parâmetros bind ($1) no asyncpg — interpolamos
            # diretamente. Seguro: tenant_id é uuid.UUID validado (só hex + hifens).
            tid = str(tenant_id)
            await session.execute(text(f"SET LOCAL app.current_tenant_id = '{tid}'"))
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Verifica a conexão com o banco no startup.
    Levanta exceção se não conseguir conectar — o startup da API falhará explicitamente.
    """
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    logger.info("database.connected", url=settings.DATABASE_URL.split("@")[-1])
