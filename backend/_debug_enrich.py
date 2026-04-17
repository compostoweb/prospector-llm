"""Debug: testa fetch_profile_company para 3 perfis e imprime resposta bruta da Unipile."""

import asyncio
import json
import os
import sys

import httpx

os.environ.setdefault("ENV", "dev")
sys.path.insert(0, os.path.dirname(__file__))

from core.config import settings

BASE_URL = settings.UNIPILE_BASE_URL
API_KEY = settings.UNIPILE_API_KEY
ACCOUNT_ID = settings.UNIPILE_ACCOUNT_ID_LINKEDIN


# Pegar alguns provider_ids de um search rápido
async def main():
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        headers={"X-API-KEY": API_KEY},
        timeout=30.0,
    ) as client:
        # 1) Buscar 5 perfis via search
        print("=== SEARCH (5 perfis) ===")
        r = await client.post(
            "/linkedin/search",
            params={"account_id": ACCOUNT_ID, "limit": 5},
            json={"api": "classic", "category": "people", "keywords": "gerente"},
        )
        r.raise_for_status()
        search_data = r.json()
        items = search_data.get("items", search_data if isinstance(search_data, list) else [])

        print(f"Search retornou {len(items)} itens")
        for i, item in enumerate(items[:3]):
            pid = item.get("id") or item.get("public_id") or ""
            name = (
                item.get("name")
                or f"{item.get('first_name', '')} {item.get('last_name', '')}".strip()
            )
            company_from_search = item.get("company") or item.get("current_company")
            print(f"\n--- Perfil {i + 1}: {name} (id={pid}) ---")
            print(f"  company from search: {company_from_search}")
            print(f"  headline: {item.get('headline') or item.get('title')}")

            # 2) Buscar experience desse perfil
            print(f"\n  === GET /users/{pid}?linkedin_sections=experience ===")
            r2 = await client.get(
                f"/users/{pid}",
                params={"account_id": ACCOUNT_ID, "linkedin_sections": "experience"},
            )
            print(f"  Status: {r2.status_code}")
            if r2.status_code == 200:
                data = r2.json()
                # Mostrar todas as chaves do topo
                print(f"  Top-level keys: {list(data.keys())}")

                # Procurar por qualquer campo que contenha "experience" ou "company" ou "work"
                for key in sorted(data.keys()):
                    val = data[key]
                    if any(
                        kw in key.lower()
                        for kw in ["experience", "company", "work", "position", "occupation"]
                    ):
                        print(f"  {key}: {json.dumps(val, ensure_ascii=False, indent=4)[:500]}")
                    elif (
                        isinstance(val, str)
                        and len(val) < 200
                        or isinstance(val, (int, float, bool, type(None)))
                    ):
                        print(f"  {key}: {val}")
                    elif isinstance(val, list):
                        print(f"  {key}: list[{len(val)} items]")
                    elif isinstance(val, dict):
                        print(f"  {key}: dict[{len(val)} keys]")

                # Dump completo para o primeiro perfil
                if i == 0:
                    print("\n  === FULL JSON (perfil 1) ===")
                    print(json.dumps(data, ensure_ascii=False, indent=2)[:3000])
            else:
                print(f"  Body: {r2.text[:500]}")

            await asyncio.sleep(1)  # Rate limit


asyncio.run(main())
