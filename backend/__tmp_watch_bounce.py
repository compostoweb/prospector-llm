import asyncio
import json
from datetime import datetime
from sqlalchemy import select
from core.database import AsyncSessionLocal
from models.lead import Lead

LEAD_ID = '15b02ccf-2359-47bb-92ad-5d00978323c9'
TARGET_EMAIL = 'bounce-test-1776892293@prospector-bounce-1776892293.invalid'

async def main():
    for attempt in range(24):
        async with AsyncSessionLocal() as db:
            lead = (await db.execute(select(Lead).where(Lead.id == LEAD_ID))).scalar_one_or_none()
            payload = {
                'attempt': attempt + 1,
                'checked_at': datetime.utcnow().isoformat(),
                'target_email': TARGET_EMAIL,
                'found': lead is not None,
                'email_bounced_at': lead.email_bounced_at.isoformat() if lead and lead.email_bounced_at else None,
                'email_bounce_type': lead.email_bounce_type if lead else None,
            }
            print(json.dumps(payload), flush=True)
            if lead and lead.email_bounced_at:
                return
        await asyncio.sleep(15)

asyncio.run(main())
