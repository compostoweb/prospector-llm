"""Debug: teste mínimo de fetch_profile_company."""

import asyncio
import json
import os
import sys
import traceback

os.environ.setdefault("ENV", "dev")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import httpx  # noqa: E402

from core.config import settings  # noqa: E402

BASE_URL = settings.UNIPILE_BASE_URL
API_KEY = settings.UNIPILE_API_KEY
ACCOUNT_ID = settings.UNIPILE_ACCOUNT_ID_LINKEDIN


async def main() -> None:
    out: list[str] = []
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        headers={"X-API-KEY": API_KEY},
        timeout=30.0,
    ) as client:
        # Search 3 perfis
        r = await client.post(
            "/linkedin/search",
            params={"account_id": ACCOUNT_ID, "limit": 3},
            json={"api": "classic", "category": "people", "keywords": "gerente"},
        )
        r.raise_for_status()
        items = r.json().get("items", [])
        out.append(f"Search: {len(items)} itens\n")

        for i, item in enumerate(items[:3]):
            pid = item.get("id") or item.get("public_id") or ""
            name = item.get("name", "?")
            out.append(f"\n=== Perfil {i + 1}: {name} (pid={pid}) ===")
            out.append(f"  search.company = {item.get('company')}")
            out.append(f"  search.current_company = {item.get('current_company')}")
            out.append(f"  search.headline = {item.get('headline') or item.get('title')}")

            r2 = await client.get(
                f"/users/{pid}",
                params={"account_id": ACCOUNT_ID, "linkedin_sections": "experience"},
            )
            out.append(f"  GET /users status = {r2.status_code}")
            if r2.status_code == 200:
                data = r2.json()
                out.append(f"  top keys = {sorted(data.keys())}")
                # Dump all experience-related fields
                for key in sorted(data.keys()):
                    val = data[key]
                    kl = key.lower()
                    if any(w in kl for w in ("exp", "work", "company", "position", "occup")):
                        out.append(f"  {key} = {json.dumps(val, ensure_ascii=False)[:600]}")
                # Full dump first profile
                if i == 0:
                    out.append(
                        f"\n  FULL JSON:\n{json.dumps(data, ensure_ascii=False, indent=2)[:4000]}"
                    )
            else:
                out.append(f"  response body = {r2.text[:300]}")

            await asyncio.sleep(1.5)

    with open("_debug_enrich_output.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print(f"Output escrito em _debug_enrich_output.txt ({len(out)} linhas)")


try:
    asyncio.run(main())
except Exception:
    traceback.print_exc()
