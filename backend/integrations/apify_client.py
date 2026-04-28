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


# ── Registro de atores B2B disponíveis ───────────────────────────────
# Cada entrada expõe metadados para o frontend (nome, custo estimado, link).
# O campo "runner" mapeia para o método do ApifyClient que executa o ator.

B2B_ACTORS: list[dict[str, str]] = [
    {
        "id": "pipelinelabs/leads-finder-with-emails-apollo-lusha-zoominfo",
        "name": "Pipeline Labs — 250M+ Leads (recomendado)",
        "description": "250M+ contatos verificados, 100% email coverage, $1.50–$2.00/1k leads. Funciona no plano gratuito do Apify.",
        "pricing": "$1.50–$2.00 / 1k leads",
        "runner": "pipelinelabs",
    },
    {
        "id": "code_crafter/leads-finder",
        "name": "Code Crafter — Leads Finder",
        "description": "Base alternativa com email e telefone. Requer plano pago Apify ($49+/mês).",
        "pricing": "$1.50 / 1k leads (plano pago exigido)",
        "runner": "code_crafter",
    },
    {
        "id": "braveleads/leads-finder-linkedin-apollo-leads-generator",
        "name": "Brave Leads — Leads Finder",
        "description": "Alternativa com email corporativo e telefone. Rating 4.7 ⭐, 324 usuários/mês.",
        "pricing": "$1.50 / 1k leads (mín. 100 leads)",
        "runner": "braveleads",
    },
]


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
        actor_key: str = "pipelinelabs",
        job_titles: list[str] | None = None,
        locations: list[str] | None = None,
        cities: list[str] | None = None,
        industries: list[str] | None = None,
        company_keywords: list[str] | None = None,
        company_sizes: list[str] | None = None,
        email_status: list[str] | None = None,
        max_items: int = 100,
    ) -> list[ApifyLeadRaw]:
        """Despacha para o runner correto baseado no actor_key."""
        if actor_key == "pipelinelabs":
            return await self._run_b2b_pipelinelabs(
                job_titles=job_titles,
                locations=locations,
                cities=cities,
                industries=industries,
                company_keywords=company_keywords,
                company_sizes=company_sizes,
                max_items=max_items,
            )
        elif actor_key == "braveleads":
            return await self._run_b2b_braveleads(
                job_titles=job_titles,
                locations=locations,
                cities=cities,
                industries=industries,
                company_keywords=company_keywords,
                company_sizes=company_sizes,
                max_items=max_items,
            )
        else:
            # code_crafter (legado) ou qualquer outro ID desconhecido
            return await self._run_b2b_code_crafter(
                job_titles=job_titles,
                locations=locations,
                cities=cities,
                industries=industries,
                company_keywords=company_keywords,
                company_sizes=company_sizes,
                email_status=email_status,
                max_items=max_items,
            )

    async def _run_b2b_pipelinelabs(
        self,
        *,
        job_titles: list[str] | None = None,
        locations: list[str] | None = None,
        cities: list[str] | None = None,
        industries: list[str] | None = None,
        company_keywords: list[str] | None = None,
        company_sizes: list[str] | None = None,
        max_items: int = 100,
    ) -> list[ApifyLeadRaw]:
        """
        Runner para pipelinelabs/leads-finder-with-emails-apollo-lusha-zoominfo.
        Schema de input: personTitleIncludes, personLocationCountryIncludes,
        personLocationCityIncludes, companyIndustryIncludes, companySizeIncludes,
        companyKeywordIncludes, totalResults.
        Funciona no plano gratuito do Apify (free: 100 leads/run via API).
        """
        actor_id = "pipelinelabs/leads-finder-with-emails-apollo-lusha-zoominfo"
        input_data: dict[str, Any] = {
            "totalResults": max_items,
            # Não salvar cursor de progresso — cada run começa do zero.
            # Sem isso, runs com os mesmos filtros continuam de onde pararam e
            # quando chegam ao fim retornam 0 leads com diagnosisType "cursor_at_end".
            "dontSaveProgress": True,
            # Expande variantes comuns de cargo (CEO → Chief Executive Officer etc.)
            "includeTitleVariants": True,
        }

        if job_titles:
            input_data["personTitleIncludes"] = job_titles
        if locations:
            input_data["personLocationCountryIncludes"] = [
                _normalize_location_pipelinelabs(loc) for loc in locations
            ]
        if cities:
            input_data["personLocationCityIncludes"] = [c.strip() for c in cities]
        if industries:
            normalized_industries = [_normalize_industry_pipelinelabs(i) for i in industries]
            valid_industries = [v for v in normalized_industries if v is not None]
            if valid_industries:
                input_data["companyIndustryIncludes"] = valid_industries
        if company_keywords:
            input_data["companyKeywordIncludes"] = company_keywords
        if company_sizes:
            # pipelinelabs aceita: "1-10", "11-50", "51-200", "201-500", "501-1000",
            # "1001-5000", "5001-10000", "10001+"
            input_data["companySizeIncludes"] = _normalize_sizes_pipelinelabs(company_sizes)

        logger.debug(
            "apify.pipelinelabs.input",
            input_data=input_data,
        )

        items = await self._run_actor(actor_id, input_data)

        # O pipelinelabs mistura linhas de diagnóstico com leads reais no mesmo dataset.
        # Leads reais sempre têm firstName, linkedinUrl ou email.
        # Linhas de diagnóstico têm IMPORTANT_NOT_CHARGED/diagnosisType e NÃO têm firstName.
        lead_items = []
        for item in items:
            is_lead = bool(
                item.get("firstName")
                or item.get("fullName")
                or item.get("linkedinUrl")
                or item.get("email")
            )
            if not is_lead:
                logger.warning(
                    "apify.pipelinelabs.diagnostic_row",
                    why_zero=item.get("whyZero"),
                    summary=item.get("summary"),
                    diagnosis=item.get("diagnosisType"),
                    what_to_do=item.get("whatToDo"),
                    total_in_search=item.get("totalLeadsInSearch"),
                    monthly_limit=item.get("monthlyLimit"),
                    monthly_remaining=item.get("monthlyRemaining"),
                    reset_date=item.get("resetDate"),
                    hard_blockers=item.get("hardBlockers"),
                )
                continue
            lead_items.append(item)

        return [_parse_pipelinelabs_item(item) for item in lead_items]

    async def _run_b2b_braveleads(
        self,
        *,
        job_titles: list[str] | None = None,
        locations: list[str] | None = None,
        cities: list[str] | None = None,
        industries: list[str] | None = None,
        company_keywords: list[str] | None = None,
        company_sizes: list[str] | None = None,
        max_items: int = 100,
    ) -> list[ApifyLeadRaw]:
        """
        Runner para braveleads/leads-finder-linkedin-apollo-leads-generator.
        Schema: maxResults, personTitle, personCountry, functional, companyEmployeeSize.
        """
        actor_id = "braveleads/leads-finder-linkedin-apollo-leads-generator"
        input_data: dict[str, Any] = {"maxResults": max_items}

        if job_titles:
            input_data["personTitle"] = job_titles
        if locations:
            input_data["personCountry"] = [_normalize_location(loc) for loc in locations]
        if cities:
            input_data["personCity"] = [c.strip() for c in cities]
        if industries:
            input_data["companyIndustry"] = [i.strip().lower() for i in industries]
        if company_keywords:
            input_data["companyKeyword"] = company_keywords
        if company_sizes:
            input_data["companyEmployeeSize"] = company_sizes

        items = await self._run_actor(actor_id, input_data)
        return [_parse_b2b_item(item) for item in items]

    async def _run_b2b_code_crafter(
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
        """
        Runner legado para code_crafter/leads-finder.
        ATENÇÃO: requer plano pago Apify — retorna erro no plano gratuito.
        """
        actor_id = settings.APIFY_B2B_LEADS_ACTOR_ID
        input_data: dict[str, Any] = {
            "fetch_count": max_items,
            "email_status": email_status or ["validated"],
        }
        if job_titles:
            input_data["contact_job_title"] = job_titles
        if locations:
            input_data["contact_location"] = [_normalize_location(loc) for loc in locations]
        if cities:
            input_data["contact_city"] = [c.lower().strip() for c in cities]
        if industries:
            input_data["company_industry"] = [i.strip().lower() for i in industries]
        if company_keywords:
            input_data["company_keywords"] = company_keywords
        if company_sizes:
            normalized_sizes = [_normalize_company_size(s) for s in company_sizes]
            valid_sizes = [s for s in normalized_sizes if s is not None]
            invalid = [orig for orig, norm in zip(company_sizes, normalized_sizes) if norm is None]
            if invalid:
                raise RuntimeError(
                    f"Faixas de tamanho inválidas: {', '.join(invalid)}. "
                    f"Valores aceitos: {', '.join(_SIZE_CANONICAL)}."
                )
            input_data["size"] = valid_sizes
        items = await self._run_actor(
            actor_id,
            input_data,
            run_params={"maxTotalChargeUsd": settings.APIFY_B2B_MAX_CHARGE_USD},
        )
        return [_parse_b2b_item(item) for item in items]

    # ── Enriquecimento via LinkedIn ───────────────────────────────────

    async def run_linkedin_enrichment(
        self,
        linkedin_urls: list[str],
        max_items: int = 50,
    ) -> list[ApifyLeadRaw]:
        actor_id = settings.APIFY_LINKEDIN_ENRICH_ACTOR_ID
        input_data: dict[str, Any] = {
            "urls": linkedin_urls,
            "profileScraperMode": "Profile details no email ($4 per 1k)",
        }
        # Enrichment de perfis demora ~10-15s por perfil; usar timeout dedicado
        items = await self._run_actor(actor_id, input_data, max_wait_seconds=600)
        return [_parse_linkedin_enrichment_item(item) for item in items]

    # ── Helpers internos ──────────────────────────────────────────────

    async def _run_actor(
        self,
        actor_id: str,
        input_data: dict[str, Any],
        run_params: dict[str, Any] | None = None,
        max_wait_seconds: int = _MAX_WAIT_SECONDS,
    ) -> list[dict[str, Any]]:
        """
        Dispara um Actor, aguarda sua conclusão e retorna os itens do dataset.
        Usa polling com intervalo de _POLL_INTERVAL_SECONDS.
        run_params são passados como query params ao endpoint /runs (ex: maxTotalChargeUsd).
        """
        if not settings.APIFY_API_TOKEN:
            raise RuntimeError("APIFY_API_TOKEN não configurado.")

        # Apify usa "~" como separador owner/actor na URL REST
        actor_path = actor_id.replace("/", "~")

        # Dispara o run
        run_response = await self._client.post(
            f"/acts/{actor_path}/runs",
            json=input_data,
            params=run_params or {},
        )
        if run_response.is_error:
            try:
                apify_msg: str = (
                    run_response.json().get("error", {}).get("message", run_response.text[:300])
                )
            except Exception:
                apify_msg = run_response.text[:300]
            logger.error(
                "apify.actor.start_failed",
                actor=actor_id,
                status=run_response.status_code,
                body=apify_msg,
            )
            raise RuntimeError(apify_msg)
        run = run_response.json().get("data", {})
        run_id: str = run["id"]
        dataset_id: str = run["defaultDatasetId"]

        logger.info("apify.actor.started", actor=actor_id, run_id=run_id)

        # Aguarda conclusão
        elapsed = 0
        status = "RUNNING"
        while elapsed < max_wait_seconds:
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
                f"Apify Actor {actor_id} excedeu timeout de {max_wait_seconds}s (status={status})"
            )

        # Busca os itens do dataset
        items_response = await self._client.get(
            f"/datasets/{dataset_id}/items",
            params={"format": "json", "clean": "true"},
        )
        items_response.raise_for_status()
        all_items = cast(list[dict[str, Any]], items_response.json())

        # O ator pode retornar itens com campo "error" quando não encontra resultados
        error_items = [i for i in all_items if "error" in i and len(i) == 1]
        items = [i for i in all_items if not ("error" in i and len(i) == 1)]

        if error_items:
            error_msg = error_items[0].get("error", "Erro desconhecido do ator Apify")
            logger.warning(
                "apify.actor.error_items",
                actor=actor_id,
                run_id=run_id,
                error=error_msg,
                count=len(error_items),
            )
            if not items:
                raise RuntimeError(f"Apify Actor retornou erro: {error_msg}")

        logger.info("apify.actor.done", actor=actor_id, run_id=run_id, items=len(items))
        return items

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> ApifyClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()


