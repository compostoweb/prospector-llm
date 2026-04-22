import asyncio
import json
import time
from sqlalchemy import select
from core.database import AsyncSessionLocal
from integrations.unipile_client import unipile_client
from models.lead import Lead
from models.enums import LeadSource, LeadStatus

TENANT_ID = 'c00948b6-76d7-4d9c-8cd5-ba90663af6ac'
UNIPILE_ACCOUNT_ID = 'immfTjFkR2e4Z3vnpka6mw'

async def main():
    stamp = int(time.time())
    target_email = f'bounce-test-{stamp}@prospector-bounce-{stamp}.invalid'
    async with AsyncSessionLocal() as db:
        lead = Lead(
            tenant_id=TENANT_ID,
            name=f'Teste Bounce {stamp}',
            company='Bounce QA',
            email_corporate=target_email,
            source=LeadSource.MANUAL,
            status=LeadStatus.RAW,
        )
        db.add(lead)
        await db.commit()
        await db.refresh(lead)

    result = await unipile_client.send_email(
        account_id=UNIPILE_ACCOUNT_ID,
        to_email=target_email,
        subject=f'Teste bounce {stamp}',
        body_html=f'<p>Teste controlado de bounce {stamp}</p>',
    )

    print(json.dumps({
        'lead_id': str(lead.id),
        'target_email': target_email,
        'message_id': result.message_id,
        'success': result.success,
    }))

asyncio.run(main())
