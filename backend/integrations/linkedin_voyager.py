"""
integrations/linkedin_voyager.py

Cliente para a LinkedIn Voyager API (API interna do linkedin.com).

Voyager é a API privada usada pelo próprio site do LinkedIn para renderizar
o feed e os analytics do perfil pessoal. Ela retorna impressões, likes,
comentários e compartilhamentos de posts de PERFIS PESSOAIS — dados que a
API pública oficial (v2) não expõe para apps de terceiros.

⚠️  Aviso: Esta API não é documentada oficialmente e pode mudar sem aviso.
    É usada por ferramentas de mercado (Unipile, PhantomBuster, Taplio, etc.)
    como alternativa para perfis pessoais enquanto o LinkedIn não abre
    r_member_social para apps externos.

Fluxo:
    1. GET /voyager/api/me  →  obtém JSESSIONID (CSRF) + member_id
    2. GET /voyager/api/contentcreation/normShares  →  lista de posts do autor
    3. GET /voyager/api/analyticsModules  →  impressões + métricas por post

Autenticação:
    - Cookie li_at: token de sessão do LinkedIn (validade ~1 ano, invalidado no logout)
    - JSESSIONID: token CSRF extraído da sessão, obtido em tempo real
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog

logger = structlog.get_logger()

_BASE_URL = "https://www.linkedin.com"
_VOYAGER = "/voyager/api"
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


class VoyagerError(Exception):
    """Erro retornado pela Voyager API ou de autenticação."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Voyager API error {status_code}: {detail}")