# ── Helpers de normalização ────────────────────────────────────────────

# O ator code_crafter/leads-finder exige contact_location em inglês e minúsculas.
# Mapeamento dos nomes mais comuns em português → inglês aceito pelo ator.
_LOCATION_PT_TO_EN: dict[str, str] = {
    "brasil": "brazil",
    "estados unidos": "united states",
    "reino unido": "united kingdom",
    "alemanha": "germany",
    "franca": "france",
    "frança": "france",
    "espanha": "spain",
    "italia": "italy",
    "itália": "italy",
    "holanda": "netherlands",
    "paises baixos": "netherlands",
    "países baixos": "netherlands",
    "belgica": "belgium",
    "bélgica": "belgium",
    "suecia": "sweden",
    "suécia": "sweden",
    "polonia": "poland",
    "polônia": "poland",
    "africa do sul": "south africa",
    "áfrica do sul": "south africa",
    "republica tcheca": "czech republic",
    "república tcheca": "czech republic",
    "colombia": "colombia",
    "colômbia": "colombia",
    "vietna": "vietnam",
    "vietnã": "vietnam",
}

# Valores EXATOS aceitos pelo pipelinelabs (case-sensitive).
# Chave: qualquer variação em lowercase que o usuário pode digitar.
# Valor: string exata exigida pelo ator.
_PIPELINELABS_COUNTRY_MAP: dict[str, str] = {
    # Português → exato
    "brasil": "Brazil",
    "estados unidos": "United States",
    "reino unido": "United Kingdom",
    "canada": "Canada",
    "franca": "France",
    "frança": "France",
    "italia": "Italy",
    "itália": "Italy",
    "espanha": "Spain",
    "australia": "Australia",
    "australia": "Australia",
    "austrália": "Australia",
    "alemanha": "Germany",
    "holanda": "Netherlands",
    "paises baixos": "Netherlands",
    "países baixos": "Netherlands",
    "belgica": "Belgium",
    "bélgica": "Belgium",
    "suecia": "Sweden",
    "suécia": "Sweden",
    "noruega": "Norway",
    "dinamarca": "Denmark",
    "finlandia": "Finland",
    "finlândia": "Finland",
    "suica": "Switzerland",
    "suíça": "Switzerland",
    "austria": "Austria",
    "áustria": "Austria",
    "portugal": "Portugal",
    "polonia": "Poland",
    "polônia": "Poland",
    "romenia": "Romania",
    "romênia": "Romania",
    "turquia": "Turkey",
    "russia": "Russia",
    "rússia": "Russia",
    "china": "China",
    "japao": "Japan",
    "japão": "Japan",
    "india": "India",
    "índia": "India",
    "paquistao": "Pakistan",
    "paquistão": "Pakistan",
    "indonesia": "Indonesia",
    "indonésia": "Indonesia",
    "filipinas": "Philippines",
    "tailandia": "Thailand",
    "tailândia": "Thailand",
    "vietnam": "Vietnam",
    "vietna": "Vietnam",
    "vietnã": "Vietnam",
    "coreia do sul": "South Korea",
    "cingapura": "Singapore",
    "singapura": "Singapore",
    "malaysia": "Malaysia",
    "malásia": "Malaysia",
    "mexico": "Mexico",
    "méxico": "Mexico",
    "argentina": "Argentina",
    "colombia": "Colombia",
    "colômbia": "Colombia",
    "chile": "Chile",
    "peru": "Peru",
    "venezuela": "Venezuela",
    "equador": "Ecuador",
    "bolivia": "Bolivia",
    "bolívia": "Bolivia",
    "paraguai": "Paraguay",
    "uruguai": "Uruguay",
    "nigeria": "Nigeria",
    "nigéria": "Nigeria",
    "africa do sul": "South Africa",
    "áfrica do sul": "South Africa",
    "quenia": "Kenya",
    "quênia": "Kenya",
    "ghana": "Ghana",
    "marrocos": "Morocco",
    "egito": "Egypt",
    "egipto": "Egypt",
    "israel": "Israel",
    "arabia saudita": "Saudi Arabia",
    "arábia saudita": "Saudi Arabia",
    "emirados arabes unidos": "United Arab Emirates",
    "emirados árabes unidos": "United Arab Emirates",
    "irlanda": "Ireland",
    "nova zelandia": "New Zealand",
    "nova zelândia": "New Zealand",
    "hungria": "Hungary",
    "hungria": "Hungary",
    "republica tcheca": "Czech Republic",
    "república tcheca": "Czech Republic",
    "eslovaquia": "Slovakia",
    "eslováquia": "Slovakia",
    "croacia": "Croatia",
    "croácia": "Croatia",
    "eslovenia": "Slovenia",
    "eslovênia": "Slovenia",
    "bulgaria": "Bulgaria",
    "bulgária": "Bulgaria",
    "grecia": "Greece",
    "grécia": "Greece",
    "servia": "Serbia",
    "sérvia": "Serbia",
    "ucrania": "Ukraine",
    "ucrânia": "Ukraine",
    "bielorrussia": "Belarus",
    "bielorrússia": "Belarus",
    "cazaquistao": "Kazakhstan",
    "cazaquistão": "Kazakhstan",
    "azerbaijao": "Azerbaijan",
    "azerbaijão": "Azerbaijan",
    # English lowercase → exato (para quem digita em inglês sem maiúsculas)
    "brazil": "Brazil",
    "united states": "United States",
    "us": "United States",
    "usa": "United States",
    "united kingdom": "United Kingdom",
    "uk": "United Kingdom",
    "canada": "Canada",
    "france": "France",
    "italy": "Italy",
    "spain": "Spain",
    "australia": "Australia",
    "germany": "Germany",
    "netherlands": "Netherlands",
    "belgium": "Belgium",
    "sweden": "Sweden",
    "norway": "Norway",
    "denmark": "Denmark",
    "finland": "Finland",
    "switzerland": "Switzerland",
    "austria": "Austria",
    "portugal": "Portugal",
    "poland": "Poland",
    "romania": "Romania",
    "turkey": "Turkey",
    "russia": "Russia",
    "china": "China",
    "japan": "Japan",
    "india": "India",
    "pakistan": "Pakistan",
    "indonesia": "Indonesia",
    "philippines": "Philippines",
    "thailand": "Thailand",
    "vietnam": "Vietnam",
    "south korea": "South Korea",
    "singapore": "Singapore",
    "malaysia": "Malaysia",
    "mexico": "Mexico",
    "argentina": "Argentina",
    "colombia": "Colombia",
    "chile": "Chile",
    "peru": "Peru",
    "venezuela": "Venezuela",
    "ecuador": "Ecuador",
    "bolivia": "Bolivia",
    "paraguay": "Paraguay",
    "uruguay": "Uruguay",
    "nigeria": "Nigeria",
    "south africa": "South Africa",
    "kenya": "Kenya",
    "ghana": "Ghana",
    "morocco": "Morocco",
    "egypt": "Egypt",
    "israel": "Israel",
    "saudi arabia": "Saudi Arabia",
    "united arab emirates": "United Arab Emirates",
    "uae": "United Arab Emirates",
    "ireland": "Ireland",
    "new zealand": "New Zealand",
    "hungary": "Hungary",
    "czech republic": "Czech Republic",
    "slovakia": "Slovakia",
    "croatia": "Croatia",
    "slovenia": "Slovenia",
    "bulgaria": "Bulgaria",
    "greece": "Greece",
    "serbia": "Serbia",
    "ukraine": "Ukraine",
    "belarus": "Belarus",
    "kazakhstan": "Kazakhstan",
    "azerbaijan": "Azerbaijan",
    "hong kong": "Hong Kong",
    "taiwan": "Taiwan",
    "puerto rico": "Puerto Rico",
    "luxembourg": "Luxembourg",
    "cyprus": "Cyprus",
    "malta": "Malta",
    "iceland": "Iceland",
    "estonia": "Estonia",
    "latvia": "Latvia",
    "lithuania": "Lithuania",
    "andorra": "Andorra",
    "monaco": "Monaco",
    "liechtenstein": "Liechtenstein",
}


