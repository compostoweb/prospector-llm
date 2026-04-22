import asyncio
from sqlalchemy import delete
from core.database import AsyncSessionLocal
from models.lead import Lead

LEAD_ID = '15b02ccf-2359-47bb-92ad-5d00978323c9'

async def main():
    async with AsyncSessionLocal() as db:
        await db.execute(delete(Lead).where(Lead.id == LEAD_ID))
        await db.commit()
        print('DELETED', LEAD_ID)

asyncio.run(main())
