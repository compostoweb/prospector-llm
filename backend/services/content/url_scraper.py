"""
services/content/url_scraper.py

Extrai metadados (title, description, thumbnail) de uma URL externa
para alimentar a prévia de Article (link share LinkedIn).

Estratégia:
  1. Cache Redis (TTL 24h) por hash da URL
  2. Tenta Firecrawl /scrape (retorna metadados estruturados via OpenGraph)
  3. Fallback: parse manual das primeiras tags <meta og:*> via httpx + regex
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import TypedDict

import httpx
import structlog

from core.config import settings
from core.redis_client import redis_client

logger = structlog.get_logger()

_CACHE_TTL = 24 * 60 * 60  # 24h
_FIRECRAWL_BASE = "https://api.firecrawl.dev/v1"


class ScrapedMetadata(TypedDict):
    title: str | None
    description: str | None
    thumbnail_url: str | None


def _cache_key(url: str) -> str:
    h = hashlib.sha1(url.encode("utf-8")).hexdigest()
    return f"content:url_scraper:{h}"


async def scrape_url(url: str, *, force_refresh: bool = False) -> ScrapedMetadata:
    """
    Retorna metadados básicos da URL (com cache).

    Sempre retorna dict com 3 campos. Campos podem ser None se não encontrados.
    """
    key = _cache_key(url)

    if not force_refresh:
        cached = await redis_client.get(key)
        if cached:
            try:
                return json.loads(cached)  # type: ignore[no-any-return]
            except json.JSONDecodeError:
                pass

    metadata: ScrapedMetadata = {"title": None, "description": None, "thumbnail_url": None}

    # 1) Firecrawl
    if settings.FIRECRAWL_API_KEY:
        metadata = await _scrape_firecrawl(url, settings.FIRECRAWL_API_KEY) or metadata

    # 2) Fallback manual (se algo ainda está vazio)
    if not (metadata.get("title") and metadata.get("description")):
        fallback = await _scrape_fallback(url)
        if fallback:
            if not metadata.get("title"):
                metadata["title"] = fallback.get("title")
            if not metadata.get("description"):
                metadata["description"] = fallback.get("description")
            if not metadata.get("thumbnail_url"):
                metadata["thumbnail_url"] = fallback.get("thumbnail_url")

    await redis_client.set(key, json.dumps(metadata), ex=_CACHE_TTL)
    return metadata


async def _scrape_firecrawl(url: str, api_key: str) -> ScrapedMetadata | None:
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                f"{_FIRECRAWL_BASE}/scrape",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "url": url,
                    "formats": ["markdown"],
                    "onlyMainContent": True,
                },
            )
        if resp.status_code >= 400:
            logger.warning(
                "url_scraper.firecrawl_http_error",
                url=url,
                status=resp.status_code,
            )
            return None
        data = resp.json().get("data") or {}
        meta = data.get("metadata") or {}
        return {
            "title": meta.get("title") or meta.get("ogTitle"),
            "description": meta.get("description") or meta.get("ogDescription"),
            "thumbnail_url": meta.get("ogImage") or meta.get("twitterImage"),
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("url_scraper.firecrawl_failed", url=url, error=str(exc))
        return None


_OG_TAG = re.compile(
    r'<meta[^>]+(?:property|name)=["\'](og:title|og:description|og:image'
    r'|twitter:title|twitter:description|twitter:image|description)["\']'
    r'[^>]+content=["\']([^"\']+)["\']',
    flags=re.IGNORECASE,
)
_TITLE_TAG = re.compile(r"<title[^>]*>([^<]+)</title>", flags=re.IGNORECASE)


async def _scrape_fallback(url: str) -> ScrapedMetadata | None:
    try:
        async with httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; CompostoWebBot/1.0; +https://compostoweb.com.br)"
                )
            },
        ) as client:
            resp = await client.get(url)
        if resp.status_code >= 400:
            return None
        html = resp.text[:60_000]  # limita
        title: str | None = None
        description: str | None = None
        thumbnail: str | None = None
        for match in _OG_TAG.finditer(html):
            name = match.group(1).lower()
            value = match.group(2).strip()
            if name in ("og:title", "twitter:title") and not title:
                title = value
            elif (
                name in ("og:description", "twitter:description", "description") and not description
            ):
                description = value
            elif name in ("og:image", "twitter:image") and not thumbnail:
                thumbnail = value
        if not title:
            tm = _TITLE_TAG.search(html)
            if tm:
                title = tm.group(1).strip()
        return {
            "title": title,
            "description": description,
            "thumbnail_url": thumbnail,
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("url_scraper.fallback_failed", url=url, error=str(exc))
        return None
