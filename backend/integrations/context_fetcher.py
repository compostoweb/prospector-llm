"""
integrations/context_fetcher.py

Agrega contexto de múltiplas fontes (Jina, Firecrawl, Tavily) para enriquecer
o prompt do AI Composer com informações sobre a empresa do lead.

Estratégia:
  1. Tenta Jina Reader (gratuito, rápido) — converte HTML em Markdown limpo
  2. Em paralelo, tenta Firecrawl (mais robusto para SPAs/JS)
  3. Usa Tavily apenas para empresas sem website (busca pela URL do LinkedIn ou nome)
  4. Resultado é cacheado no Redis por 24h (chave: ctx:{sha256(url)})

Retorna uma string Markdown (máx ~4.000 tokens) pronta para injeção no prompt.
"""

from __future__ import annotations

import hashlib

import httpx
import structlog

from core.config import settings
from core.redis_client import redis_client

logger = structlog.get_logger()

_JINA_BASE = "https://r.jina.ai"
_FIRECRAWL_BASE = "https://api.firecrawl.dev/v1"
_TAVILY_BASE = "https://api.tavily.com"
_TIMEOUT = 30.0
_CACHE_TTL = 86_400  # 24h
_MAX_CHARS = 16_000  # ~4.000 tokens (margem generosa antes de cortar)


class ContextFetcher:
    """
    Agrega contexto de websites e buscas para enriquecer prompts de AI.
    """

    def __init__(self) -> None:
        self._http = httpx.AsyncClient(timeout=_TIMEOUT)

    async def fetch_from_website(self, website_url: str) -> str:
        """
        Retorna conteúdo Markdown extraído do website.

        Estratégia: Jina Reader (melhor esforço) → Firecrawl (fallback).
        Resultado cacheado por 24h.
        """
        cache_key = _cache_key(website_url)
        cached = await redis_client.get(cache_key)
        if cached:
            logger.debug("context_fetcher.cache_hit", url=website_url)
            return cached.decode() if isinstance(cached, bytes) else cached

        content = await self._fetch_jina(website_url)
        if not content:
            content = await self._fetch_firecrawl(website_url)
        if not content:
            content = ""

        content = _truncate(content)
        if content:
            await redis_client.set(cache_key, content, ex=_CACHE_TTL)

        return content

    async def search_company(self, company_name: str, website_url: str | None = None) -> str:
        """
        Busca informações sobre a empresa via Tavily.
        Usado quando não há website disponível.
        """
        query = f'"{company_name}" empresa site oficial informações'
        if website_url:
            query += f" {website_url}"

        cache_key = _cache_key(f"tavily:{query}")
        cached = await redis_client.get(cache_key)
        if cached:
            return cached.decode() if isinstance(cached, bytes) else cached

        content = await self._fetch_tavily(query)
        content = _truncate(content)
        if content:
            await redis_client.set(cache_key, content, ex=_CACHE_TTL)

        return content

    # ── Sources ───────────────────────────────────────────────────────

    async def _fetch_jina(self, url: str) -> str:
        """Converte o website em Markdown via Jina Reader (r.jina.ai)."""
        try:
            resp = await self._http.get(
                f"{_JINA_BASE}/{url}",
                headers={
                    "Authorization": f"Bearer {settings.JINA_API_KEY or ''}",
                    "Accept": "text/plain",
                },
            )
            resp.raise_for_status()
            content = resp.text.strip()
            logger.info("context_fetcher.jina_ok", url=url, chars=len(content))
            return content
        except Exception as exc:  # noqa: BLE001
            logger.warning("context_fetcher.jina_failed", url=url, error=str(exc))
            return ""

    async def _fetch_firecrawl(self, url: str) -> str:
        """Scrape via Firecrawl /scrape — retorna Markdown."""
        try:
            resp = await self._http.post(
                f"{_FIRECRAWL_BASE}/scrape",
                headers={"Authorization": f"Bearer {settings.FIRECRAWL_API_KEY or ''}"},
                json={"url": url, "formats": ["markdown"]},
            )
            resp.raise_for_status()
            data = resp.json()
            content = (data.get("data") or {}).get("markdown", "").strip()
            logger.info("context_fetcher.firecrawl_ok", url=url, chars=len(content))
            return content
        except Exception as exc:  # noqa: BLE001
            logger.warning("context_fetcher.firecrawl_failed", url=url, error=str(exc))
            return ""

    async def _fetch_tavily(self, query: str) -> str:
        """Busca informações via Tavily /search — agrega snippets dos resultados."""
        try:
            resp = await self._http.post(
                f"{_TAVILY_BASE}/search",
                json={
                    "api_key": settings.TAVILY_API_KEY or "",
                    "query": query,
                    "search_depth": "basic",
                    "max_results": 5,
                    "include_answer": True,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            parts: list[str] = []
            if answer := data.get("answer"):
                parts.append(answer)
            for result in data.get("results", []):
                if snippet := result.get("content", "").strip():
                    parts.append(snippet)
            content = "\n\n".join(parts)
            logger.info("context_fetcher.tavily_ok", query=query[:60], chars=len(content))
            return content
        except Exception as exc:  # noqa: BLE001
            logger.warning("context_fetcher.tavily_failed", query=query[:60], error=str(exc))
            return ""

    async def aclose(self) -> None:
        await self._http.aclose()


# ── Helpers ───────────────────────────────────────────────────────────

def _cache_key(url: str) -> str:
    digest = hashlib.sha256(url.encode()).hexdigest()[:16]
    return f"ctx:{digest}"


def _truncate(text: str) -> str:
    if len(text) <= _MAX_CHARS:
        return text
    return text[:_MAX_CHARS] + "\n\n[... conteúdo truncado ...]"


# Singleton
context_fetcher = ContextFetcher()