def _normalize_location_pipelinelabs(value: str) -> str:
    """Converte país para o valor exato aceito pelo ator pipelinelabs (case-sensitive)."""
    key = value.strip().lower()
    mapped = _PIPELINELABS_COUNTRY_MAP.get(key)
    if mapped:
        return mapped
    # Fallback: title-case do valor original (melhor chance de aceitar do que lowercase)
    return value.strip().title()


# Lista completa de indústrias aceitas pelo pipelinelabs.
_PIPELINELABS_INDUSTRIES: list[str] = [
    "Accounting",
    "Agriculture",
    "Airlines/Aviation",
    "Animation",
    "Apparel & Fashion",
    "Architecture & Planning",
    "Automotive",
    "Aviation & Aerospace",
    "Banking",
    "Biotechnology",
    "Broadcast Media",
    "Building Materials",
    "Capital Markets",
    "Chemicals",
    "Civil Engineering",
    "Commercial Real Estate",
    "Computer & Network Security",
    "Computer Games",
    "Computer Hardware",
    "Computer Networking",
    "Computer Software",
    "Construction",
    "Consumer Electronics",
    "Consumer Goods",
    "Consumer Services",
    "Defense & Space",
    "Design",
    "E-Learning",
    "Education Management",
    "Electrical/Electronic Manufacturing",
    "Entertainment",
    "Environmental Services",
    "Events Services",
    "Financial Services",
    "Food & Beverages",
    "Food Production",
    "Furniture",
    "Government Administration",
    "Graphic Design",
    "Health, Wellness & Fitness",
    "Higher Education",
    "Hospital & Health Care",
    "Hospitality",
    "Human Resources",
    "Industrial Automation",
    "Information Services",
    "Information Technology & Services",
    "Insurance",
    "Internet",
    "Investment Banking",
    "Investment Management",
    "Law Practice",
    "Legal Services",
    "Leisure, Travel & Tourism",
    "Logistics & Supply Chain",
    "Luxury Goods & Jewelry",
    "Machinery",
    "Management Consulting",
    "Market Research",
    "Marketing & Advertising",
    "Mechanical or Industrial Engineering",
    "Media Production",
    "Medical Devices",
    "Medical Practice",
    "Mental Health Care",
    "Mining & Metals",
    "Non-Profit Organization Management",
    "Oil & Energy",
    "Online Media",
    "Outsourcing/Offshoring",
    "Pharmaceuticals",
    "Photography",
    "Professional Training & Coaching",
    "Public Relations & Communications",
    "Publishing",
    "Real Estate",
    "Recreation & Sports",
    "Renewables & Environment",
    "Research",
    "Restaurants",
    "Retail",
    "Security & Investigations",
    "Semiconductors",
    "Staffing & Recruiting",
    "Telecommunications",
    "Transportation/Trucking/Railroad",
    "Utilities",
    "Venture Capital & Private Equity",
    "Warehousing",
    "Wholesale",
    "Wine & Spirits",
    "Wireless",
    "Writing & Editing",
]

