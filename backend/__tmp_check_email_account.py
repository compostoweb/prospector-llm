import asyncio
from sqlalchemy import select
from core.database import AsyncSessionLocal
from models.email_account import EmailAccount
from integrations.email.registry import EmailRegistry
from core.config import settings

ACCOUNT_ID = 'f2f3e0bd-bb1c-490b-915f-c8549d787063'

async def main():
    async with AsyncSessionLocal() as db:
        account = (await db.execute(select(EmailAccount).where(EmailAccount.id == ACCOUNT_ID))).scalar_one()
        print('EMAIL', account.email_address)
        print('PROVIDER', account.provider_type)
        print('HISTORY_ID', account.gmail_history_id)
        registry = EmailRegistry(settings=settings)
        ok = await registry.ping(account)
        print('PING', ok)

asyncio.run(main())
