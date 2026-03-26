import asyncio
import sqlalchemy as sa
from core.database import engine


async def main() -> None:
    async with engine.connect() as conn:
        # Check all channel-related enums
        for enum_name in ("cadence_step_channel", "interaction_channel", "channel", "lead_source"):
            r = await conn.execute(sa.text(
                f"SELECT e.enumlabel FROM pg_enum e "
                f"JOIN pg_type t ON e.enumtypid = t.oid "
                f"WHERE t.typname = '{enum_name}' "
                f"ORDER BY e.enumsortorder"
            ))
            values = [row[0] for row in r]
            print(f"{enum_name}: {values}")


asyncio.run(main())
