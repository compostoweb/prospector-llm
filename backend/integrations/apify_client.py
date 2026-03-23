"""
integrations/apify_client.py

Cliente HTTP assíncrono para a Apify API.

Responsabilidades:
  - Disparar Actors do Apify para captura de leads
  - Actor Google Maps: busca empresas por categoria/cidade
  - Actor LinkedIn: busca perfis por filtros de cargo/empresa/setor
  - Aguardar a conclusão do run e retornar os itens do dataset

Base URL: https://api.apify.com/v2
Auth:     Authorization: Bearer {APIFY_API_TOKEN}

Os Actor IDs são configurados via settings. Os defaults usam Actors públicos populares.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

import httpx
import structlog

from core.config import settings

logger = structlog.get_logger()

_BASE_URL = "https://api.apify.com/v2"
_TIMEOUT = 60.0
_POLL_INTERVAL_SECONDS = 5
_MAX_WAIT_SECONDS = 300  # 5 minutos


@dataclass
class ApifyLeadRaw:
    """Lead bruto retornado pelo Apify antes do enriquecimento."""
    name: str
    company: str | None = None
    website: str | None = None
    linkedin_url: str | None = None
    city: str | None = None
    segment: str | None = None
    phone: str | None = None
    extra: dict = field(default_factory=dict)


class ApifyClient:
    """
    Cliente assíncrono para disparar e aguardar Actors do Apify.
    """

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=_BASE_URL,
            headers={"Authorization": f"Bearer {settings.APIFY_API_TOKEN or ''}"},
            timeout=_TIMEOUT,
        )

    # ── Captura via Google Maps ───────────────────────────────────────

    async def run_google_maps(
        self,
        search_queries: list[str],
        max_items: int = 100,
    ) -> list[ApifyLeadRaw]:
        """
        Executa o Actor 'compass/crawler-google-places' para capturar
        empresas do Google Maps por query de busca.

        search_queries: ex. ["restaurantes São Paulo", "clínicas odontológicas Curitiba"]
        """
        actor_id = "compass/crawler-google-places"
        input_data = {
            "searchStringsArray": search_queries,
            "maxCrawledPlacesPerSearch": max_items,
            "language": "pt",
            "exportPlaceUrls": False,
        }
        items = await self._run_actor(actor_id, input_data)
        return [_parse_maps_item(item) for item in items]

    # ── Captura via LinkedIn ──────────────────────────────────────────

    async def run_linkedin_search(
        self,
        titles: list[str],
        locations: list[str],
        max_items: int = 50,
    ) -> list[ApifyLeadRaw]:
        """
        Executa o Actor 'curious_coder/linkedin-profile-scraper' para
        capturar perfis LinkedIn por cargo e localização.

        titles:    ex. ["CEO", "Diretor Comercial", "Sócio"]
        locations: ex. ["São Paulo", "Rio de Janeiro"]
        """
        actor_id = "curious_coder/linkedin-profile-scraper"
        input_data = {
            "searchQueries": [
                f"{title} {location}"
                for title in titles
                for location in locations
            ],
            "maxResults": max_items,
        }
        items = await self._run_actor(actor_id, input_data)
        return [_parse_linkedin_item(item) for item in items]

    # ── Helpers internos ──────────────────────────────────────────────

    async def _run_actor(self, actor_id: str, input_data: dict) -> list[dict]:
        """
        Dispara um Actor, aguarda sua conclusão e retorna os itens do dataset.
        Usa polling com intervalo de _POLL_INTERVAL_SECONDS.
        """
        # Dispara o run
        run_response = await self._client.post(
            f"/acts/{actor_id}/runs",
            json=input_data,
        )
        run_response.raise_for_status()
        run = run_response.json().get("data", {})
        run_id: str = run["id"]
        dataset_id: str = run["defaultDatasetId"]

        logger.info("apify.actor.started", actor=actor_id, run_id=run_id)

        # Aguarda conclusão
        elapsed = 0
        while elapsed < _MAX_WAIT_SECONDS:
            await asyncio.sleep(_POLL_INTERVAL_SECONDS)
            elapsed += _POLL_INTERVAL_SECONDS

            status_response = await self._client.get(f"/actor-runs/{run_id}")
            status_response.raise_for_status()
            status = status_response.json().get("data", {}).get("status", "")

            if status == "SUCCEEDED":
                break
            elif status in ("FAILED", "ABORTED", "TIMED-OUT"):
                raise RuntimeError(f"Apify Actor {actor_id} falhou com status: {status}")

        # Busca os itens do dataset
        items_response = await self._client.get(
            f"/datasets/{dataset_id}/items",
            params={"format": "json", "clean": "true"},
        )
        items_response.raise_for_status()
        items: list[dict] = items_response.json()
        logger.info("apify.actor.done", actor=actor_id, run_id=run_id, items=len(items))
        return items

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "ApifyClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()


# ── Parsers de resposta ───────────────────────────────────────────────

def _parse_maps_item(item: dict) -> ApifyLeadRaw:
    return ApifyLeadRaw(
        name=item.get("title") or item.get("name") or "",
        company=item.get("title") or item.get("name"),
        website=item.get("website"),
        city=item.get("city") or _extract_city(item.get("address", "")),
        phone=item.get("phone"),
        segment=item.get("categoryName") or item.get("category"),
        extra=item,
    )


def _parse_linkedin_item(item: dict) -> ApifyLeadRaw:
    return ApifyLeadRaw(
        name=item.get("fullName") or item.get("name") or "",
        company=item.get("company") or item.get("currentCompany"),
        linkedin_url=item.get("url") or item.get("linkedinUrl"),
        city=item.get("location") or item.get("city"),
        segment=item.get("industry"),
        extra=item,
    )


def _extract_city(address: str) -> str | None:
    """Extrai a cidade de um endereço livre (heurística simples)."""
    parts = [p.strip() for p in address.split(",")]
    return parts[-2] if len(parts) >= 2 else None


# Singleton
apify_client = ApifyClient()
