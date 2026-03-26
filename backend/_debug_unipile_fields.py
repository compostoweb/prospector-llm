"""Check unread field and profile data from Unipile."""
import asyncio
import httpx
import json
from core.config import settings

async def main() -> None:
    acc = settings.UNIPILE_ACCOUNT_ID_LINKEDIN or ""
    async with httpx.AsyncClient(
        base_url=settings.UNIPILE_BASE_URL,
        headers={"X-API-KEY": settings.UNIPILE_API_KEY or "", "accept": "application/json"},
        timeout=30.0,
    ) as c:
        resp = await c.get("/chats", params={"account_id": acc, "limit": 20})
        data = resp.json()

        print("=== Non-sponsored chats ===")
        valid_chats = []
        for chat in data["items"]:
            ct = chat.get("content_type", "")
            if ct in ("sponsored", "linkedin_offer", "linkedin_ad") or chat.get("read_only"):
                continue
            valid_chats.append(chat)
            cid = chat["id"][:12]
            att = chat.get("attendee_provider_id", "")[:20]
            print(f"  id={cid}  unread={chat.get('unread')!r}  unread_count={chat.get('unread_count')}  ts={chat.get('timestamp')}  att={att}")

        print(f"\nTotal valid: {len(valid_chats)}")

        # Check profile for first valid chat
        if valid_chats:
            att_id = valid_chats[0].get("attendee_provider_id", "")
            print(f"\n=== Profile test: {att_id} ===")
            resp2 = await c.get(f"/users/{att_id}", params={"account_id": acc})
            print(f"Status: {resp2.status_code}")
            if resp2.status_code == 200:
                d = resp2.json()
                print(f"Keys: {sorted(d.keys())}")
                for k in ["first_name", "last_name", "display_name", "name", "headline", "public_identifier"]:
                    print(f"  {k}: {d.get(k)!r}")

        # Also check messages endpoint for first valid chat
        if valid_chats:
            cid = valid_chats[0]["id"]
            print(f"\n=== Last message for chat {cid[:12]} ===")
            resp3 = await c.get(f"/chats/{cid}/messages", params={"limit": 1})
            if resp3.status_code == 200:
                md = resp3.json()
                msgs = md.get("items", [])
                if msgs:
                    m = msgs[0]
                    print(f"  Keys: {sorted(m.keys())}")
                    print(f"  text: {(m.get('text',''))[:100]!r}")
                    print(f"  timestamp: {m.get('timestamp')}")
                    print(f"  sender_id: {m.get('sender_id', '')[:20]}")
                    print(f"  is_sender: {m.get('is_sender')}")

asyncio.run(main())
