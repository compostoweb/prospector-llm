"""Check raw chat structure for chats with numeric attendee IDs."""
import asyncio
import json
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
        resp = await client.get("/chats", params={"account_id": account_id, "limit": 20})
        data = resp.json()
        for chat in data.get("items", []):
            att_id = chat.get("attendee_provider_id", "?")
            # Only show chats with numeric attendee_ids (problematic ones)
            if att_id.isdigit():
                print(f"\n=== NUMERIC ATT_ID: {att_id} ===")
                print(json.dumps(chat, indent=2, default=str))

        # Also try /chats/{id} for one numeric attendee chat
        for chat in data.get("items", []):
            att_id = chat.get("attendee_provider_id", "?")
            if att_id.isdigit():
                chat_id = chat.get("id", "")
                print(f"\n=== GET /chats/{chat_id} ===")
                resp2 = await client.get(f"/chats/{chat_id}")
                detail = resp2.json()
                # Check if there's attendees array or any name field
                for key in ["attendees", "display_name", "name", "participants", "members"]:
                    if key in detail:
                        print(f"  {key}: {detail[key]}")
                break


asyncio.run(main())
