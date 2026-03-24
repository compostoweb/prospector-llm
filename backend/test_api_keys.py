"""
Teste rápido de todas as API keys configuradas em .env.dev
Executa: cd backend && python test_api_keys.py
"""
import asyncio
import os
import sys

# Carrega .env.dev
os.environ.setdefault("ENV", "dev")

import httpx

TIMEOUT = httpx.Timeout(15.0)

results: list[tuple[str, str, str]] = []  # (name, status, detail)


def _key(name: str) -> str:
    return os.environ.get(name, "")


def _is_placeholder(val: str) -> bool:
    return not val or val.strip() in ("", "...")


async def test_openai() -> None:
    key = _key("OPENAI_API_KEY")
    if _is_placeholder(key):
        results.append(("OpenAI", "⏭ NÃO CONFIGURADA", ""))
        return
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {key}"},
        )
        if r.status_code == 200:
            models = [m["id"] for m in r.json()["data"][:5]]
            results.append(("OpenAI", "✅ OK", f"Modelos: {', '.join(models)}…"))
        else:
            results.append(("OpenAI", "❌ FALHOU", f"HTTP {r.status_code}: {r.text[:120]}"))


async def test_gemini() -> None:
    key = _key("GEMINI_API_KEY")
    if _is_placeholder(key):
        results.append(("Gemini", "⏭ NÃO CONFIGURADA", ""))
        return
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get(
            f"https://generativelanguage.googleapis.com/v1beta/models?key={key}",
        )
        if r.status_code == 200:
            models = [m["name"].split("/")[-1] for m in r.json().get("models", [])[:5]]
            results.append(("Gemini", "✅ OK", f"Modelos: {', '.join(models)}…"))
        else:
            results.append(("Gemini", "❌ FALHOU", f"HTTP {r.status_code}: {r.text[:120]}"))


async def test_apify() -> None:
    key = _key("APIFY_API_TOKEN")
    if _is_placeholder(key):
        results.append(("Apify", "⏭ NÃO CONFIGURADA", ""))
        return
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get(
            "https://api.apify.com/v2/users/me",
            headers={"Authorization": f"Bearer {key}"},
        )
        if r.status_code == 200:
            data = r.json().get("data", {})
            results.append(("Apify", "✅ OK", f"User: {data.get('username', '?')}"))
        else:
            results.append(("Apify", "❌ FALHOU", f"HTTP {r.status_code}: {r.text[:120]}"))


async def test_prospeo() -> None:
    key = _key("PROSPEO_API_KEY")
    if _is_placeholder(key):
        results.append(("Prospeo", "⏭ NÃO CONFIGURADA", ""))
        return
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        # Usa /account-information (GET, gratuito, não consome créditos)
        r = await c.get(
            "https://api.prospeo.io/account-information",
            headers={"X-KEY": key},
        )
        if r.status_code == 200:
            resp = r.json()
            if resp.get("error") is False:
                info = resp.get("response", {})
                credits = info.get("remaining_credits", "?")
                plan = info.get("current_plan", "?")
                results.append(("Prospeo", "✅ OK", f"Plano: {plan}, Créditos: {credits}"))
            else:
                results.append(("Prospeo", "⚠ RESPOSTA INESPERADA", str(resp)[:120]))
        else:
            results.append(("Prospeo", "❌ FALHOU", f"HTTP {r.status_code}: {r.text[:120]}"))


async def test_hunter() -> None:
    key = _key("HUNTER_API_KEY")
    if _is_placeholder(key):
        results.append(("Hunter", "⏭ NÃO CONFIGURADA", ""))
        return
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get(
            "https://api.hunter.io/v2/account",
            params={"api_key": key},
        )
        if r.status_code == 200:
            data = r.json().get("data", {})
            results.append(("Hunter", "✅ OK", f"Email: {data.get('email', '?')}, Requests restantes: {data.get('requests', {}).get('searches', {}).get('available', '?')}"))
        else:
            results.append(("Hunter", "❌ FALHOU", f"HTTP {r.status_code}: {r.text[:120]}"))


async def test_apollo() -> None:
    key = _key("APOLLO_API_KEY")
    if _is_placeholder(key):
        results.append(("Apollo", "⏭ NÃO CONFIGURADA", ""))
        return
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.post(
            "https://api.apollo.io/api/v1/auth/health",
            headers={"x-api-key": key, "Content-Type": "application/json"},
            json={},
        )
        if r.status_code == 200:
            results.append(("Apollo", "✅ OK", "API key válida"))
        elif r.status_code == 401:
            results.append(("Apollo", "❌ FALHOU", "401 Unauthorized — key inválida"))
        else:
            # Apollo pode não ter /health. Testar /people/match
            r2 = await c.post(
                "https://api.apollo.io/v1/people/match",
                headers={"x-api-key": key, "Content-Type": "application/json"},
                json={"email": "test@google.com"},
            )
            if r2.status_code in (200, 422):
                results.append(("Apollo", "✅ OK", f"Key aceita (HTTP {r2.status_code})"))
            else:
                results.append(("Apollo", "❌ FALHOU", f"HTTP {r2.status_code}: {r2.text[:120]}"))