# Lookup lowercase → valor exato (para busca por substring/alias também)
_PIPELINELABS_INDUSTRY_LOWER: dict[str, str] = {v.lower(): v for v in _PIPELINELABS_INDUSTRIES}

# Mapeamentos de termos em PT/EN → valor exato pipelinelabs
_PIPELINELABS_INDUSTRY_MAP: dict[str, str] = {
    # Português
    "tecnologia": "Information Technology & Services",
    "tecnologia da informacao": "Information Technology & Services",
    "tecnologia da informação": "Information Technology & Services",
    "ti": "Information Technology & Services",
    "software": "Computer Software",
    "hardware": "Computer Hardware",
    "internet": "Internet",
    "jogos": "Computer Games",
    "saude": "Hospital & Health Care",
    "saúde": "Hospital & Health Care",
    "hospital": "Hospital & Health Care",
    "saude e bem estar": "Health, Wellness & Fitness",
    "saúde e bem estar": "Health, Wellness & Fitness",
    "fitness": "Health, Wellness & Fitness",
    "farmaceutica": "Pharmaceuticals",
    "farmacêutica": "Pharmaceuticals",
    "farma": "Pharmaceuticals",
    "dispositivos medicos": "Medical Devices",
    "dispositivos médicos": "Medical Devices",
    "clinica": "Medical Practice",
    "clínica": "Medical Practice",
    "saude mental": "Mental Health Care",
    "saúde mental": "Mental Health Care",
    "educacao": "Education Management",
    "educação": "Education Management",
    "ensino superior": "Higher Education",
    "e-learning": "E-Learning",
    "elearning": "E-Learning",
    "marketing": "Marketing & Advertising",
    "publicidade": "Marketing & Advertising",
    "propaganda": "Marketing & Advertising",
    "relacoes publicas": "Public Relations & Communications",
    "relações públicas": "Public Relations & Communications",
    "rp": "Public Relations & Communications",
    "financas": "Financial Services",
    "finanças": "Financial Services",
    "financeiro": "Financial Services",
    "banco": "Banking",
    "bancario": "Banking",
    "bancário": "Banking",
    "seguros": "Insurance",
    "seguro": "Insurance",
    "investimento": "Investment Management",
    "gestao de investimentos": "Investment Management",
    "gestão de investimentos": "Investment Management",
    "banco de investimento": "Investment Banking",
    "capital de risco": "Venture Capital & Private Equity",
    "venture capital": "Venture Capital & Private Equity",
    "mercado de capitais": "Capital Markets",
    "contabilidade": "Accounting",
    "auditoria": "Accounting",
    "consultoria": "Management Consulting",
    "consultoria de gestao": "Management Consulting",
    "consultoria de gestão": "Management Consulting",
    "pesquisa de mercado": "Market Research",
    "pesquisa": "Research",
    "varejo": "Retail",
    "comercio varejista": "Retail",
    "comércio varejista": "Retail",
    "atacado": "Wholesale",
    "bens de consumo": "Consumer Goods",
    "servicos ao consumidor": "Consumer Services",
    "serviços ao consumidor": "Consumer Services",
    "eletronicos": "Consumer Electronics",
    "eletrônicos": "Consumer Electronics",
    "eletronico": "Consumer Electronics",
    "eletrônico": "Consumer Electronics",
    "construcao": "Construction",
    "construção": "Construction",
    "engenharia civil": "Civil Engineering",
    "arquitetura": "Architecture & Planning",
    "planejamento urbano": "Architecture & Planning",
    "imoveis": "Real Estate",
    "imóveis": "Real Estate",
    "imobiliario": "Real Estate",
    "imobiliário": "Real Estate",
    "imoveis comerciais": "Commercial Real Estate",
    "imóveis comerciais": "Commercial Real Estate",
    "logistica": "Logistics & Supply Chain",
    "logística": "Logistics & Supply Chain",
    "cadeia de suprimentos": "Logistics & Supply Chain",
    "transporte": "Transportation/Trucking/Railroad",
    "aviacao": "Airlines/Aviation",
    "aviação": "Airlines/Aviation",
    "aerospacial": "Aviation & Aerospace",
    "aeroespacial": "Aviation & Aerospace",
    "automovel": "Automotive",
    "automóvel": "Automotive",
    "automotivo": "Automotive",
    "industria automotiva": "Automotive",
    "indústria automotiva": "Automotive",
    "quimica": "Chemicals",
    "química": "Chemicals",
    "mineracao": "Mining & Metals",
    "mineração": "Mining & Metals",
    "oleo e gas": "Oil & Energy",
    "óleo e gás": "Oil & Energy",
    "energia": "Oil & Energy",
    "energia renovavel": "Renewables & Environment",
    "energia renovável": "Renewables & Environment",
    "meio ambiente": "Environmental Services",
    "ambiental": "Environmental Services",
    "telecomunicacoes": "Telecommunications",
    "telecomunicações": "Telecommunications",
    "telecom": "Telecommunications",
    "midia": "Online Media",
    "mídia": "Online Media",
    "midia online": "Online Media",
    "mídia online": "Online Media",
    "producao de midia": "Media Production",
    "produção de mídia": "Media Production",
    "entretenimento": "Entertainment",
    "jogos e entretenimento": "Computer Games",
    "publicacao": "Publishing",
    "publicação": "Publishing",
    "editorial": "Publishing",
    "redacao": "Writing & Editing",
    "redação": "Writing & Editing",
    "design": "Design",
    "design grafico": "Graphic Design",
    "design gráfico": "Graphic Design",
    "fotografia": "Photography",
    "animacao": "Animation",
    "animação": "Animation",
    "vestuario": "Apparel & Fashion",
    "vestuário": "Apparel & Fashion",
    "moda": "Apparel & Fashion",
    "moveis": "Furniture",
    "móveis": "Furniture",
    "alimentos e bebidas": "Food & Beverages",
    "alimentos": "Food Production",
    "bebidas": "Food & Beverages",
    "restaurante": "Restaurants",
    "restaurantes": "Restaurants",
    "hotelaria": "Hospitality",
    "turismo": "Leisure, Travel & Tourism",
    "viagens": "Leisure, Travel & Tourism",
    "recursos humanos": "Human Resources",
    "rh": "Human Resources",
    "recrutamento": "Staffing & Recruiting",
    "selecao": "Staffing & Recruiting",
    "seleção": "Staffing & Recruiting",
    "terceirizacao": "Outsourcing/Offshoring",
    "terceirização": "Outsourcing/Offshoring",
    "treinamento": "Professional Training & Coaching",
    "coaching": "Professional Training & Coaching",
    "juridico": "Legal Services",
    "jurídico": "Legal Services",
    "advocacia": "Law Practice",
    "direito": "Law Practice",
    "governo": "Government Administration",
    "ong": "Non-Profit Organization Management",
    "terceiro setor": "Non-Profit Organization Management",
    "seguranca": "Security & Investigations",
    "segurança": "Security & Investigations",
    "semiconductores": "Semiconductors",
    "semicondutores": "Semiconductors",
    "eletrica": "Electrical/Electronic Manufacturing",
    "elétrica": "Electrical/Electronic Manufacturing",
    "eletronico de consumo": "Consumer Electronics",
    "maquinario": "Machinery",
    "maquinário": "Machinery",
    "automacao industrial": "Industrial Automation",
    "automação industrial": "Industrial Automation",
    "engenharia mecanica": "Mechanical or Industrial Engineering",
    "engenharia mecânica": "Mechanical or Industrial Engineering",
    "agricultura": "Agriculture",
    "agro": "Agriculture",
    "agronegocio": "Agriculture",
    "agronegócio": "Agriculture",
    "materiais de construcao": "Building Materials",
    "materiais de construção": "Building Materials",
    "luxo": "Luxury Goods & Jewelry",
    "joias": "Luxury Goods & Jewelry",
    "jóias": "Luxury Goods & Jewelry",
    "vinho": "Wine & Spirits",
    "bebidas alcoolicas": "Wine & Spirits",
    "bebidas alcoólicas": "Wine & Spirits",
    "esporte": "Recreation & Sports",
    "esportes": "Recreation & Sports",
    "recreacao": "Recreation & Sports",
    "recreação": "Recreation & Sports",
    "eventos": "Events Services",
    "armazenamento": "Warehousing",
    "armazem": "Warehousing",
    "armazém": "Warehousing",
    "defesa": "Defense & Space",
    "espaco": "Defense & Space",
    "espaço": "Defense & Space",
    "servicos de informacao": "Information Services",
    "serviços de informação": "Information Services",
    "redes": "Computer Networking",
    "seguranca da informacao": "Computer & Network Security",
    "segurança da informação": "Computer & Network Security",
    "biotecnologia": "Biotechnology",
    "transmissao": "Broadcast Media",
    "transmissão": "Broadcast Media",
    "radio tv": "Broadcast Media",
    "utilidades": "Utilities",
    "servicos publicos": "Utilities",
    "serviços públicos": "Utilities",
    # English aliases
    "it": "Information Technology & Services",
    "tech": "Information Technology & Services",
    "technology": "Information Technology & Services",
    "information technology": "Information Technology & Services",
    "software development": "Computer Software",
    "saas": "Computer Software",
    "fintech": "Financial Services",
    "finance": "Financial Services",
    "banking": "Banking",
    "insurance": "Insurance",
    "healthcare": "Hospital & Health Care",
    "health": "Hospital & Health Care",
    "pharma": "Pharmaceuticals",
    "pharmaceuticals": "Pharmaceuticals",
    "education": "Education Management",
    "ecommerce": "Internet",
    "e-commerce": "Internet",
    "retail": "Retail",
    "real estate": "Real Estate",
    "construction": "Construction",
    "automotive": "Automotive",
    "logistics": "Logistics & Supply Chain",
    "supply chain": "Logistics & Supply Chain",
    "consulting": "Management Consulting",
    "hr": "Human Resources",
    "recruiting": "Staffing & Recruiting",
    "staffing": "Staffing & Recruiting",
    "legal": "Legal Services",
    "law": "Law Practice",
    "media": "Online Media",
    "advertising": "Marketing & Advertising",
    "marketing": "Marketing & Advertising",
    "telecom": "Telecommunications",
    "energy": "Oil & Energy",
    "oil and gas": "Oil & Energy",
    "mining": "Mining & Metals",
    "agriculture": "Agriculture",
    "food": "Food & Beverages",
    "hospitality": "Hospitality",
    "travel": "Leisure, Travel & Tourism",
    "tourism": "Leisure, Travel & Tourism",
    "entertainment": "Entertainment",
    "gaming": "Computer Games",
    "design": "Design",
    "fashion": "Apparel & Fashion",
    "security": "Security & Investigations",
    "cybersecurity": "Computer & Network Security",
    "semiconductors": "Semiconductors",
    "biotech": "Biotechnology",
    "nonprofit": "Non-Profit Organization Management",
    "non-profit": "Non-Profit Organization Management",
    "government": "Government Administration",
    "aerospace": "Aviation & Aerospace",
    "aviation": "Airlines/Aviation",
    "chemicals": "Chemicals",
    "manufacturing": "Electrical/Electronic Manufacturing",
    "machinery": "Machinery",
    "utilities": "Utilities",
    "warehousing": "Warehousing",
    "wholesale": "Wholesale",
    "publishing": "Publishing",
    "research": "Research",
    "training": "Professional Training & Coaching",
    "coaching": "Professional Training & Coaching",
    "outsourcing": "Outsourcing/Offshoring",
    "events": "Events Services",
    "sports": "Recreation & Sports",
    "luxury": "Luxury Goods & Jewelry",
    "wine": "Wine & Spirits",
    "restaurants": "Restaurants",
    "animation": "Animation",
    "photography": "Photography",
    "writing": "Writing & Editing",
    "furniture": "Furniture",
    "building materials": "Building Materials",
}


