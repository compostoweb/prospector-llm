"""
Check Unipile account status and look for multiple LinkedIn accounts.
"""
import asyncio
import httpx
import json
from core.config import settings

async def main() -> None:
    base = settings.UNIPILE_BASE_URL
    key = settings.UNIPILE_API_KEY or ""
    configured_acc = settings.UNIPILE_ACCOUNT_ID_LINKEDIN or ""
    print(f"Configured account ID: {configured_acc}")
    print(f"Base URL: {base}\n")

    async with httpx.AsyncClient(
        base_url=base,
        headers={"X-API-KEY": key, "accept": "application/json"},
        timeout=30.0,
    ) as c:
        # 1. List ALL accounts
        print("=== ALL ACCOUNTS ===")
        resp = await c.get("/accounts")
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("items", data) if isinstance(data, dict) else data
            if isinstance(items, list):
                for acc in items:
                    acc_id = acc.get("id", "")
                    prov = acc.get("provider", "")
                    status = acc.get("status", "")
                    name = acc.get("name", "")
                    email = acc.get("email", "")
                    acc_type = acc.get("type", "")
                    created = acc.get("created_at", "")
                    sources = acc.get("sources", [])
                    print(f"  ID: {acc_id}")
                    print(f"    provider: {prov}  status: {status}  type: {acc_type}")
                    print(f"    name: {name}  email: {email}")
                    print(f"    created: {created}")
                    print(f"    sources: {sources}")
                    print(f"    ALL KEYS: {sorted(acc.keys())}")
                    
                    # Check if LINKEDIN type
                    if prov and "linkedin" in str(prov).lower():
                        print(f"    *** THIS IS A LINKEDIN ACCOUNT ***")
                    print()
            else:
                print(f"  Raw response: {json.dumps(data, default=str)[:500]}")
        else:
            print(f"  Status: {resp.status_code}")
            print(f"  Body: {resp.text[:500]}")

        # 2. Get specific account details
        print(f"\n=== CONFIGURED ACCOUNT DETAILS ({configured_acc}) ===")
        resp2 = await c.get(f"/accounts/{configured_acc}")
        if resp2.status_code == 200:
            acc_data = resp2.json()
            for k, v in sorted(acc_data.items()):
                if isinstance(v, (str, int, bool, float, type(None))):
                    print(f"  {k}: {v}")
                else:
                    print(f"  {k}: {json.dumps(v, default=str)[:200]}")
        else:
            print(f"  Status: {resp2.status_code}: {resp2.text[:300]}")

        # 3. Check if there's a sync endpoint
        print(f"\n=== SYNC STATUS ===")
        for endpoint in [
            f"/accounts/{configured_acc}/sync",
            f"/accounts/{configured_acc}/status",
        ]:
            try:
                resp3 = await c.get(endpoint)
                print(f"  GET {endpoint}: {resp3.status_code}")
                if resp3.status_code == 200:
                    print(f"    {json.dumps(resp3.json(), default=str)[:300]}")
            except Exception as e:
                print(f"  GET {endpoint}: ERROR {e}")

asyncio.run(main())
