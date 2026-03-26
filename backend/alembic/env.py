"""
alembic/env.py

Configuração do Alembic para migrations async com asyncpg.

Responsabilidades:
  - Carregar DATABASE_URL de core/config.settings (nunca hardcoded)
  - Importar todos os models para que o autogenerate detecte as tabelas
  - Rodar em modo assíncrono (asyncpg) via asyncio.run()
  - Suportar tanto offline (SQL script) quanto online (execução direta)
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# ── Importar settings ────────────────────────────────────────────────
from core.config import settings

# ── Importar TODOS os models para o autogenerate funcionar ──────────
# Cada import adiciona os models ao metadata da Base
from models.base import Base  # noqa: F401
from models.audio_file import AudioFile  # noqa: F401
from models.cadence import Cadence  # noqa: F401
from models.cadence_step import CadenceStep  # noqa: F401
from models.interaction import Interaction  # noqa: F401
from models.lead import Lead  # noqa: F401
from models.lead_list import LeadList  # noqa: F401
from models.lead_tag import LeadTag  # noqa: F401
from models.manual_task import ManualTask  # noqa: F401
from models.sandbox import SandboxRun, SandboxStep  # noqa: F401
from models.tenant import Tenant, TenantIntegration  # noqa: F401
from models.user import User  # noqa: F401

# Objeto de configuração do Alembic (lê alembic.ini)
config = context.config

# Configura logging via alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata alvo para autogenerate
target_metadata = Base.metadata

# Injeta a DATABASE_URL de settings no config do Alembic
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)


def run_migrations_offline() -> None:
    """
    Modo offline: gera SQL sem conectar ao banco.
    Útil para gerar scripts de migration para revisar antes de aplicar.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Modo online async — usa asyncpg via async_engine_from_config."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Ponto de entrada online — delega para a coroutine async."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