async def test_zerobounce() -> None:
    key = _key("ZEROBOUNCE_API_KEY")
    if _is_placeholder(key):
        results.append(("ZeroBounce", "⏭ NÃO CONFIGURADA", ""))
        return
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get(
            "https://api.zerobounce.net/v2/getcredits",
            params={"api_key": key},
        )
        if r.status_code == 200:
            data = r.json()
            results.append(("ZeroBounce", "✅ OK", f"Créditos: {data.get('Credits', '?')}"))
        else:
            results.append(("ZeroBounce", "❌ FALHOU", f"HTTP {r.status_code}: {r.text[:120]}"))


async def test_jina() -> None:
    key = _key("JINA_API_KEY")
    if _is_placeholder(key):
        results.append(("Jina", "⏭ NÃO CONFIGURADA", ""))
        return
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get(
            "https://r.jina.ai/https://example.com",
            headers={"Authorization": f"Bearer {key}", "Accept": "text/plain"},
        )
        if r.status_code == 200:
            results.append(("Jina", "✅ OK", f"Retornou {len(r.text)} chars de example.com"))
        else:
            results.append(("Jina", "❌ FALHOU", f"HTTP {r.status_code}: {r.text[:120]}"))


async def test_firecrawl() -> None:
    key = _key("FIRECRAWL_API_KEY")
    if _is_placeholder(key):
        results.append(("Firecrawl", "⏭ NÃO CONFIGURADA", ""))
        return
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.post(
            "https://api.firecrawl.dev/v1/scrape",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"url": "https://example.com", "formats": ["markdown"]},
        )
        if r.status_code == 200:
            data = r.json()
            results.append(("Firecrawl", "✅ OK", f"Scrape OK, {len(data.get('data', {}).get('markdown', ''))} chars"))
        else:
            results.append(("Firecrawl", "❌ FALHOU", f"HTTP {r.status_code}: {r.text[:120]}"))


async def test_tavily() -> None:
    key = _key("TAVILY_API_KEY")
    if _is_placeholder(key):
        results.append(("Tavily", "⏭ NÃO CONFIGURADA", ""))
        return
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.post(
            "https://api.tavily.com/search",
            json={"api_key": key, "query": "test", "max_results": 1},
        )
        if r.status_code == 200:
            data = r.json()
            n = len(data.get("results", []))
            results.append(("Tavily", "✅ OK", f"{n} resultado(s) retornado(s)"))
        else:
            results.append(("Tavily", "❌ FALHOU", f"HTTP {r.status_code}: {r.text[:120]}"))


async def test_speechify() -> None:
    key = _key("SPEECHIFY_API_KEY")
    if _is_placeholder(key):
        results.append(("Speechify", "⏭ NÃO CONFIGURADA", "chave = '...'"))
        return
    results.append(("Speechify", "✅ CONFIGURADA", "Não testada (requer voice_id)"))


async def test_unipile() -> None:
    key = _key("UNIPILE_API_KEY")
    if _is_placeholder(key):
        results.append(("Unipile", "⏭ NÃO CONFIGURADA", "chave = '...'"))
        return
    base = _key("UNIPILE_BASE_URL") or "https://api2.unipile.com:13246/api/v1"
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get(
            f"{base}/accounts",
            headers={"X-API-KEY": key},
        )
        if r.status_code == 200:
            results.append(("Unipile", "✅ OK", "Accounts endpoint OK"))
        else:
            results.append(("Unipile", "❌ FALHOU", f"HTTP {r.status_code}: {r.text[:120]}"))


async def test_pipedrive() -> None:
    key = _key("PIPEDRIVE_API_TOKEN")
    domain = _key("PIPEDRIVE_DOMAIN") or "compostoweb"
    if _is_placeholder(key):
        results.append(("Pipedrive", "⏭ NÃO CONFIGURADA", "chave = '...'"))
        return
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get(
            f"https://{domain}.pipedrive.com/api/v2/users/me",
            params={"api_token": key},
        )
        if r.status_code == 200:
            results.append(("Pipedrive", "✅ OK", "Autenticado"))
        else:
            results.append(("Pipedrive", "❌ FALHOU", f"HTTP {r.status_code}: {r.text[:120]}"))


async def main() -> None:
    # Carregar .env.dev
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(__file__), ".env.dev")
    load_dotenv(env_path, override=True)

    print("=" * 60)
    print("  TESTE DE API KEYS — .env.dev")
    print("=" * 60)
    print()

    tests = [
        test_openai(),
        test_gemini(),
        test_apify(),
        test_prospeo(),
        test_hunter(),
        test_apollo(),
        test_zerobounce(),
        test_jina(),
        test_firecrawl(),
        test_tavily(),
        test_speechify(),
        test_unipile(),
        test_pipedrive(),
    ]

    await asyncio.gather(*tests, return_exceptions=True)

    # Ordenar: OK primeiro, depois falhou, depois não configurada
    order = {"✅": 0, "⚠": 1, "❌": 2, "⏭": 3}
    results.sort(key=lambda x: order.get(x[1][0], 9))

    ok = sum(1 for _, s, _ in results if "✅" in s)
    fail = sum(1 for _, s, _ in results if "❌" in s)
    skip = sum(1 for _, s, _ in results if "⏭" in s)
    warn = sum(1 for _, s, _ in results if "⚠" in s)

    for name, status, detail in results:
        line = f"  {status}  {name:<12}"
        if detail:
            line += f" — {detail}"
        print(line)

    print()
    print("-" * 60)
    print(f"  Total: {len(results)} | ✅ {ok} OK | ❌ {fail} falha(s) | ⚠ {warn} aviso(s) | ⏭ {skip} não configurada(s)")
    print("-" * 60)

    if fail > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
