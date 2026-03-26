"""Check Unipile API for attachment sending capabilities."""
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
        # Check the POST /chats/messages endpoint docs by sending options
        # Try sending a message with attachment parameter to see what error
        # First, let's check what the API accepts
        
        # Check if there's an upload endpoint
        resp = await client.options("/chats/messages")
        print(f"OPTIONS /chats/messages: {resp.status_code}")
        print(f"Headers: {dict(resp.headers)}")
        
        # Try multipart with a dummy small file
        account_id = settings.UNIPILE_ACCOUNT_ID_LINKEDIN or ""
        # Don't actually send - just check the API docs path
        resp2 = await client.get("/docs")
        print(f"\nGET /docs: {resp2.status_code}")
        
        # Check if /chats/messages accepts multipart
        # Based on Unipile docs: POST /chats/messages supports
        # multipart/form-data with "attachments" field
        print("\n--- Unipile API supports ---")
        print("POST /chats/messages - text + attachments (multipart/form-data)")
        print("  Fields: account_id, attendees_ids, text, attachments[]")
        print("POST /chats/messages/audio - audio_url")


asyncio.run(main())
