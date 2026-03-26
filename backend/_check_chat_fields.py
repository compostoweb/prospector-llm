"""Quick test to check chat raw fields for display_name fallback."""
import asyncio
import os
os.environ["ENV"] = "dev"

from core.config import settings
import httpx


async def main() -> None:
    async with httpx.AsyncClient(
        base_url=settings.UNIPILE_BASE_URL,
        headers={"X-API-KEY": settings.UNIPILE_API_KEY or "", "accept": "application/json"},
        timeout=30.0,
    ) as client:
        account_id = settings.UNIPILE_ACCOUNT_ID_LINKEDIN or ""
        resp = await client.get("/chats", params={"account_id": account_id, "limit": 5})
        data = resp.json()
        for chat in data.get("items", []):
            att_id = chat.get("attendee_provider_id", "?")
            # Print all top-level string fields
            fields = {k: v for k, v in chat.items() if isinstance(v, str)}
            print(f"att_id={att_id[:20]}  fields={list(fields.keys())}  display_name={chat.get('display_name')}  name={chat.get('name')}")


asyncio.run(main())
