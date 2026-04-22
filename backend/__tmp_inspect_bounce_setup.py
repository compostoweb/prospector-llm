import asyncio
from sqlalchemy import select
from core.database import AsyncSessionLocal
from models.tenant import Tenant, TenantIntegration
from models.email_account import EmailAccount
from models.cadence import Cadence

async def main():
    async with AsyncSessionLocal() as db:
        tenants = (await db.execute(select(Tenant).where(Tenant.is_active.is_(True)))).scalars().all()
        print('TENANTS', len(tenants))
        for tenant in tenants[:10]:
            print('TENANT', tenant.id, tenant.name)
            integration = (await db.execute(select(TenantIntegration).where(TenantIntegration.tenant_id == tenant.id))).scalar_one_or_none()
            if integration:
                print('  INTEGRATION', 'gmail=', integration.unipile_gmail_account_id, 'linkedin=', integration.unipile_linkedin_account_id)
            accounts = (await db.execute(select(EmailAccount).where(EmailAccount.tenant_id == tenant.id, EmailAccount.is_active.is_(True)))).scalars().all()
            print('  EMAIL_ACCOUNTS', len(accounts))
            for acc in accounts[:10]:
                print('   -', acc.id, acc.email_address, acc.provider_type, 'imap=', bool(acc.imap_host), 'smtp=', bool(acc.smtp_host), 'unipile=', acc.unipile_account_id)
            cadences = (await db.execute(select(Cadence).where(Cadence.tenant_id == tenant.id, Cadence.is_active.is_(True)))).scalars().all()
            print('  CADENCES', len(cadences))
            for cad in cadences[:10]:
                print('   -', cad.id, cad.name, 'email_account_id=', cad.email_account_id)

asyncio.run(main())