def _normalize_industry_pipelinelabs(value: str) -> str | None:
    """Converte indústria para o valor exato aceito pelo pipelinelabs.

    Retorna None se não conseguir mapear (item será descartado do input).
    """
    key = value.strip().lower()
    # 1. Lookup direto no mapa de aliases
    if key in _PIPELINELABS_INDUSTRY_MAP:
        return _PIPELINELABS_INDUSTRY_MAP[key]
    # 2. Já está no formato exato (case-insensitive)
    if key in _PIPELINELABS_INDUSTRY_LOWER:
        return _PIPELINELABS_INDUSTRY_LOWER[key]
    # 3. Substring: valor contém algum canonical
    for canonical_lower, canonical in _PIPELINELABS_INDUSTRY_LOWER.items():
        if canonical_lower in key or key in canonical_lower:
            return canonical
    # 4. Não mapeado — retorna None para omitir
    return None


def _normalize_location(value: str) -> str:
    """Converte nome de país/região para o formato aceito pelo ator (inglês, minúsculas)."""
    normalized = value.strip().lower()
    return _LOCATION_PT_TO_EN.get(normalized, normalized)


# Valores aceitos pelo ator para o campo size (tamanho de empresa).
# Mapeamento de variações comuns digitadas pelo usuário para o valor exato.
_SIZE_CANONICAL: list[str] = [
    "1-10",
    "11-20",
    "21-50",
    "51-100",
    "101-200",
    "201-500",
    "501-1000",
    "1001-2000",
    "2001-5000",
    "5001-10000",
    "10001-20000",
    "20001-50000",
    "50000+",
]

