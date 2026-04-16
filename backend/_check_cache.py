"""Quick check of linkedin_search_params cache in DB."""

import asyncio
import os

os.environ.setdefault("ENV", "dev")


async def check():
    from sqlalchemy import func, select

    from core.database import AsyncSessionLocal
    from models.linkedin_search_param import LinkedInSearchParam

    async with AsyncSessionLocal() as db:
        total = (await db.execute(select(func.count()).select_from(LinkedInSearchParam))).scalar()
        loc = (
            await db.execute(
                select(func.count())
                .select_from(LinkedInSearchParam)
                .where(LinkedInSearchParam.param_type == "LOCATION")
            )
        ).scalar()
        ind = (
            await db.execute(
                select(func.count())
                .select_from(LinkedInSearchParam)
                .where(LinkedInSearchParam.param_type == "INDUSTRY")
            )
        ).scalar()
        print(f"Total: {total}  |  LOCATION: {loc}  |  INDUSTRY: {ind}")


asyncio.run(check())
