import asyncio
import sqlalchemy as sa
from core.database import engine


async def main() -> None:
    async with engine.connect() as conn:
        r = await conn.execute(
            sa.text("SELECT typname FROM pg_type WHERE typtype = 'e' ORDER BY typname")
        )
        print("Enums no banco:")
        for row in r:
            print(" ", row[0])


asyncio.run(main())
