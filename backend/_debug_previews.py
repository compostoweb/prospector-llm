"""Debug preview fetch for specific chats."""
import asyncio
import httpx
from core.config import settings

async def main() -> None:
    acc = settings.UNIPILE_ACCOUNT_ID_LINKEDIN or ""
    async with httpx.AsyncClient(
        base_url=settings.UNIPILE_BASE_URL,
        headers={"X-API-KEY": settings.UNIPILE_API_KEY or "", "accept": "application/json"},
        timeout=30.0,
    ) as c:
        # First, get a few chat IDs
        resp = await c.get("/chats", params={"account_id": acc, "limit": 20})
        data = resp.json()
        valid = [
            ch for ch in data["items"]
            if ch.get("content_type", "") not in ("sponsored", "linkedin_offer", "linkedin_ad")
            and not ch.get("read_only")
        ]
        
        print(f"Valid chats: {len(valid)}")
        
        # Test 3 chats: first, and 2 random ones
        for ch in valid[:5]:
            cid = ch["id"]
            print(f"\n--- Chat {cid[:12]} (ts={ch.get('timestamp')}) ---")
            try:
                resp2 = await c.get(f"/chats/{cid}/messages", params={"limit": 1})
                print(f"  Status: {resp2.status_code}")
                if resp2.status_code == 200:
                    md = resp2.json()
                    msgs = md.get("items", [])
                    if msgs:
                        m = msgs[0]
                        text = m.get("text", "")
                        ts = m.get("timestamp", "")
                        sender = m.get("sender_id", "")[:20]
                        is_sender = m.get("is_sender")
                        print(f"  text: {text[:80]!r}")
                        print(f"  timestamp: {ts}")
                        print(f"  is_sender: {is_sender}")
                    else:
                        print(f"  NO MESSAGES")
                else:
                    print(f"  Error: {resp2.text[:200]}")
            except Exception as e:
                print(f"  Exception: {e}")

asyncio.run(main())