# Alias comuns que usuários digitam → valor canônico
_SIZE_ALIASES: dict[str, str] = {
    "1": "1-10",
    "1-1": "1-10",
    "0-10": "1-10",
    "2-10": "1-10",
    "1-10": "1-10",
    "11-50": "11-20",  # não existe; mapeia para o mais próximo menor
    "21-50": "21-50",  # alias próprio — não é válido; mapeia para 21-50 se correto
    "51-200": "51-100",
    "201-1000": "201-500",
    "1001-5000": "1001-2000",
    "5001+": "5001-10000",
    "10000+": "10001-20000",
    "10001+": "10001-20000",
    "+10000": "10001-20000",
    "50000+": "50000+",
    "50001+": "50000+",
}


def _normalize_company_size(value: str) -> str | None:
    """
    Normaliza um valor de tamanho de empresa para o formato aceito pelo ator.
    Retorna None se o valor não puder ser mapeado.
    """
    cleaned = value.strip()
    if cleaned in _SIZE_CANONICAL:
        return cleaned
    alias = _SIZE_ALIASES.get(cleaned)
    if alias:
        return alias
    # Tenta case-insensitive contra os canônicos
    lower = cleaned.lower()
    for canonical in _SIZE_CANONICAL:
        if lower == canonical.lower():
            return canonical
    return None


