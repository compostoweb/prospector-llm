"""
services/content/apify_linkedin_scanner.py

Garimpagem de posts do LinkedIn via Apify actor: harvestapi/linkedin-post-search
Sem cookies, sem conta LinkedIn — fonte primaria do Engagement Scanner.
"""

from __future__ import annotations

import re
from datetime import datetime

import structlog

from integrations.apify_client import ApifyClient

logger = structlog.get_logger()

_ACTOR_ID = "harvestapi/linkedin-post-search"

# ── Detecção de idioma ─────────────────────────────────────────────────────────

# Stopwords PT-BR (presença forte → provável português)
_PT_STOPWORDS = frozenset({
    "de", "do", "da", "dos", "das", "que", "com", "para", "por",
    "uma", "um", "como", "mais", "mas", "quando", "muito", "isso",
    "entre", "sobre", "também", "são", "ser", "sua", "seu", "tem",
    "esse", "essa", "está", "foi", "não", "nos", "nas", "pela",
    "pelo", "todo", "toda", "onde", "aqui", "quem", "cada",
    "bem", "fazer", "ainda", "você", "nós", "pode", "então",
})

# Stopwords exclusivas do espanhol (não existem em PT-BR)
# Se o texto tem muitas dessas → espanhol, não português
_ES_ONLY_STOPWORDS = frozenset({
    "los", "las", "del", "con", "una", "por", "pero", "esto",
    "esta", "estos", "estas", "también", "muy", "puede", "desde",
    "donde", "hay", "sin", "sobre", "tiene", "ser", "están",
    "fue", "han", "ya", "cuando", "aquí", "más", "después",
    "otro", "otra", "otros", "todas", "todos", "ese", "esa",
    "esos", "esas", "hoy", "él", "ella", "ellos", "nosotros",
    "ustedes", "cómo", "qué", "quién", "así", "ahora",
    "siempre", "nunca", "cada", "nuestro", "nuestra",
    "porque", "hacia", "mientras", "según", "además",
})

# ── Filtro de vagas de emprego ─────────────────────────────────────────────────

_JOB_POSTING_PATTERNS = re.compile(
    r"(?i)"
    r"\b(?:vaga|vagas|contratando|estamos contratando|oportunidade de emprego"
    r"|we are hiring|we.re hiring|hiring|job opening|job opportunity"
    r"|apply now|candidate|candidatar|envie seu curr[ií]culo"
    r"|vem fazer parte|junte-se|venha trabalhar|processo seletivo"
    r"|estamos buscando profissionais|requisitos da vaga"
    r"|estamos con vacantes|buscamos profesionales"
    r"|postúlate|envía tu cv|oportunidad laboral)\b"
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
            if _is_job_posting(post["post_text"]):
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
        days_back: int = 3,
        max_results: int = 15,
    ) -> list[dict]:
        """
        Busca posts recentes de decisores do ICP cruzando titulos x setores.

        Combina até 30 pares (titulo x setor) como queries de busca.
        Filtra por autores cujo headline contenha algum dos titulos do ICP.
        """
        if not icp_titles or not icp_sectors:
            return []

        # Gera queries combinadas titulo+setor (max 85 chars)
        # Limita a 15 pares (titulo x setor) para volume adequado
        queries: list[str] = []
        for title in icp_titles[:5]:
            for sector in icp_sectors[:3]:
                query = f"{title} {sector}"[:85]
                queries.append(query)
                if len(queries) >= 15:
                    break
            if len(queries) >= 15:
                break

        posted_limit = "month" if days_back >= 14 else "week"

        input_data = {
            "searchQueries": queries,
            "sortBy": "date",
            "maxPosts": 4,  # por query — 15 queries x 4 = 60 posts brutos
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

        # Normaliza titulos para matching case-insensitive
        titles_lower = {t.lower() for t in icp_titles}

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
            if _is_job_posting(post["post_text"]):
                continue
            url = post.get("post_url", "")
            if url and url in seen_urls:
                continue

            # Filtra por titulo do autor (headline do LinkedIn)
            author_info = post.get("author_title") or ""
            if not _headline_matches_icp(author_info, titles_lower):
                continue
            # Exclui cargos de vendas não-decisores
            if _is_excluded_sales_title(author_info):
                continue

            if url:
                seen_urls.add(url)
            posts.append(post)
            if len(posts) >= max_results:
                break

        logger.info(
            "engagement_scanner.icp_search_done",
            queries_count=len(queries),
            posts_found=len(posts),
        )
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
            post_published_at = datetime.fromisoformat(
                raw_date.replace("Z", "+00:00")
            )
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
    headline_lower = headline.lower()
    return any(title in headline_lower for title in titles_lower)


def _is_excluded_sales_title(headline: str) -> bool:
    """Retorna True se o headline indica cargo de vendas não-decisor."""
    return bool(_EXCLUDED_SALES_TITLES.search(headline))


def _is_job_posting(text: str) -> bool:
    """Detecta se o post é uma vaga de emprego / job posting."""
    return bool(_JOB_POSTING_PATTERNS.search(text))


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
