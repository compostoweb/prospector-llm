"""Quick script to check DB state for migration 017."""
import asyncio
import os

os.environ["ENV"] = "dev"
from core.config import settings


async def check() -> None:
    import asyncpg

    conn = await asyncpg.connect(settings.DATABASE_URL.replace("+asyncpg", ""))

    cols = await conn.fetch(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'leads' AND column_name IN ('linkedin_connection_status', 'linkedin_connected_at')"
    )
    print("Lead columns:", [r["column_name"] for r in cols])

    tables = await conn.fetch(
        "SELECT tablename FROM pg_tables WHERE tablename = 'manual_tasks'"
    )
    print("manual_tasks table:", bool(tables))

    mode_col = await conn.fetch(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'cadences' AND column_name = 'mode'"
    )
    print("cadences.mode:", bool(mode_col))

    enums = await conn.fetch(
        "SELECT typname FROM pg_type WHERE typname = 'manual_task_status'"
    )
    print("manual_task_status enum:", bool(enums))

    # Check alembic_version
    ver = await conn.fetch("SELECT version_num FROM alembic_version")
    print("alembic_version:", [r["version_num"] for r in ver])

    await conn.close()


asyncio.run(check())
