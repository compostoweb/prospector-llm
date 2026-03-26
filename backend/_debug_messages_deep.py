"""Deep debug: check messages for all found chats."""
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
        # Fetch 3 pages to find chats
        all_chats = []
        cursor = None
        for page in range(3):
            params = {"account_id": acc, "limit": 100}
            if cursor:
                params["cursor"] = cursor
            resp = await c.get("/chats", params=params)
            data = resp.json()
            for ch in data["items"]:
                ct = ch.get("content_type", "")
                if ct in ("sponsored", "linkedin_offer", "linkedin_ad") or ch.get("read_only"):
                    continue
                all_chats.append(ch)
            cursor = data.get("cursor")
            if not cursor:
                break
        
        print(f"Found {len(all_chats)} valid chats across {page+1} pages\n")
        
        # Test messages for first 5 chats
        for i, ch in enumerate(all_chats[:8]):
            cid = ch["id"]
            ts = ch.get("timestamp", "")
            print(f"--- Chat {i+1}: {cid[:15]} (ts={ts}) ---")
            try:
                resp2 = await c.get(f"/chats/{cid}/messages", params={"limit": 1})
                print(f"  HTTP Status: {resp2.status_code}")
                if resp2.status_code == 200:
                    md = resp2.json()
                    msgs = md.get("items", [])
                    if msgs:
                        m = msgs[0]
                        text = m.get("text", "")
                        ts2 = m.get("timestamp", "")
                        print(f"  text: {text[:100]!r}")
                        print(f"  msg_ts: {ts2}")
                    else:
                        print(f"  NO MESSAGES in response")
                        print(f"  Response keys: {sorted(md.keys())}")
                else:
                    print(f"  Error body: {resp2.text[:200]}")
            except Exception as e:
                print(f"  EXCEPTION: {type(e).__name__}: {e}")
            print()

asyncio.run(main())
