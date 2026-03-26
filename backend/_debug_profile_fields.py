"""Debug: Verifica todos os campos que a Unipile retorna para um perfil."""
import asyncio
import json
import httpx
from dotenv import load_dotenv
import os

load_dotenv(".env.dev")

BASE_URL = os.getenv("UNIPILE_BASE_URL", "https://api2.unipile.com:13246/api/v1")
API_KEY = os.getenv("UNIPILE_API_KEY", "")
ACCOUNT_ID = os.getenv("UNIPILE_ACCOUNT_ID", "")

async def main():
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        headers={"X-API-KEY": API_KEY},
        timeout=30.0,
    ) as client:
        # Primeiro pega uma conversa com attendee
        resp = await client.get("/chats", params={"account_id": ACCOUNT_ID, "limit": 5})
        chats = resp.json().get("items", [])
        
        seen_providers = set()
        for chat in chats:
            for att in chat.get("attendees", []):
                pid = att.get("attendee_provider_id", "")
                if pid and pid not in seen_providers:
                    seen_providers.add(pid)
                    print(f"\n{'='*60}")
                    print(f"Provider ID: {pid}")
                    print(f"Raw attendee from /chats: {json.dumps(att, indent=2, default=str)}")
                    
                    # Agora busca perfil completo
                    profile_resp = await client.get(
                        f"/users/{pid}",
                        params={"account_id": ACCOUNT_ID},
                    )
                    if profile_resp.status_code == 200:
                        profile = profile_resp.json()
                        print(f"\nFull profile from /users/{pid}:")
                        print(json.dumps(profile, indent=2, default=str))
                    else:
                        print(f"Profile fetch failed: {profile_resp.status_code}")
                    
                    if len(seen_providers) >= 3:
                        break
            if len(seen_providers) >= 3:
                break

asyncio.run(main())
