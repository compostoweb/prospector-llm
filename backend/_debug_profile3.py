"""Debug: Verifica campos de perfil Unipile."""
import asyncio, json, httpx, os
from dotenv import load_dotenv
load_dotenv(".env.dev")

BASE = os.getenv("UNIPILE_BASE_URL", "https://api2.unipile.com:13246/api/v1")
KEY = os.getenv("UNIPILE_API_KEY", "")
ACC = os.getenv("UNIPILE_ACCOUNT_ID_LINKEDIN", "") or os.getenv("UNIPILE_ACCOUNT_ID", "")

print(f"Account: {ACC[:10]}...")

async def main():
    async with httpx.AsyncClient(base_url=BASE, headers={"X-API-KEY": KEY}, timeout=30.0) as c:
        r = await c.get("/chats", params={"account_id": ACC, "limit": 5})
        items = r.json().get("items", [])
        print(f"Got {len(items)} chats")
        
        if items:
            chat = items[0]
            print(f"\nChat keys: {list(chat.keys())}")
            atts = chat.get("attendees", [])
            print(f"Attendees count: {len(atts)}")
            if atts:
                print(f"Attendee[0] keys: {list(atts[0].keys())}")
                print(f"Attendee[0]: {json.dumps(atts[0], indent=2, default=str, ensure_ascii=False)}")
            
            # Pega provider_id de qualquer campo
            pid = None
            for att in atts:
                pid = att.get("attendee_provider_id") or att.get("provider_id") or att.get("id")
                if pid:
                    break
            
            if not pid:
                # Tenta extrair do chat diretamente
                pid = chat.get("provider_id") or chat.get("attendee_provider_id")
                print(f"Got provider_id from chat: {pid}")
            
            if pid:
                print(f"\nFetching /users/{pid} ...")
                pr = await c.get(f"/users/{pid}", params={"account_id": ACC})
                print(f"Status: {pr.status_code}")
                if pr.status_code == 200:
                    data = pr.json()
                    print(f"Profile keys: {list(data.keys())}")
                    print(json.dumps(data, indent=2, default=str, ensure_ascii=False))
                    
                    # Highlight key fields
                    for key in ["headline", "occupation", "current_position", "title", "company", "industry", "summary", "about"]:
                        if key in data:
                            print(f"\n*** Found field '{key}': {data[key]}")
            else:
                print("No provider_id found, printing full first chat:")
                print(json.dumps(chat, indent=2, default=str, ensure_ascii=False)[:2000])

asyncio.run(main())
