"""Quick diagnostic for Speechify API."""
import asyncio
import httpx
from core.config import settings

async def test():
    client = httpx.AsyncClient(
        base_url="https://api.sws.speechify.com/v1",
        headers={"Authorization": f"Bearer {settings.SPEECHIFY_API_KEY}"},
        timeout=30.0,
    )
    try:
        resp = await client.get("/voices")
        print(f"Status: {resp.status_code}")
        data = resp.json()
        if isinstance(data, list):
            print(f"Response is a list with {len(data)} items")
            if data:
                print(f"First item keys: {list(data[0].keys())}")
                v = data[0]
                print(f"Sample: {v}")
        elif isinstance(data, dict):
            print(f"Response is a dict with keys: {list(data.keys())}")
            voices = data.get("voices", data.get("data", []))
            print(f"Voices count: {len(voices)}")
        else:
            print(f"Unexpected type: {type(data)}")
            print(f"Raw: {resp.text[:500]}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.aclose()

asyncio.run(test())
