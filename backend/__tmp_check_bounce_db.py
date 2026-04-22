import asyncio
from sqlalchemy import select
from core.database import AsyncSessionLocal
from models.lead import Lead

LEAD_ID = '15b02ccf-2359-47bb-92ad-5d00978323c9'

async def main():
    async with AsyncSessionLocal() as db:
        lead = (await db.execute(select(Lead).where(Lead.id == LEAD_ID))).scalar_one()
        print('LEAD_ID', lead.id)
        print('EMAIL', lead.email_corporate)
        print('BOUNCED_AT', lead.email_bounced_at.isoformat() if lead.email_bounced_at else None)
        print('BOUNCE_TYPE', lead.email_bounce_type)

asyncio.run(main())
