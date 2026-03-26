"""
Deep diagnostic: Check ALL chats from Unipile without any filtering.
Compare with what our filter removes.
"""
import asyncio
import httpx
from core.config import settings

async def main() -> None:
    acc = settings.UNIPILE_ACCOUNT_ID_LINKEDIN or ""
    print(f"Account: {acc}\n")

    async with httpx.AsyncClient(
        base_url=settings.UNIPILE_BASE_URL,
        headers={"X-API-KEY": settings.UNIPILE_API_KEY or "", "accept": "application/json"},
        timeout=30.0,
    ) as c:
        # Fetch ALL chats from first 3 pages without filtering
        all_chats = []
        cursor = None
        for page in range(3):
            params = {"account_id": acc, "limit": 100}
            if cursor:
                params["cursor"] = cursor
            resp = await c.get("/chats", params=params)
            data = resp.json()
            items = data.get("items", [])
            all_chats.extend(items)
            cursor = data.get("cursor")
            print(f"Page {page+1}: {len(items)} chats")
            if not cursor:
                break

        print(f"\nTotal raw chats: {len(all_chats)}\n")

        # Group by filtering status
        skip_types = {"linkedin_offer", "sponsored", "linkedin_ad"}
        kept = []
        filtered_out = []
        for ch in all_chats:
            ct = ch.get("content_type", "") or ""
            ro = ch.get("read_only", 0)
            if ct in skip_types or ro:
                filtered_out.append(ch)
            else:
                kept.append(ch)

        print(f"Kept: {len(kept)}")
        print(f"Filtered out: {len(filtered_out)}\n")

        # Show recent conversations (2026) that we're FILTERING OUT
        print("=== FILTERED OUT chats from 2026 ===")
        for ch in filtered_out:
            ts = ch.get("timestamp", "")
            if "2026" in ts:
                ct = ch.get("content_type", "")
                ro = ch.get("read_only", 0)
                att = ch.get("attendee_provider_id", "")[:30]
                name = ch.get("name") or ch.get("display_name") or "?"
                unread = ch.get("unread_count", 0)
                print(f"  ts={ts}  ct={ct!r}  ro={ro}  unread={unread}  att={att}  name={name!r}")

        # Show ALL kept chats with dates
        print(f"\n=== ALL {len(kept)} KEPT chats (sorted by timestamp) ===")
        kept.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        for i, ch in enumerate(kept[:30]):
            ts = ch.get("timestamp", "")
            ct = ch.get("content_type", "") or "none"
            att = ch.get("attendee_provider_id", "")[:30]
            unread = ch.get("unread_count", 0)
            name = ch.get("name") or ch.get("display_name") or ""
            folder = ch.get("folder", [])
            print(f"  {i+1:3}. ts={ts}  ct={ct!r}  unread={unread}  folders={folder}  att={att[:20]}")

        # Check if there are chats with content_type=None but not in kept
        print(f"\n=== Content type distribution ===")
        ct_counts: dict[str, int] = {}
        for ch in all_chats:
            ct = ch.get("content_type") or "NONE/empty"
            ct_counts[ct] = ct_counts.get(ct, 0) + 1
        for ct, count in sorted(ct_counts.items(), key=lambda x: -x[1]):
            print(f"  {ct}: {count}")

        # Check folder distribution
        print(f"\n=== Folder distribution ===")
        folder_counts: dict[str, int] = {}
        for ch in all_chats:
            folders = ch.get("folder", [])
            key = ",".join(folders) if folders else "NONE"
            folder_counts[key] = folder_counts.get(key, 0) + 1
        for f, count in sorted(folder_counts.items(), key=lambda x: -x[1]):
            print(f"  {f}: {count}")

        # Check type distribution
        print(f"\n=== Type distribution ===")
        type_counts: dict[str, int] = {}
        for ch in all_chats:
            t = ch.get("type") or "NONE"
            type_counts[t] = type_counts.get(t, 0) + 1
        for t, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            print(f"  {t}: {count}")

asyncio.run(main())
