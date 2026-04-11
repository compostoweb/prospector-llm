"""
services/content/apify_linkedin_scanner.py

Garimpagem de posts do LinkedIn via Apify actor: harvestapi/linkedin-post-search
Sem cookies, sem conta LinkedIn — fonte primaria do Engagement Scanner.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime

import structlog

from integrations.apify_client import ApifyClient

logger = structlog.get_logger()

_ACTOR_ID = "harvestapi/linkedin-post-search"
_MIN_ICP_POSTS_TARGET = 5

# ── Detecção de idioma ─────────────────────────────────────────────────────────

# Stopwords PT-BR (presença forte → provável português)
_PT_STOPWORDS = frozenset(
    {
        "de",
        "do",
        "da",
        "dos",
        "das",
        "que",
        "com",
        "para",
        "por",
        "uma",
        "um",
        "como",
        "mais",
        "mas",
        "quando",
        "muito",
        "isso",
        "entre",
        "sobre",
        "também",
        "são",
        "ser",
        "sua",
        "seu",
        "tem",
        "esse",
        "essa",
        "está",
        "foi",
        "não",
        "nos",
        "nas",
        "pela",
        "pelo",
        "todo",
        "toda",
        "onde",
        "aqui",
        "quem",
        "cada",
        "bem",
        "fazer",
        "ainda",
        "você",
        "nós",
        "pode",
        "então",
    }
)

# Stopwords exclusivas do espanhol (não existem em PT-BR)
# Se o texto tem muitas dessas → espanhol, não português
_ES_ONLY_STOPWORDS = frozenset(
    {
        "los",
        "las",
        "del",
        "con",
        "una",
        "por",
        "pero",
        "esto",
        "esta",
        "estos",
        "estas",
        "también",
        "muy",
        "puede",
        "desde",
        "donde",
        "hay",
        "sin",
        "sobre",
        "tiene",
        "ser",
        "están",
        "fue",
        "han",
        "ya",
        "cuando",
        "aquí",
        "más",
        "después",
        "otro",
        "otra",
        "otros",
        "todas",
        "todos",
        "ese",
        "esa",
        "esos",
        "esas",
        "hoy",
        "él",
        "ella",
        "ellos",
        "nosotros",
        "ustedes",
        "cómo",
        "qué",
        "quién",
        "así",
        "ahora",
        "siempre",
        "nunca",
        "cada",
        "nuestro",
        "nuestra",
        "porque",
        "hacia",
        "mientras",
        "según",
        "además",
    }
)

# ── Filtro de vagas de emprego ─────────────────────────────────────────────────

_JOB_POSTING_PATTERNS = re.compile(
    r"(?i)"
    r"\b(?:contratando|estamos contratando|oportunidade de emprego"
    r"|we are hiring|we.re hiring|hiring|job opening|job opportunity"
    r"|vaga(?:s)?\s+(?:aberta(?:s)?|dispon[ií]vel(?:is)?|para|em|na|no)"
    r"|posi[cç][aã]o\s+aberta|oportunidade\s+para\s+(?:atuar|trabalhar|integrar)"
    r"|apply now|candidate|candidatar|envie seu curr[ií]culo"
    r"|vem fazer parte|junte-se|venha trabalhar|processo seletivo"
    r"|estamos buscando profissionais|requisitos da vaga"
    r"|estamos con vacantes|buscamos profesionales"
    r"|postúlate|envía tu cv|oportunidad laboral)\b"
)

_CAREER_MILESTONE_PATTERNS = re.compile(
    r"(?i)"
    r"\b(?:fui promovid[oa]|fui promovid[oa] ao cargo|promovid[oa] para"
    r"|novo passo na minha trajet[oó]ria|novo ciclo na minha carreira"
    r"|novo desafio profissional|assumo um novo desafio|assumo a cadeira"
    r"|assumo como|inicio uma nova jornada|come[çc]o uma nova jornada"
    r"|feliz em compartilhar minha promo[cç][aã]o|compartilho que fui promovid[oa]"
    r"|agrade[cç]o pela confian[çc]a|gratid[aã]o pela oportunidade"
    r"|recoloca[cç][aã]o profissional|dispon[ií]vel para novos desafios)\b"
)

# ── Cargos de vendas a excluir (não-decisores) ────────────────────────────────

_EXCLUDED_SALES_TITLES = re.compile(
    r"(?i)"
    r"\b(?:executivo de vendas|vendedor|consultor de vendas"
    r"|representante comercial|representante de vendas"
    r"|sales representative|sales executive|account executive"
    r"|inside sales|sdr|bdr|closer"
    r"|promotor de vendas|agente comercial"
    r"|analista de vendas|analista comercial"
    r"|sales consultant|business development representative)\b"
)

_SECTOR_FAMILY_TERMS: dict[str, tuple[str, ...]] = {
    "finance": (
        "financas",
        "financeiro",
        "controladoria",
        "credito",
        "tesouraria",
        "fpa",
        "fp&a",
        "planejamento financeiro",
    ),
    "operations": (
        "operacoes",
        "operacao",
        "processos",
        "logistica",
        "supply chain",
        "pcp",
        "industrial",
        "manufatura",
    ),
    "technology": (
        "tecnologia",
        "software",
        "ti",
        "infraestrutura",
        "dados",
        "seguranca",
        "cloud",
        "devops",
        "transformacao digital",
    ),
    "commercial": (
        "comercial",
        "vendas",
        "marketing",
        "growth",
        "crm",
        "receita",
        "go to market",
    ),
    "legal": (
        "juridico",
        "advocacia",
        "compliance",
        "tributario",
        "societario",
    ),
    "health": (
        "saude",
        "clinica",
        "hospital",
        "laboratorio",
        "hospitalar",
    ),
}

_GENERIC_TITLE_ALIASES: dict[str, tuple[str, ...]] = {
    "diretor": ("Director",),
    "gerente": ("Manager",),
    "head": ("Lead",),
    "ceo": ("Chief Executive Officer", "Founder & CEO", "Diretor Executivo"),
    "coo": ("Chief Operating Officer", "Diretor de Operações", "Operations Director"),
    "cto": ("Chief Technology Officer", "Diretor de Tecnologia", "Head of Technology"),
    "cfo": ("Chief Financial Officer", "Diretor Financeiro", "Finance Director"),
    "cmo": ("Chief Marketing Officer", "Diretor de Marketing", "Head of Growth"),
    "controller": ("Diretor de Controladoria", "Head of Finance"),
}

_ROLE_FAMILY_TITLE_ALIASES: dict[str, dict[str, tuple[str, ...]]] = {
    "finance": {
        "diretor": ("Diretor Financeiro", "Finance Director", "CFO", "Controller"),
        "gerente": ("Gerente Financeiro", "Finance Manager", "FP&A Manager"),
        "head": ("Head de Finanças", "Head of Finance", "Finance Director"),
        "ceo": ("CEO", "Founder & CEO"),
        "cfo": ("Finance Director", "Head of Finance", "Controller"),
    },
    "operations": {
        "diretor": ("Diretor de Operações", "Operations Director", "COO"),
        "gerente": ("Gerente de Operações", "Operations Manager", "Gerente Industrial"),
        "head": ("Head of Operations", "COO", "Operations Lead"),
        "ceo": ("CEO", "Founder & CEO"),
        "coo": ("Diretor de Operações", "Operations Director", "Head of Operations"),
    },
    "technology": {
        "diretor": ("Diretor de TI", "Diretor de Tecnologia", "CTO", "Head of Technology"),
        "gerente": ("Gerente de TI", "IT Manager", "Engineering Manager"),
        "head": ("Head of Technology", "Head de TI", "CTO"),
        "ceo": ("CEO", "Founder & CEO"),
        "cto": ("Diretor de Tecnologia", "Head of Technology", "VP de Tecnologia"),
    },
    "commercial": {
        "diretor": ("Diretor Comercial", "Diretor de Marketing", "CMO", "Head of Sales"),
        "gerente": ("Gerente Comercial", "Sales Manager", "Growth Manager"),
        "head": ("Head of Growth", "Head of Sales", "CMO"),
        "ceo": ("CEO", "Founder & CEO"),
        "cmo": ("Diretor de Marketing", "Head of Growth", "Growth Director"),
    },
    "legal": {
        "diretor": ("Diretor Jurídico", "General Counsel", "Sócio Advogado"),
        "gerente": ("Gerente Jurídico", "Legal Manager", "Compliance Manager"),
        "head": ("Head Jurídico", "General Counsel", "Head of Compliance"),
        "ceo": ("CEO", "Managing Partner"),
    },
    "health": {
        "diretor": ("Diretor de Clínica", "Administrador Hospitalar", "Diretor Hospitalar"),
        "gerente": ("Gerente Administrativo", "Gerente Hospitalar", "Clinic Manager"),
        "head": ("Head Médico", "Head Hospitalar", "Clinical Director"),
        "ceo": ("CEO", "Sócio Clínica"),
    },
}


class ApifyLinkedInScanner:
    """
    Busca posts do LinkedIn via Apify harvestapi/linkedin-post-search.

    Dois modos:
      1. search_posts_by_keywords — posts de alto engajamento do nicho
      2. get_icp_recent_posts     — posts recentes de decisores do ICP
    """

    def __init__(self) -> None:
        self._client = ApifyClient()

    async def search_posts_by_keywords(
        self,
        keywords: list[str],
        max_results: int = 20,
        min_engagement_score: int = 30,
    ) -> list[dict]:
        """
        Busca posts de alto engajamento por palavras-chave.

        Retorna lista de posts com engagement_score >= min_engagement_score,
        deduplicados por URL, limitado a max_results.
        Filtra: somente PT-BR, exclui vagas de emprego.
        """
        if not keywords:
            return []

        # Limita a 8 keywords por run para volume adequado
        # Garante queries de no maximo 85 chars (limite do LinkedIn Search)
        queries = [kw[:85] for kw in keywords[:8]]

        input_data = {
            "searchQueries": queries,
            "sortBy": "relevance",
            "maxPosts": 5,  # por keyword — 8 keywords x 5 = 40 posts brutos
            "scrapeReactions": False,
            "scrapeComments": False,
        }

        try:
            items = await self._client._run_actor(_ACTOR_ID, input_data)
        except Exception as exc:
            logger.error(
                "engagement_scanner.keyword_search_failed",
                error=str(exc),
                keywords_count=len(keywords),
            )
            return []

        posts: list[dict] = []
        seen_urls: set[str] = set()

        for item in items:
            if item.get("type") != "post":
                continue
            post = _map_apify_item(item)
            if not post.get("post_text"):
                continue
            if not _is_portuguese(post["post_text"]):
                continue
            if not _matches_reference_keywords(post["post_text"], keywords):
                continue
            if _is_job_posting(post["post_text"]):
                continue
            if _is_career_milestone_post(post["post_text"]):
                continue
            url = post.get("post_url", "")
            if url and url in seen_urls:
                continue
            if url:
                seen_urls.add(url)
            score = post["engagement_score"]
            if score < min_engagement_score:
                continue
            posts.append(post)
            if len(posts) >= max_results:
                break

        # Ordena por engagement_score desc
        posts.sort(key=lambda p: p["engagement_score"], reverse=True)
        logger.info(
            "engagement_scanner.keyword_search_done",
            keywords_count=len(keywords),
            posts_found=len(posts),
        )
        return posts[:max_results]

    async def get_icp_recent_posts(
        self,
        icp_titles: list[str],
        icp_sectors: list[str],
        topic_keywords: list[str] | None = None,
        days_back: int = 3,
        max_results: int = 15,
        minimum_results: int = _MIN_ICP_POSTS_TARGET,
    ) -> list[dict]:
        """
        Busca posts recentes de decisores do ICP cruzando titulos x setores.

        Combina até 30 pares (titulo x setor) como queries de busca.
        Filtra por autores cujo headline contenha algum dos titulos do ICP.
        """
        if not icp_titles or not icp_sectors:
            return []

        normalized_topic_keywords = _dedupe_normalized_strings(topic_keywords or [])[:4]
        expanded_titles = _expand_icp_titles(icp_titles=icp_titles, icp_sectors=icp_sectors)
        expanded_sectors = _expand_icp_sectors(icp_sectors)
        titles_lower = {_normalize_text(title) for title in expanded_titles}
        sectors_normalized = {_normalize_text(sector) for sector in expanded_sectors}
        minimum_target = min(max_results, max(1, minimum_results) * 2)

        query_batches = _build_icp_query_batches(
            icp_titles=expanded_titles,
            icp_sectors=expanded_sectors,
            topic_keywords=normalized_topic_keywords,
            posted_limit="month" if days_back >= 14 else "week",
        )

        posts: list[dict] = []
        seen_urls: set[str] = set()

        for batch in query_batches:
            if len(posts) >= minimum_target or len(posts) >= max_results:
                break

            remaining = max_results - len(posts)
            if remaining <= 0:
                break

            batch_posts = await self._collect_icp_candidates(
                queries=batch["queries"],
                titles_lower=titles_lower,
                sectors_normalized=sectors_normalized,
                posted_limit=batch["posted_limit"],
                max_results=remaining,
                seen_urls=seen_urls,
                sort_by=batch["sort_by"],
                max_posts_per_query=batch["max_posts_per_query"],
                require_sector_match=batch["require_sector_match"],
                required_keywords=batch["required_keywords"],
            )
            posts.extend(batch_posts)

        logger.info(
            "engagement_scanner.icp_search_done",
            queries_count=sum(len(batch["queries"]) for batch in query_batches),
            posts_found=len(posts),
        )
        return posts[:max_results]

    async def _collect_icp_candidates(
        self,
        *,
        queries: list[str],
        titles_lower: set[str],
        sectors_normalized: set[str],
        posted_limit: str,
        max_results: int,
        seen_urls: set[str],
        sort_by: str,
        max_posts_per_query: int,
        require_sector_match: bool,
        required_keywords: list[str],
    ) -> list[dict]:
        input_data = {
            "searchQueries": queries,
            "sortBy": sort_by,
            "maxPosts": max_posts_per_query,
            "postedLimit": posted_limit,
            "scrapeReactions": False,
            "scrapeComments": False,
        }

        try:
            items = await self._client._run_actor(_ACTOR_ID, input_data)
        except Exception as exc:
            logger.error(
                "engagement_scanner.icp_search_failed",
                error=str(exc),
                queries_count=len(queries),
            )
            return []

        posts: list[dict] = []

        for item in items:
            if item.get("type") != "post":
                continue

            post = _map_apify_item(item)
            post_text = post.get("post_text") or ""
            if not post_text:
                continue
            if not _is_portuguese(post_text):
                continue
            if _is_job_posting(post_text):
                continue
            if required_keywords and not _matches_reference_keywords(post_text, required_keywords):
                continue

            url = post.get("post_url", "")
            if url and url in seen_urls:
                continue

            author_info = post.get("author_title") or ""
            if not _headline_matches_icp(author_info, titles_lower):
                continue
            if _is_excluded_sales_title(author_info):
                continue

            sector_context = " ".join(
                value
                for value in [author_info, post.get("author_company") or "", post_text]
                if value
            )
            if (
                require_sector_match
                and sectors_normalized
                and not _matches_any_sector(sector_context, sectors_normalized)
            ):
                continue

            if url:
                seen_urls.add(url)
            posts.append(post)
            if len(posts) >= max_results:
                break

        return posts[:max_results]

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> ApifyLinkedInScanner:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    @staticmethod
    def calculate_engagement_score(likes: int, comments: int, shares: int) -> int:
        """Pontuacao de engajamento: comentarios*3 + likes + shares*2."""
        return (comments * 3) + likes + (shares * 2)


# ── Helpers ────────────────────────────────────────────────────────────────────


def _map_apify_item(item: dict) -> dict:
    """Mapeia um item do actor harvestapi/linkedin-post-search para nosso formato."""
    author = item.get("author") or {}
    engagement = item.get("engagement") or {}
    posted_at_data = item.get("postedAt") or {}

    likes = engagement.get("likes") or 0
    comments = engagement.get("comments") or 0
    shares = engagement.get("shares") or 0

    score = ApifyLinkedInScanner.calculate_engagement_score(likes, comments, shares)

    # Extrair empresa a partir do headline (autor["info"])
    # Formato comum: "Cargo at Empresa" ou "Cargo | Empresa"
    headline: str = author.get("info") or ""
    author_company = _extract_company_from_headline(headline)

    # Parse da data do post
    post_published_at: datetime | None = None
    raw_date = posted_at_data.get("date")
    if raw_date:
        try:
            post_published_at = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            pass

    return {
        "post_text": item.get("content") or "",
        "author_name": author.get("name"),
        "author_title": headline,  # headline completo como author_title
        "author_company": author_company,
        "author_linkedin_urn": author.get("id"),
        "author_profile_url": author.get("linkedinUrl"),
        "post_url": item.get("linkedinUrl"),
        "post_published_at": post_published_at,
        "likes": likes,
        "comments": comments,
        "shares": shares,
        "engagement_score": score,
    }


def _extract_company_from_headline(headline: str) -> str | None:
    """
    Extrai nome da empresa a partir do headline do LinkedIn.

    Exemplos:
      "CEO at Composto Web"            → "Composto Web"
      "Diretor de TI | ACME Corp"      → "ACME Corp"
      "Fundador da StartupXYZ"         → None
    """
    if not headline:
        return None

    # Tenta " at " (ingles)
    match = re.search(r"\bat\s+(.+)$", headline, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Tenta " | " (separador comum de headline)
    parts = headline.split("|")
    if len(parts) >= 2:
        return parts[-1].strip()

    # Tenta " na " / " em " / " da " (portugues)
    match = re.search(r"\b(?:na|em|da|do)\s+(.+)$", headline, re.IGNORECASE)
    if match:
        candidate = match.group(1).strip()
        if len(candidate) > 3:  # evita falsos positivos como "um"
            return candidate

    return None


def _headline_matches_icp(headline: str, titles_lower: set[str]) -> bool:
    """
    Verifica se o headline do autor contem algum dos titulos ICP.
    Matching parcial case-insensitive.
    """
    headline_lower = _normalize_text(headline)
    return any(title in headline_lower for title in titles_lower)


def _is_excluded_sales_title(headline: str) -> bool:
    """Retorna True se o headline indica cargo de vendas não-decisor."""
    return bool(_EXCLUDED_SALES_TITLES.search(headline))


def _is_job_posting(text: str) -> bool:
    """Detecta se o post é uma vaga de emprego / job posting."""
    return bool(_JOB_POSTING_PATTERNS.search(text))


def _is_career_milestone_post(text: str) -> bool:
    """Detecta posts sobre promoção, recolocação ou mudança de cargo."""
    return bool(_CAREER_MILESTONE_PATTERNS.search(text))


def _matches_reference_keywords(text: str, keywords: list[str]) -> bool:
    normalized_text = _normalize_text(text)
    for keyword in keywords:
        normalized_keyword = _normalize_text(keyword)
        if not normalized_keyword:
            continue
        if normalized_keyword in normalized_text:
            return True

        keyword_tokens = [
            token
            for token in re.findall(r"\b[a-z0-9]{4,}\b", normalized_keyword)
            if token not in {"para", "com", "sobre", "empresa", "empresas"}
        ]
        if not keyword_tokens:
            continue
        matched_tokens = sum(1 for token in keyword_tokens if token in normalized_text)
        if matched_tokens >= min(2, len(keyword_tokens)):
            return True

    return False


def _matches_any_sector(text: str, sectors_normalized: set[str]) -> bool:
    normalized_text = _normalize_text(text)
    return any(sector and sector in normalized_text for sector in sectors_normalized)


def _normalize_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.lower())
    ascii_only = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", ascii_only).strip()


def _dedupe_normalized_strings(values: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()

    for value in values:
        normalized = value.strip()
        key = _normalize_text(normalized)
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(normalized)

    return deduped


def _build_icp_queries(icp_titles: list[str], icp_sectors: list[str]) -> list[str]:
    queries: list[str] = []
    for title in icp_titles[:5]:
        for sector in icp_sectors[:3]:
            query = f"{title} {sector}"[:85]
            queries.append(query)
            if len(queries) >= 15:
                return queries
    return queries


def _build_icp_fallback_queries(icp_titles: list[str]) -> list[str]:
    fallback_queries: list[str] = []
    for title in icp_titles[:6]:
        normalized = title.strip()
        if not normalized:
            continue
        fallback_queries.append(normalized[:85])
    return fallback_queries


def _expand_icp_titles(icp_titles: list[str], icp_sectors: list[str]) -> list[str]:
    normalized_sectors = {_normalize_text(sector) for sector in icp_sectors}
    detected_families = _detect_sector_families(normalized_sectors)
    titles = _dedupe_normalized_strings(icp_titles)

    for title in list(titles):
        normalized_title = _normalize_text(title)
        titles.extend(_GENERIC_TITLE_ALIASES.get(normalized_title, ()))

        for family in detected_families:
            titles.extend(_ROLE_FAMILY_TITLE_ALIASES.get(family, {}).get(normalized_title, ()))

    for family in detected_families:
        family_aliases = _ROLE_FAMILY_TITLE_ALIASES.get(family, {})
        for aliases in family_aliases.values():
            titles.extend(aliases[:2])

    return _dedupe_normalized_strings(titles)


def _expand_icp_sectors(icp_sectors: list[str]) -> list[str]:
    sectors = _dedupe_normalized_strings(icp_sectors)
    normalized_sectors = {_normalize_text(sector) for sector in sectors}

    for family in _detect_sector_families(normalized_sectors):
        sectors.extend(_SECTOR_FAMILY_TERMS.get(family, ()))

    return _dedupe_normalized_strings(sectors)


def _looks_like_finance_sector(normalized_sectors: set[str]) -> bool:
    return any(
        sector in normalized_sectors
        for sector in {"financas", "financeiro", "controladoria", "credito", "tesouraria"}
    )


def _detect_sector_families(normalized_sectors: set[str]) -> set[str]:
    families: set[str] = set()

    for family, terms in _SECTOR_FAMILY_TERMS.items():
        if any(term in normalized_sectors for term in terms):
            families.add(family)

    return families


def _build_icp_query_batches(
    *,
    icp_titles: list[str],
    icp_sectors: list[str],
    topic_keywords: list[str],
    posted_limit: str,
) -> list[dict[str, object]]:
    batches: list[dict[str, object]] = []

    if topic_keywords:
        keyword_queries: list[str] = []
        for title in icp_titles[:5]:
            for keyword in topic_keywords[:3]:
                keyword_queries.append(f"{title} {keyword}"[:85])
                if len(keyword_queries) >= 12:
                    break
            if len(keyword_queries) >= 12:
                break

        if keyword_queries:
            batches.append(
                {
                    "queries": _dedupe_normalized_strings(keyword_queries),
                    "posted_limit": "month",
                    "sort_by": "relevance",
                    "max_posts_per_query": 6,
                    "require_sector_match": False,
                    "required_keywords": topic_keywords,
                }
            )

    sector_queries = _build_icp_queries(icp_titles=icp_titles, icp_sectors=icp_sectors)
    if sector_queries:
        batches.append(
            {
                "queries": sector_queries,
                "posted_limit": posted_limit,
                "sort_by": "date",
                "max_posts_per_query": 5,
                "require_sector_match": True,
                "required_keywords": [],
            }
        )
        batches.append(
            {
                "queries": sector_queries,
                "posted_limit": "month",
                "sort_by": "relevance",
                "max_posts_per_query": 6,
                "require_sector_match": True,
                "required_keywords": [],
            }
        )

    fallback_queries = _build_icp_fallback_queries(icp_titles=icp_titles)
    if fallback_queries:
        batches.append(
            {
                "queries": fallback_queries,
                "posted_limit": "month",
                "sort_by": "relevance",
                "max_posts_per_query": 8,
                "require_sector_match": False,
                "required_keywords": topic_keywords,
            }
        )

    return batches


def _is_portuguese(text: str) -> bool:
    """
    Heuristica para detectar se o texto esta em portugues e NAO em espanhol.

    1. Conta stopwords PT-BR — precisa de >= 4 hits
    2. Se tem muitas stopwords exclusivas de espanhol (>= 3), rejeita
    3. Presença de caracteres tipicamente PT-BR (ã, õ, ç) dá bonus
    """
    if not text or len(text) < 50:
        return False
    words = set(re.findall(r"\b\w+\b", text.lower()))

    # Check PT-BR stopwords
    pt_hits = len(words & _PT_STOPWORDS)
    if pt_hits < 4:
        return False

    # Check espanhol exclusivo — se muitas palavras ES-only, é espanhol
    es_hits = len(words & _ES_ONLY_STOPWORDS)
    if es_hits >= 3:
        return False

    # Bonus: caracteres tipicamente portugueses (ã, õ, ç)
    pt_chars = len(re.findall(r"[ãõç]", text.lower()))
    if pt_chars == 0 and pt_hits < 6:
        # Sem letras típicas de PT e com stopwords baixas → incerto, rejeita
        return False

    return True
