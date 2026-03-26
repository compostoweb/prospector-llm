"""
Debug script: dump raw Unipile /chats response to see exact field names.
Run: cd backend && ENV=dev python _debug_unipile_chats.py
"""
import asyncio
import json
import httpx
from core.config import settings

async def main() -> None:
    base = settings.UNIPILE_BASE_URL
    key = settings.UNIPILE_API_KEY or ""
    acc = settings.UNIPILE_ACCOUNT_ID_LINKEDIN or ""
    print(f"Base URL: {base}")
    print(f"Account ID: {acc}")

    async with httpx.AsyncClient(
        base_url=base,
        headers={"X-API-KEY": key, "accept": "application/json"},
        timeout=30.0,
    ) as client:
        # Fetch 5 chats only
        resp = await client.get("/chats", params={"account_id": acc, "limit": 5})
        resp.raise_for_status()
        data = resp.json()

        items = data.get("items", [])
        print(f"\n=== Got {len(items)} chats ===\n")

        for i, chat in enumerate(items):
            print(f"--- Chat {i+1} ---")
            print(f"  TOP-LEVEL KEYS: {sorted(chat.keys())}")
            print(f"  id:                    {chat.get('id')}")
            print(f"  account_id:            {chat.get('account_id')}")
            print(f"  attendee_provider_id:  {chat.get('attendee_provider_id')}")
            print(f"  content_type:          {chat.get('content_type')}")
            print(f"  read_only:             {chat.get('read_only')}")
            print(f"  unread_count:          {chat.get('unread_count')}")
            print(f"  display_name:          {chat.get('display_name')}")
            print(f"  name:                  {chat.get('name')}")
            print(f"  timestamp:             {chat.get('timestamp')}")
            
            # Check for lastMessage in various forms
            for key_name in ["lastMessage", "last_message", "lastActivity", "last_activity", "snippet"]:
                val = chat.get(key_name)
                if val is not None:
                    print(f"  {key_name}: {json.dumps(val, default=str, ensure_ascii=False)[:300]}")

            # Check for any nested objects we might be missing
            for k, v in chat.items():
                if isinstance(v, dict) and k not in ("lastMessage", "last_message"):
                    print(f"  NESTED[{k}]: {json.dumps(v, default=str, ensure_ascii=False)[:200]}")
                elif isinstance(v, list) and k not in ("items",):
                    print(f"  LIST[{k}]: len={len(v)}, first={json.dumps(v[0], default=str, ensure_ascii=False)[:200] if v else 'empty'}")
            
            print()

        print(f"Cursor: {data.get('cursor', 'NONE')}")

asyncio.run(main())
