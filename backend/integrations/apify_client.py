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
from typing import Any, cast

import httpx
import structlog

from core.config import settings

logger = structlog.get_logger()

_BASE_URL = "https://api.apify.com/v2"
_TIMEOUT = 60.0
_POLL_INTERVAL_SECONDS = 5
_MAX_WAIT_SECONDS = 120  # 2 minutos por run


@dataclass
class ApifyLeadRaw:
    """Lead bruto retornado pelo Apify antes do enriquecimento."""

    name: str
    first_name: str | None = None
    last_name: str | None = None
    job_title: str | None = None
    company: str | None = None
    company_domain: str | None = None
    website: str | None = None
    linkedin_url: str | None = None
    linkedin_profile_id: str | None = None
    city: str | None = None
    location: str | None = None
    industry: str | None = None
    company_size: str | None = None
    segment: str | None = None
    phone: str | None = None
    email_corporate: str | None = None
    email_personal: str | None = None
    notes: str | None = None
    extra: dict[str, Any] = field(default_factory=lambda: cast(dict[str, Any], {}))


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
        location_query: str | None = None,
        categories: list[str] | None = None,
        max_items: int = 100,
    ) -> list[ApifyLeadRaw]:
        """
        Executa o Actor 'compass/crawler-google-places' para capturar
        empresas do Google Maps por query de busca.

        search_queries: ex. ["restaurantes São Paulo", "clínicas odontológicas Curitiba"]
        """
        actor_id = settings.APIFY_GOOGLE_MAPS_ACTOR_ID
        input_data: dict[str, Any] = {
            "searchStringsArray": search_queries,
            "searchTerms": search_queries,
            "maxCrawledPlacesPerSearch": max_items,
            "maxResults": max_items,
            "language": "pt-BR",
            "locationQuery": location_query,
            "categoryFilterWords": categories or [],
            "skipClosedPlaces": True,
            "exportPlaceUrls": False,
        }
        items = await self._run_actor(actor_id, input_data)
        return [_parse_maps_item(item) for item in items]

    # ── Captura via Base B2B ──────────────────────────────────────────

    async def run_b2b_leads(
        self,
        *,
        job_titles: list[str] | None = None,
        locations: list[str] | None = None,
        cities: list[str] | None = None,
        industries: list[str] | None = None,
        company_keywords: list[str] | None = None,
        company_sizes: list[str] | None = None,
        email_status: list[str] | None = None,
        max_items: int = 100,
    ) -> list[ApifyLeadRaw]:
        actor_id = settings.APIFY_B2B_LEADS_ACTOR_ID
        input_data: dict[str, Any] = {
            "fetch_count": max_items,
            "contact_job_title": job_titles or [],
            "contact_location": locations or [],
            "contact_city": cities or [],
            "company_industry": industries or [],
            "company_keywords": company_keywords or [],
            "size": company_sizes or [],
            "email_status": email_status or ["validated"],
        }
        items = await self._run_actor(actor_id, input_data)
        return [_parse_b2b_item(item) for item in items]

    # ── Enriquecimento via LinkedIn ───────────────────────────────────

    async def run_linkedin_enrichment(
        self,
        linkedin_urls: list[str],
        max_items: int = 50,
    ) -> list[ApifyLeadRaw]:
        actor_id = settings.APIFY_LINKEDIN_ENRICH_ACTOR_ID
        input_data: dict[str, Any] = {
            "profileUrls": linkedin_urls,
            "urls": linkedin_urls,
            "linkedin_urls": linkedin_urls,
            "maxResults": max_items,
            "max_items": max_items,
        }
        items = await self._run_actor(actor_id, input_data)
        return [_parse_linkedin_enrichment_item(item) for item in items]

    # ── Helpers internos ──────────────────────────────────────────────

    async def _run_actor(self, actor_id: str, input_data: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Dispara um Actor, aguarda sua conclusão e retorna os itens do dataset.
        Usa polling com intervalo de _POLL_INTERVAL_SECONDS.
        """
        if not settings.APIFY_API_TOKEN:
            raise RuntimeError("APIFY_API_TOKEN não configurado.")

        # Apify usa "~" como separador owner/actor na URL REST
        actor_path = actor_id.replace("/", "~")

        # Dispara o run
        run_response = await self._client.post(
            f"/acts/{actor_path}/runs",
            json=input_data,
        )
        run_response.raise_for_status()
        run = run_response.json().get("data", {})
        run_id: str = run["id"]
        dataset_id: str = run["defaultDatasetId"]

        logger.info("apify.actor.started", actor=actor_id, run_id=run_id)

        # Aguarda conclusão
        elapsed = 0
        status = "RUNNING"
        while elapsed < _MAX_WAIT_SECONDS:
            await asyncio.sleep(_POLL_INTERVAL_SECONDS)
            elapsed += _POLL_INTERVAL_SECONDS

            status_response = await self._client.get(f"/actor-runs/{run_id}")
            status_response.raise_for_status()
            status = status_response.json().get("data", {}).get("status", "")

            logger.info(
                "apify.actor.polling",
                actor=actor_id,
                run_id=run_id,
                status=status,
                elapsed_s=elapsed,
            )

            if status == "SUCCEEDED":
                break
            elif status in ("FAILED", "ABORTED", "TIMED-OUT"):
                raise RuntimeError(f"Apify Actor {actor_id} falhou com status: {status}")
        else:
            raise RuntimeError(
                f"Apify Actor {actor_id} excedeu timeout de {_MAX_WAIT_SECONDS}s (status={status})"
            )

        # Busca os itens do dataset
        items_response = await self._client.get(
            f"/datasets/{dataset_id}/items",
            params={"format": "json", "clean": "true"},
        )
        items_response.raise_for_status()
        items = cast(list[dict[str, Any]], items_response.json())
        logger.info("apify.actor.done", actor=actor_id, run_id=run_id, items=len(items))
        return items

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> ApifyClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()


# ── Parsers de resposta ───────────────────────────────────────────────


def _parse_maps_item(item: dict[str, Any]) -> ApifyLeadRaw:
    return ApifyLeadRaw(
        name=item.get("title") or item.get("name") or "",
        company=item.get("title") or item.get("name"),
        company_domain=_extract_domain(item.get("website")),
        website=item.get("website"),
        city=item.get("city") or _extract_city(item.get("address", "")),
        location=item.get("address") or item.get("city"),
        industry=item.get("categoryName") or item.get("category"),
        phone=item.get("phone"),
        segment=item.get("categoryName") or item.get("category"),
        notes=item.get("address"),
        extra=item,
    )


def _parse_b2b_item(item: dict[str, Any]) -> ApifyLeadRaw:
    return ApifyLeadRaw(
        name=item.get("full_name") or item.get("name") or "",
        first_name=item.get("first_name"),
        last_name=item.get("last_name"),
        job_title=item.get("job_title") or item.get("headline"),
        company=item.get("company_name"),
        company_domain=item.get("company_domain"),
        website=item.get("company_website"),
        linkedin_url=item.get("linkedin"),
        city=item.get("city") or item.get("company_city"),
        location=_join_location(item.get("city"), item.get("state"), item.get("country")),
        industry=item.get("industry"),
        company_size=item.get("company_size"),
        segment=item.get("industry"),
        phone=item.get("mobile_number") or item.get("company_phone"),
        email_corporate=item.get("email"),
        email_personal=item.get("personal_email"),
        extra=item,
    )


def _parse_linkedin_enrichment_item(item: dict[str, Any]) -> ApifyLeadRaw:
    return ApifyLeadRaw(
        name=item.get("full_name") or item.get("name") or "",
        first_name=item.get("first_name"),
        last_name=item.get("last_name"),
        job_title=item.get("job_title") or item.get("headline"),
        company=item.get("company_name") or item.get("name"),
        company_domain=_extract_domain(item.get("company_website") or item.get("website")),
        website=item.get("company_website") or item.get("website"),
        linkedin_url=item.get("url"),
        linkedin_profile_id=item.get("public_identifier") or item.get("id"),
        city=item.get("city") or item.get("hq"),
        location=_join_location(item.get("city"), item.get("country")),
        industry=item.get("company_industry") or item.get("industry"),
        company_size=item.get("company_size"),
        segment=item.get("company_industry") or item.get("industry"),
        notes=item.get("summary") or item.get("tagline"),
        extra=item,
    )


def _extract_city(address: str) -> str | None:
    """Extrai a cidade de um endereço livre (heurística simples)."""
    parts = [p.strip() for p in address.split(",")]
    return parts[-2] if len(parts) >= 2 else None


def _extract_domain(website: str | None) -> str | None:
    if not website:
        return None
    normalized = website.replace("https://", "").replace("http://", "")
    return normalized.split("/")[0] or None


def _join_location(*parts: str | None) -> str | None:
    values = [part.strip() for part in parts if part and part.strip()]
    if not values:
        return None
    return ", ".join(values)


# Singleton
apify_client = ApifyClient()
