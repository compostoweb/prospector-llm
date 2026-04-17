"""Debug: simula o fluxo completo search + enrich para 25 perfis."""

import asyncio
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


async def fetch_company(client: httpx.AsyncClient, pid: str) -> tuple[str, str | None, int]:
    """Replica fetch_profile_company: retorna (pid, company, status)."""
    try:
        r = await client.get(
            f"/users/{pid}",
            params={"account_id": ACCOUNT_ID, "linkedin_sections": "experience"},
        )
        if r.status_code != 200:
            return pid, None, r.status_code
        data = r.json()
        exp = data.get("work_experience") or []
        if isinstance(exp, list) and exp:
            first = exp[0]
            if isinstance(first, dict):
                company = first.get("company") or first.get("company_name") or None
                return pid, company, 200
        return pid, None, 200  # 200 mas sem experience
    except Exception:
        return pid, None, -1


async def main() -> None:
    out: list[str] = []
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        headers={"X-API-KEY": API_KEY},
        timeout=30.0,
    ) as client:
        # Search 25 perfis
        r = await client.post(
            "/linkedin/search",
            params={"account_id": ACCOUNT_ID, "limit": 25},
            json={"api": "classic", "category": "people", "keywords": "diretor marketing"},
        )
        r.raise_for_status()
        items = r.json().get("items", [])
        out.append(f"Search: {len(items)} itens\n")

        found = 0
        not_found = 0
        errors = 0

        for i, item in enumerate(items):
            pid = item.get("id") or item.get("public_id") or ""
            name = item.get("name", "?")
            search_company = item.get("company") or item.get("current_company")

            pid_str, company, status_code = await fetch_company(client, pid)

            if company:
                found += 1
                marker = "OK"
            elif status_code == 200:
                not_found += 1
                marker = "NO_EXP"
            else:
                errors += 1
                marker = f"ERR_{status_code}"

            out.append(
                f"  [{marker}] {i + 1:2d}. {name[:35]:35s} | search_co={str(search_company)[:25]:25s} | enrich_co={str(company)[:30]}"
            )

            # Delay como o endpoint faz (0.4s)
            await asyncio.sleep(0.4)

        out.append("\n=== SUMMARY ===")
        out.append(f"  Total: {len(items)}")
        out.append(f"  Found company: {found}")
        out.append(f"  No experience: {not_found}")
        out.append(f"  Errors: {errors}")

    result = "\n".join(out)
    with open("_debug_enrich_output2.txt", "w", encoding="utf-8") as f:
        f.write(result)
    print(result)


try:
    asyncio.run(main())
except Exception:
    traceback.print_exc()
