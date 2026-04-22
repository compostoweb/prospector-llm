import asyncio
from workers.email_inbox_poll import _poll_all

print(asyncio.run(_poll_all()))
