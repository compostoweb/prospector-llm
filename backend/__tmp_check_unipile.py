import asyncio
from integrations.unipile_client import unipile_client

ACCOUNT_ID = 'immfTjFkR2e4Z3vnpka6mw'

async def main():
    account = await unipile_client.get_account_status(ACCOUNT_ID)
    print('ACCOUNT_OK', bool(account))
    if account:
        print('ACCOUNT_TYPE', account.get('type'))
        print('ACCOUNT_STATUS', account.get('status'))
        print('ACCOUNT_NAME', account.get('name'))
        print('ACCOUNT_EMAIL', account.get('email'))
    webhooks = await unipile_client.list_webhooks(limit=50)
    print('WEBHOOKS', len(webhooks))
    for webhook in webhooks[:20]:
        print(' -', webhook.get('source'), webhook.get('request_url'), webhook.get('enabled'), webhook.get('events'))

asyncio.run(main())
