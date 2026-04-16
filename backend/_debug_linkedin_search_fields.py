"""Debug: ver campos brutos retornados pelo Unipile na busca de perfis LinkedIn."""
import asyncio
import json
import os

os.environ["ENV"] = "dev"


async def main() -> None:
    from core.config import settings
    from integrations.unipile_client import UnipileClient

    client = UnipileClient()
    acc = settings.UNIPILE_ACCOUNT_ID_LINKEDIN or ""

    # Busca pequena para inspecionar os campos
    import httpx
    async with httpx.AsyncClient(
        base_url=settings.UNIPILE_BASE_URL,
        headers={"X-API-KEY": settings.UNIPILE_API_KEY or "", "accept": "application/json"},
        timeout=30.0,
    ) as c:
        body = {
            "api": "classic",
            "category": "people",
            "keywords": "gerente",
        }
        resp = await c.post(
            "/linkedin/search",
            params={"account_id": acc, "limit": 3},
            json=body,
        )
        print(f"Status: {resp.status_code}")
        data = resp.json()
        items = data.get("items", [])
        print(f"\nTotal items: {len(items)}")
        if items:
            print("\n=== Campos do primeiro perfil (todos) ===")
            print(json.dumps(items[0], indent=2, ensure_ascii=False))
            print("\n=== Chaves presentes em todos os perfis ===")
            all_keys: set[str] = set()
            for item in items:
                all_keys.update(item.keys())
            print(sorted(all_keys))


if __name__ == "__main__":
    asyncio.run(main())
