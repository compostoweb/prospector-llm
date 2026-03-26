"""Debug: Verifica todos os campos que a Unipile retorna para um perfil."""
import asyncio, json, httpx, os
from dotenv import load_dotenv
load_dotenv(".env.dev")

BASE = os.getenv("UNIPILE_BASE_URL", "https://api2.unipile.com:13246/api/v1")
KEY = os.getenv("UNIPILE_API_KEY", "")
ACC = os.getenv("UNIPILE_ACCOUNT_ID_LINKEDIN", "") or os.getenv("UNIPILE_ACCOUNT_ID", "")

async def main():
    async with httpx.AsyncClient(base_url=BASE, headers={"X-API-KEY": KEY}, timeout=30.0) as c:
        # Pega chats
        r = await c.get("/chats", params={"account_id": ACC, "limit": 10})
        items = r.json().get("items", [])
        print(f"Got {len(items)} chats")
        
        for chat in items:
            atts = chat.get("attendees", [])
            for att in atts:
                pid = att.get("attendee_provider_id", "")
                if not pid:
                    continue
                print(f"\n--- Attendee provider_id: {pid} ---")
                print(f"Attendee raw keys: {list(att.keys())}")
                
                pr = await c.get(f"/users/{pid}", params={"account_id": ACC})
                if pr.status_code == 200:
                    data = pr.json()
                    print(f"Profile keys: {list(data.keys())}")
                    print(json.dumps(data, indent=2, default=str, ensure_ascii=False))
                else:
                    print(f"Status: {pr.status_code}")
                return  # Só 1 perfil basta

asyncio.run(main())
