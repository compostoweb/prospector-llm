"""Clear cached profiles and previews from Redis."""
import asyncio
import redis.asyncio as aioredis
from core.config import settings

async def main() -> None:
    c = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    keys = await c.keys("unipile:profile:*")
    keys2 = await c.keys("inbox:preview:*")
    all_keys = keys + keys2
    if all_keys:
        await c.delete(*all_keys)
        print(f"Cleared {len(all_keys)} cache keys")
    else:
        print("No keys to clear")
    await c.aclose()

asyncio.run(main())
