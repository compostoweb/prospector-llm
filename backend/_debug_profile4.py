"""Debug: Verifica campos de perfil Unipile via attendee_provider_id."""
import asyncio, json, httpx, os
from dotenv import load_dotenv
load_dotenv(".env.dev")

BASE = os.getenv("UNIPILE_BASE_URL", "https://api2.unipile.com:13246/api/v1")
KEY = os.getenv("UNIPILE_API_KEY", "")
ACC = os.getenv("UNIPILE_ACCOUNT_ID_LINKEDIN", "") or os.getenv("UNIPILE_ACCOUNT_ID", "")

async def main():
    async with httpx.AsyncClient(base_url=BASE, headers={"X-API-KEY": KEY}, timeout=30.0) as c:
        r = await c.get("/chats", params={"account_id": ACC, "limit": 10})
        items = r.json().get("items", [])
        print(f"Chats: {len(items)}")
        
        for chat in items:
            pid = chat.get("attendee_provider_id", "")
            ct = chat.get("type", "")
            name = chat.get("name", "")
            if not pid or ct in ("SPONSORED", "ADS"):
                continue
            
            print(f"\n{'='*60}")
            print(f"Chat: {name} | type={ct}")
            print(f"attendee_provider_id: {pid}")
            
            pr = await c.get(f"/users/{pid}", params={"account_id": ACC})
            print(f"Status: {pr.status_code}")
            if pr.status_code == 200:
                data = pr.json()
                print(f"All keys: {sorted(data.keys())}")
                # Print non-empty values
                for k, v in sorted(data.items()):
                    if v and v not in ("", None, [], {}):
                        val_str = json.dumps(v, default=str, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v)
                        if len(val_str) > 200:
                            val_str = val_str[:200] + "..."
                        print(f"  {k}: {val_str}")
                return  # Só preciso de 1 perfil válido
        
        print("Nenhum perfil válido encontrado")

asyncio.run(main())
