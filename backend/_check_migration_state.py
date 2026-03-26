import asyncio
import sqlalchemy as sa
from core.database import engine


async def main() -> None:
    async with engine.connect() as conn:
        # Check alembic version
        r = await conn.execute(sa.text("SELECT version_num FROM alembic_version"))
        print("Alembic version:", [row[0] for row in r])

        # Check if linkedin_recent_posts_json column exists
        r2 = await conn.execute(sa.text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'leads' AND column_name = 'linkedin_recent_posts_json'"
        ))
        rows = r2.fetchall()
        print("linkedin_recent_posts_json exists:", bool(rows))

        # Check enum values for cadence_step_channel
        r3 = await conn.execute(sa.text(
            "SELECT e.enumlabel FROM pg_enum e "
            "JOIN pg_type t ON e.enumtypid = t.oid "
            "WHERE t.typname = 'cadence_step_channel' "
            "ORDER BY e.enumsortorder"
        ))
        print("cadence_step_channel values:", [row[0] for row in r3])


asyncio.run(main())