class LinkedInVoyagerClient:
    """
    Cliente assíncrono para a LinkedIn Voyager API.

    Uso típico:
        async with LinkedInVoyagerClient(li_at) as client:
            profile = await client.get_own_profile()
            posts = await client.get_own_posts(profile["member_id"], limit=50)
            stats = await client.get_posts_analytics(post_urns)
    """

    def __init__(self, li_at: str) -> None:
        self._li_at = li_at
        self._jsessionid: str | None = None
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> LinkedInVoyagerClient:
        # Inicializa a sessão e obtém CSRF token
        await self._init_session()
        return self

    async def __aexit__(self, *args: object) -> None:
        if self._client:
            await self._client.aclose()

    # ── Inicialização de sessão ───────────────────────────────────────

    async def _init_session(self) -> None:
        """
        Obtém o JSESSIONID (CSRF token) via GET /voyager/api/me.
        O JSESSIONID é definido como cookie na response e tem o formato 'ajax:XXXX'.
        """
        # Client temporário para obter os cookies de sessão
        async with httpx.AsyncClient(
            base_url=_BASE_URL,
            timeout=15.0,
            follow_redirects=True,
        ) as tmp:
            resp = await tmp.get(
                f"{_VOYAGER}/me",
                headers=self._base_headers(),
            )

        # Se o /me retornar 403 (IP bloqueado), continua com JSESSIONID fixo —
        # os endpoints de posts/analytics podem ainda funcionar com o li_at.
        # Apenas falha no 401 (cookie definitivamente inválido).
        if resp.status_code == 401:
            raise VoyagerError(401, "Cookie li_at inválido ou expirado")

        # Extrai JSESSIONID dos cookies de resposta (pode não estar presente no 403)
        jsessionid = resp.cookies.get("JSESSIONID")
        if jsessionid:
            # Remove aspas se presente: '"ajax:12345"' → 'ajax:12345'
            self._jsessionid = jsessionid.strip('"')
        else:
            # Fallback: usa placeholder — suficiente para autenticar a maioria dos endpoints
            self._jsessionid = "ajax:0"

        self._client = httpx.AsyncClient(
            base_url=_BASE_URL,
            headers=self._auth_headers(),
            timeout=20.0,
            follow_redirects=True,
        )

    def _base_headers(self) -> dict[str, str]:
        """Headers mínimos com o cookie li_at para obter sessão."""
        return {
            "Cookie": f"li_at={self._li_at}",
            "User-Agent": _USER_AGENT,
            "X-Li-Lang": "pt_BR",
            "Accept": "application/json",
            "X-RestLi-Protocol-Version": "2.0.0",
            "Csrf-Token": "ajax:0",
            "X-Li-Track": '{"clientVersion":"1.13.19006"}',
            "X-Li-Page-Instance": "urn:li:page:d_flagship3_profile_view_base",
        }

    def _auth_headers(self) -> dict[str, str]:
        """Headers completos com CSRF para requests autenticados."""
        jsessionid = self._jsessionid or "ajax:0"
        return {
            "Cookie": f"li_at={self._li_at}; JSESSIONID={jsessionid}",
            "Csrf-Token": jsessionid,
            "User-Agent": _USER_AGENT,
            "X-Li-Lang": "pt_BR",
            "Accept": "application/json",
            "X-RestLi-Protocol-Version": "2.0.0",
            "X-Li-Track": '{"clientVersion":"1.13.19006"}',
        }

    def _assert_ready(self) -> httpx.AsyncClient:
        if not self._client:
            raise RuntimeError("LinkedInVoyagerClient não inicializado. Use 'async with'.")
        return self._client

    # ── Perfil próprio ────────────────────────────────────────────────

    async def get_own_profile(self) -> dict[str, str]:
        """
        Retorna dados do perfil autenticado.

        Returns:
            {
                "member_id": "123456789",       # ID numérico interno
                "person_urn": "urn:li:person:XYZ",  # URN base64 usado na API pública
                "public_identifier": "nome-sobrenome",  # vanity URL
                "display_name": "Nome Sobrenome",
            }
        """
        client = self._assert_ready()
        resp = await client.get(f"{_VOYAGER}/me")
        self._check(resp)

        data = resp.json()
        mini = data.get("miniProfile", {})

        # member_id: extraído do objectUrn (urn:li:member:123456789)
        object_urn: str = mini.get("objectUrn", "")
        member_id = object_urn.split(":")[-1] if object_urn else ""

        return {
            "member_id": member_id,
            "person_urn": f"urn:li:member:{member_id}" if member_id else "",
            "public_identifier": mini.get("publicIdentifier", ""),
            "display_name": (f"{mini.get('firstName', '')} {mini.get('lastName', '')}".strip()),
        }

    # ── Posts do autor ────────────────────────────────────────────────

    async def get_own_posts(
        self,
        member_id: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Lista posts publicados pelo membro via Voyager Dash API.

        Usa /identity/dash/profileUpdates com urn:li:fsd_profile:{member_id}.
        O fsd_profile ID é o mesmo base64 que o OAuth OIDC 'sub' — não exige
        o ID numérico interno (que só viria de /voyager/api/me, bloqueado em
        IPs de servidor).

        Args:
            member_id: OAuth person_id / fsd_profile ID (ex: "yPRhQvHK-4")
            limit: Número máximo de posts a retornar

        Returns:
            Lista de dicts com:
                post_urn, share_urn, text, published_at_ms,
                likes, comments, shares, lifecycle
        """
        client = self._assert_ready()

        profile_urn = f"urn:li:fsd_profile:{member_id}"
        resp = await client.get(
            f"{_VOYAGER}/identity/profileUpdatesV2",
            params={
                "q": "memberShareFeed",
                "profileUrn": profile_urn,
                "count": min(limit, 100),
                "start": 0,
                "moduleKey": "member-shares:phone",
                "includeLongTermHistory": True,
            },
        )
        self._check(resp)

        data = resp.json()
        elements: list[dict[str, Any]] = data.get("elements", [])

        logger.debug(
            "voyager.profile_updates_raw",
            element_count=len(elements),
            keys=list(data.keys()),
        )

        posts: list[dict[str, Any]] = []
        for el in elements:
            # URN do post — pode estar em locais distintos dependendo da versão do Dash
            update_meta: dict[str, Any] = el.get("updateMetadata") or {}
            urn: str = update_meta.get("urn", "") or el.get("urn", "") or el.get("entityUrn", "")
            if not urn:
                continue

            # Texto do post
            commentary_obj: dict[str, Any] = el.get("commentary") or {}
            commentary: str = commentary_obj.get("text", {}).get("text", "") or ""
            if not commentary:
                # Fallback para o formato antigo aninhado em value
                commentary = (
                    el.get("value", {})
                    .get("com.linkedin.voyager.feed.render.UpdateV2", {})
                    .get("commentary", {})
                    .get("text", {})
                    .get("text", "")
                    or ""
                )

            # Contagens sociais
            social_detail: dict[str, Any] = el.get("socialDetail") or {}
            counts: dict[str, Any] = social_detail.get("totalSocialActivityCounts") or {}
            # Fallback para formato antigo
            if not counts:
                counts = (
                    el.get("value", {})
                    .get("com.linkedin.voyager.feed.render.UpdateV2", {})
                    .get("socialDetail", {})
                    .get("totalSocialActivityCounts", {})
                ) or {}

            num_likes = int(counts.get("numLikes", 0) or 0)
            num_comments = int(counts.get("numComments", 0) or 0)
            num_shares = int(counts.get("numShares", 0) or 0)

            published_obj: dict[str, Any] = el.get("published") or el.get("created") or {}
            published_at_ms: int = int(published_obj.get("time", 0) or 0)

            posts.append(
                {
                    "post_urn": urn,
                    "share_urn": "",
                    "text": commentary,
                    "published_at_ms": published_at_ms,
                    "likes": num_likes,
                    "comments": num_comments,
                    "shares": num_shares,
                    "lifecycle": el.get("lifecycleState", "PUBLISHED"),
                }
            )

        return posts

    # ── Analytics de impressões ───────────────────────────────────────

    async def get_posts_analytics(
        self,
        post_urns: list[str],
    ) -> dict[str, dict[str, int | float]]:
        """
        Retorna impressões e engajamento para cada post informado.

        Chama o endpoint analyticsModules com q=memberShareAnalytics
        para cada URN (batching automático de até 20 por req).

        Args:
            post_urns: Lista de URNs no formato 'urn:li:ugcPost:...' ou 'urn:li:share:...'

        Returns:
            Dict mapeando URN → {impressions, likes, comments, shares, engagement_rate}
        """
        if not post_urns:
            return {}

        client = self._assert_ready()
        results: dict[str, dict[str, int | float]] = {}

        # Voyager aceita no máximo ~10 por chamada neste endpoint
        batch_size = 10
        for i in range(0, len(post_urns), batch_size):
            batch = post_urns[i : i + batch_size]
            batch_results = await self._fetch_analytics_batch(client, batch)
            results.update(batch_results)

        return results

    async def _fetch_analytics_batch(
        self,
        client: httpx.AsyncClient,
        post_urns: list[str],
    ) -> dict[str, dict[str, int | float]]:
        """
        Busca analytics para um batch de URNs via analyticsModules.
        """
        params: dict[str, Any] = {
            "q": "memberShareAnalytics",
        }
        for idx, urn in enumerate(post_urns):
            # NÃO pré-encodar: httpx já faz URL-encoding dos params uma vez
            params[f"shareIds[{idx}]"] = urn

        resp = await client.get(f"{_VOYAGER}/analyticsModules", params=params)

        if resp.status_code == 404:
            # Endpoint não disponível para esta conta — sem analytics
            logger.warning("voyager.analytics_not_available", urns=post_urns[:3])
            return {}

        self._check(resp)
        data = resp.json()

        batch_results: dict[str, dict[str, int | float]] = {}
        elements = data.get("elements", [])

        for el in elements:
            urn = str(el.get("shareId") or el.get("entityUrn") or "")
            if not urn:
                continue

            stats = el.get("totalShareStatistics", el.get("stats", {}))
            impressions = int(stats.get("impressionCount", stats.get("views", 0)))
            likes = int(stats.get("likeCount", stats.get("numLikes", 0)))
            comments = int(stats.get("commentCount", stats.get("numComments", 0)))
            shares = int(stats.get("shareCount", stats.get("numShares", 0)))
            engagement = float(stats.get("engagement", stats.get("engagementRate", 0.0)))

            batch_results[urn] = {
                "impressions": impressions,
                "likes": likes,
                "comments": comments,
                "shares": shares,
                "engagement_rate": round(engagement * 100, 2),  # converte 0.05 → 5.00%
            }

        return batch_results

    # ── Helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _check(resp: httpx.Response) -> None:
        if resp.status_code in (401, 403):
            raise VoyagerError(resp.status_code, "Cookie li_at inválido ou expirado")
        if resp.status_code == 429:
            raise VoyagerError(resp.status_code, "Rate limit atingido — tente novamente mais tarde")
        if resp.status_code >= 400:
            body = resp.text[:200] if resp.text else ""
            raise VoyagerError(
                resp.status_code,
                f"Voyager API retornou {resp.status_code}: {body}",
            )


# ── Função standalone para validar li_at ─────────────────────────────


async def validate_li_at(li_at: str) -> tuple[bool, str | None]:
    """
    Valida se o cookie li_at ainda é válido.
    Retorna (True, None) se válido ou (False, mensagem_de_erro).
    Reutiliza a mesma lógica de ping_native_account que já funciona.
    """
    headers = {
        "Cookie": f"li_at={li_at}",
        "User-Agent": _USER_AGENT,
        "X-Li-Lang": "pt_BR",
        "X-RestLi-Protocol-Version": "2.0.0",
        "Csrf-Token": "ajax:0",
        "X-Li-Track": '{"clientVersion":"1.13.19006"}',
        "X-Li-Page-Instance": "urn:li:page:d_flagship3_profile_view_base",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{_BASE_URL}{_VOYAGER}/me",
                headers=headers,
            )
        if resp.status_code == 200:
            return True, None
        if resp.status_code in (401, 403):
            return False, "Cookie li_at inválido ou expirado"
        return False, f"Status inesperado: {resp.status_code}"
    except Exception as exc:
        return False, str(exc)