# Mapeamento de faixas do formato code_crafter → pipelinelabs
# pipelinelabs aceita: "1-10", "11-50", "51-200", "201-500", "501-1000", "1001-5000",
# "5001-10000", "10001+"
_PIPELINELABS_SIZE_MAP: dict[str, str] = {
    "1-10": "1-10",
    "11-20": "11-50",
    "21-50": "11-50",
    "51-100": "51-200",
    "101-200": "51-200",
    "201-500": "201-500",
    "501-1000": "501-1000",
    "1001-2000": "1001-5000",
    "2001-5000": "1001-5000",
    "5001-10000": "5001-10000",
    "10001-20000": "10001+",
    "20001-50000": "10001+",
    "50000+": "10001+",
}


def _normalize_sizes_pipelinelabs(sizes: list[str]) -> list[str]:
    """Converte faixas do formato code_crafter para o formato aceito pelo pipelinelabs."""
    result: list[str] = []
    seen: set[str] = set()
    for s in sizes:
        cleaned = s.strip()
        mapped = _PIPELINELABS_SIZE_MAP.get(cleaned, cleaned)
        if mapped not in seen:
            seen.add(mapped)
            result.append(mapped)
    return result


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
    # O ator pode retornar nome em campos variados dependendo da versão
    full_name = (
        item.get("full_name")
        or item.get("name")
        or item.get("contact_name")
        or item.get("person_name")
        or " ".join(filter(None, [item.get("first_name"), item.get("last_name")]))
        or " ".join(filter(None, [item.get("contact_first_name"), item.get("contact_last_name")]))
        or item.get("company_name")
        or item.get("company")
        or ""
    )
    return ApifyLeadRaw(
        name=full_name,
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


def _parse_pipelinelabs_item(item: dict[str, Any]) -> ApifyLeadRaw:
    """
    Parser para pipelinelabs/leads-finder-with-emails-apollo-lusha-zoominfo.
    Campos reais retornados: firstName, lastName, fullName, title, position,
    email, emailStatus, phone, linkedinUrl, personCity, personState, personCountry,
    companyName, companyDomain, companyIndustry (list|str), companyCity, companyState,
    companyCountry, companySize (int), companySizeRange (str).
    """
    full_name = (
        item.get("fullName")
        or item.get("full_name")
        or " ".join(filter(None, [item.get("firstName"), item.get("lastName")]))
        or item.get("companyName")
        or ""
    )
    city = item.get("personCity") or item.get("companyCity") or item.get("city")
    state = item.get("personState") or item.get("companyState") or item.get("state")
    country = item.get("personCountry") or item.get("companyCountry") or item.get("country")

    # companyIndustry pode ser lista ou string
    raw_industry = (
        item.get("companyIndustry") or item.get("company_industry") or item.get("industry")
    )
    if isinstance(raw_industry, list):
        industry: str | None = raw_industry[0] if raw_industry else None
    else:
        industry = raw_industry or None

    # companySize pode ser int (headcount) — prefere a faixa textual companySizeRange
    raw_size = item.get("companySizeRange") or item.get("companySize") or item.get("company_size")
    company_size = str(raw_size) if raw_size is not None else None

    return ApifyLeadRaw(
        name=full_name,
        first_name=item.get("firstName") or item.get("first_name"),
        last_name=item.get("lastName") or item.get("last_name"),
        job_title=(
            item.get("title")
            or item.get("position")
            or item.get("jobTitle")
            or item.get("job_title")
        ),
        company=item.get("companyName") or item.get("company_name"),
        company_domain=item.get("companyDomain") or item.get("company_domain"),
        website=item.get("companyWebsite") or item.get("company_website"),
        linkedin_url=(
            item.get("linkedinUrl")
            or item.get("linkedInUrl")
            or item.get("linkedin_url")
            or item.get("linkedin")
        ),
        city=city,
        location=_join_location(city, state, country),
        industry=industry,
        company_size=company_size,
        segment=industry,
        phone=item.get("phone"),
        email_corporate=item.get("email"),
        email_personal=item.get("personalEmail") or item.get("personal_email"),
        extra=item,
    )


def _parse_linkedin_enrichment_item(item: dict[str, Any]) -> ApifyLeadRaw:
    # HarvestAPI output: linkedinUrl, firstName, lastName, headline,
    # currentPosition[{companyName}], location.parsed.{city,country}, about
    current_positions: list[dict[str, Any]] = item.get("currentPosition") or []
    current_company = current_positions[0].get("companyName") if current_positions else None

    location_parsed: dict[str, Any] = (item.get("location") or {}).get("parsed") or {}
    city = location_parsed.get("city")
    country = location_parsed.get("country")

    return ApifyLeadRaw(
        name=f"{item.get('firstName') or ''} {item.get('lastName') or ''}".strip()
        or item.get("fullName")
        or "",
        first_name=item.get("firstName"),
        last_name=item.get("lastName"),
        job_title=item.get("headline"),
        company=current_company,
        company_domain=_extract_domain(None),
        website=None,
        linkedin_url=item.get("linkedinUrl"),
        linkedin_profile_id=item.get("publicIdentifier") or item.get("id"),
        city=city,
        location=_join_location(city, country),
        industry=None,
        company_size=None,
        segment=None,
        notes=item.get("about"),
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
