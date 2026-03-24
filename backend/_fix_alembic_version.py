"""Temporary script to update alembic_version from long IDs to short IDs."""
import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from core.config import settings


async def main() -> None:
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "UPDATE alembic_version "
                "SET version_num = '003' "
                "WHERE version_num = '003_add_users'"
            )
        )
        result = await conn.execute(text("SELECT version_num FROM alembic_version"))
        for r in result.fetchall():
            print(f"Updated version: {r[0]}")
    await engine.dispose()


asyncio.run(main())
