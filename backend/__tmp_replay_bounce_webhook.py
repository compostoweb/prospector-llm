import asyncio
from types import SimpleNamespace
from sqlalchemy import select
from core.database import AsyncSessionLocal
from api.webhooks import unipile as unipile_webhook
from models.lead import Lead

LEAD_ID = '15b02ccf-2359-47bb-92ad-5d00978323c9'
ACCOUNT_ID = 'immfTjFkR2e4Z3vnpka6mw'

PAYLOAD = {
    'event': 'mail_received',
    'account_id': ACCOUNT_ID,
    'sender': {'attendee_provider_id': 'mailer-daemon@googlemail.com'},
    'message': {
        'id': 'manual-bounce-replay-1776892293',
        'account_id': ACCOUNT_ID,
        'account_type': 'GMAIL',
        'subject': 'Delivery Status Notification (Failure)',
        'body': (
            'Endereço não encontrado\n'
            'A mensagem não foi entregue para '
            'bounce-test-1776892293@prospector-bounce-1776892293.invalid '
            'porque o domínio prospector-bounce-1776892293.invalid não foi encontrado.\n'
            'A resposta foi:\n'
            "DNS Error: DNS type 'mx' lookup of prospector-bounce-1776892293.invalid responded with code NXDOMAIN Domain name not found."
        ),
    },
}

async def main():
    async with AsyncSessionLocal() as db:
        await unipile_webhook._handle_message_received(PAYLOAD, db, SimpleNamespace())
        lead = (await db.execute(select(Lead).where(Lead.id == LEAD_ID))).scalar_one()
        print('LEAD_ID', lead.id)
        print('EMAIL', lead.email_corporate)
        print('BOUNCED_AT', lead.email_bounced_at.isoformat() if lead.email_bounced_at else None)
        print('BOUNCE_TYPE', lead.email_bounce_type)

asyncio.run(main())
