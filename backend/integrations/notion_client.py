"""
integrations/notion_client.py

Cliente HTTP assíncrono para a Notion REST API.

Responsabilidades:
  - Listar as colunas disponíveis no banco de dados Notion
  - Consultar pages e mapear para campos ContentPost via mapeamento configurável pelo tenant
  - Atualizar o status de uma page no Notion após importação

Base URL: https://api.notion.com/v1
Auth:     Authorization: Bearer {notion_api_key}
Versão:   Notion-Version: 2022-06-28

O mapeamento de colunas é configurado pelo tenant em content_settings.notion_column_mappings.
Chaves do mapeamento (title e body obrigatórios):
  title         -> coluna Notion tipo title
  body          -> coluna Notion tipo rich_text
  pillar        -> coluna Notion tipo select (Visao/Autoridade/Case)
  status        -> coluna Notion tipo select (Rascunho -> draft)
  publish_date  -> coluna Notion tipo date
  week_number   -> coluna Notion tipo number
  hashtags      -> coluna Notion tipo rich_text
"""

from __future__ import annotations

import asyncio
import html as html_mod
from dataclasses import dataclass, replace as dc_replace
from typing import Any

import httpx
import structlog

logger = structlog.get_logger()

_BASE_URL = "https://api.notion.com/v1"
_NOTION_VERSION = "2022-06-28"


def _rt_to_md(rt: dict[str, Any]) -> str:
    """Converte um segmento rich_text Notion para Markdown."""
    text = rt.get("plain_text", "")
    if not text:
        return ""
    ann = rt.get("annotations", {})
    href = rt.get("href")
    if ann.get("code"):
        result = f"`{text}`"
    else:
        result = text
        if ann.get("bold"):
            result = f"**{result}**"
        if ann.get("italic"):
            result = f"*{result}*"
        if ann.get("strikethrough"):
            result = f"~~{result}~~"
    if href:
        result = f"[{result}]({href})"
    return result


def _rt_to_html(rt: dict[str, Any]) -> str:
    """Converte um segmento rich_text Notion para HTML."""
    text = rt.get("plain_text", "")
    if not text:
        return ""
    ann = rt.get("annotations", {})
    href = rt.get("href")
    escaped = html_mod.escape(text)
    if ann.get("code"):
        escaped = f"<code>{escaped}</code>"
    else:
        if ann.get("bold"):
            escaped = f"<strong>{escaped}</strong>"
        if ann.get("italic"):
            escaped = f"<em>{escaped}</em>"
        if ann.get("strikethrough"):
            escaped = f"<s>{escaped}</s>"
        if ann.get("underline"):
            escaped = f"<u>{escaped}</u>"
    if href:
        safe_href = html_mod.escape(href)
        escaped = f'<a href="{safe_href}">{escaped}</a>'
    return escaped


def _rts_to_md(rich_texts: list[dict[str, Any]]) -> str:
    return "".join(_rt_to_md(rt) for rt in rich_texts)


def _rts_to_html(rich_texts: list[dict[str, Any]]) -> str:
    return "".join(_rt_to_html(rt) for rt in rich_texts)


def _blocks_to_markdown(blocks: list[dict[str, Any]]) -> str:
    """Converte blocos Notion em Markdown com formatação (negrito, links, etc.)."""
    lines: list[str] = []
    numbered_counter = 0
    for block in blocks:
        btype = block.get("type", "")
        content = block.get(btype, {})
        if not isinstance(content, dict):
            continue
        rts = content.get("rich_text", [])
        text = _rts_to_md(rts)
        if btype == "heading_1":
            numbered_counter = 0
            lines.append(f"# {text}")
        elif btype == "heading_2":
            numbered_counter = 0
            lines.append(f"## {text}")
        elif btype == "heading_3":
            numbered_counter = 0
            lines.append(f"### {text}")
        elif btype == "paragraph":
            numbered_counter = 0
            lines.append(text)  # can be empty → blank line
        elif btype == "bulleted_list_item":
            numbered_counter = 0
            lines.append(f"- {text}")
        elif btype == "numbered_list_item":
            numbered_counter += 1
            lines.append(f"{numbered_counter}. {text}")
        elif btype == "divider":
            numbered_counter = 0
            lines.append("---")
        elif btype in ("callout", "quote"):
            numbered_counter = 0
            icon = ""
            if btype == "callout":
                icon_data = content.get("icon", {})
                if icon_data.get("type") == "emoji":
                    icon = icon_data.get("emoji", "") + " "
            lines.append(f"> {icon}{text}")
        elif btype == "code":
            numbered_counter = 0
            lang = content.get("language", "")
            plain = "".join(rt.get("plain_text", "") for rt in rts)
            lines.append(f"```{lang}\n{plain}\n```")
        else:
            numbered_counter = 0
            if text.strip():
                lines.append(text)
    return "\n\n".join(lines)


def _blocks_to_html(blocks: list[dict[str, Any]]) -> str:
    """Converte blocos Notion em HTML com formatação completa (links, negrito, etc.)."""
    parts: list[str] = []
    in_ul = False
    in_ol = False
    for block in blocks:
        btype = block.get("type", "")
        content = block.get(btype, {})
        if not isinstance(content, dict):
            continue
        rts = content.get("rich_text", [])
        html_content = _rts_to_html(rts)
        # Fechar listas abertas quando o tipo muda
        if btype != "bulleted_list_item" and in_ul:
            parts.append("</ul>")
            in_ul = False
        if btype != "numbered_list_item" and in_ol:
            parts.append("</ol>")
            in_ol = False
        if btype == "heading_1":
            parts.append(f"<h1>{html_content}</h1>")
        elif btype == "heading_2":
            parts.append(f"<h2>{html_content}</h2>")
        elif btype == "heading_3":
            parts.append(f"<h3>{html_content}</h3>")
        elif btype == "paragraph":
            if html_content.strip():
                parts.append(f"<p>{html_content}</p>")
        elif btype == "bulleted_list_item":
            if not in_ul:
                parts.append("<ul>")
                in_ul = True
            parts.append(f"  <li>{html_content}</li>")
        elif btype == "numbered_list_item":
            if not in_ol:
                parts.append("<ol>")
                in_ol = True
            parts.append(f"  <li>{html_content}</li>")
        elif btype == "divider":
            parts.append("<hr/>")
        elif btype in ("callout", "quote"):
            icon = ""
            if btype == "callout":
                icon_data = content.get("icon", {})
                if icon_data.get("type") == "emoji":
                    icon = html_mod.escape(icon_data.get("emoji", "")) + " "
            parts.append(f"<blockquote>{icon}{html_content}</blockquote>")
        elif btype == "code":
            lang = content.get("language", "")
            plain = html_mod.escape("".join(rt.get("plain_text", "") for rt in rts))
            parts.append(f'<pre><code class="language-{lang}">{plain}</code></pre>')
        else:
            if html_content.strip():
                parts.append(f"<p>{html_content}</p>")
    if in_ul:
        parts.append("</ul>")
    if in_ol:
        parts.append("</ol>")
    return "\n".join(parts)


# Mantido para compatibilidade — usado por fetch_page_blocks_as_text (posts)
def _blocks_to_text(blocks: list[dict[str, Any]]) -> str:
    """Compatibilidade: retorna Markdown usando o parser completo."""
    return _blocks_to_markdown(blocks)

# Mapeamento padrao -- fallback se o tenant nao configurou mapeamento personalizado.
DEFAULT_MAPPING: dict[str, str] = {
    "title": "Titulo do post",
    "body": "Texto do post",
    "pillar": "Pilar",
    "status": "Status",
    "publish_date": "Data de publicação",
    "week_number": "# Semana",
    "hashtags": "Hashtags",
}

_PILLAR_MAP: dict[str, str] = {
    "Visao": "vision",
    "Visão": "vision",
    "Autoridade": "authority",
    "Case": "case",
}

_STATUS_MAP: dict[str, str] = {
    "Rascunho": "draft",
    "Aprovado": "approved",
}


class NotionMissingFieldsError(Exception):
    """Levantada quando title ou body nao estao configurados no mapeamento do tenant."""

    def __init__(self, missing: list[str]) -> None:
        self.missing = missing
        names = ", ".join(f"'{m}'" for m in missing)
        super().__init__(
            f"Mapeamento de colunas incompleto: campos obrigatorios {names} nao foram vinculados. "
            "Configure o mapeamento de colunas nas Configuracoes do Content Hub."
        )


@dataclass
class NotionPageData:
    """Dados extraidos de uma page Notion prontos para criar um ContentPost."""

    page_id: str
    title: str
    body: str
    pillar: str
    status_notion: str
    publish_date: str | None = None
    week_number: int | None = None
    hashtags: str | None = None


def _clean_db_id(database_id: str) -> str:
    """Remove query string e hashes de view que o Notion inclui nas URLs copiadas.

    Exemplo: '65ef0c50361b4e2b824a7fea2840fef1?v=cb98913c8de24cca8b471e7e830e1f98'
             -> '65ef0c50361b4e2b824a7fea2840fef1'
    """
    return database_id.split("?")[0].split("#")[0].strip()


class NotionClient:
    """
    Cliente para a Notion REST API.

    Deve ser instanciado com a API key do tenant (Internal Integration token).
    Nao e um singleton global -- cada request cria/reutiliza conforme necessario.
    """

    def __init__(self, api_key: str) -> None:
        self._client = httpx.AsyncClient(
            base_url=_BASE_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Notion-Version": _NOTION_VERSION,
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "NotionClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.aclose()

    async def get_database_properties(self, database_id: str) -> list[dict[str, str]]:
        """
        Retorna as colunas disponiveis no banco de dados Notion.
        Resultado: lista de {"name": str, "type": str} ordenada pelo nome.
        """
        db_id = _clean_db_id(database_id)
        resp = await self._client.get(f"/databases/{db_id}")
        resp.raise_for_status()
        data = resp.json()
        props: dict[str, Any] = data.get("properties", {})
        return [
            {"name": name, "type": prop.get("type", "unknown")}
            for name, prop in sorted(props.items(), key=lambda x: x[0].lower())
        ]

    async def query_database(
        self,
        database_id: str,
        mapping: dict[str, str] | None = None,
    ) -> list[NotionPageData]:
        """
        Consulta todas as pages de um banco de dados Notion com paginacao automatica.

        Args:
            database_id: UUID do banco de dados Notion.
            mapping: dicionario {campo_interno: nome_coluna_notion}.
                     Mescla com DEFAULT_MAPPING (mapping prevalece sobre defaults).

        Levanta NotionMissingFieldsError se title ou body nao estiverem mapeados.
        """
        resolved: dict[str, str] = {**DEFAULT_MAPPING, **(mapping or {})}

        missing = [f for f in ("title", "body") if not resolved.get(f)]
        if missing:
            raise NotionMissingFieldsError(missing)

        db_id = _clean_db_id(database_id)
        pages: list[dict[str, Any]] = []
        cursor: str | None = None

        while True:
            body_payload: dict[str, Any] = {"page_size": 100}
            if cursor:
                body_payload["start_cursor"] = cursor

            resp = await self._client.post(
                f"/databases/{db_id}/query", json=body_payload
            )
            resp.raise_for_status()
            data = resp.json()

            pages.extend(data.get("results", []))
            if not data.get("has_more"):
                break
            cursor = data.get("next_cursor")

        logger.info("notion.database_queried", database_id=database_id, total_pages=len(pages))
        return [self._extract_fields(p, resolved) for p in pages]

    async def update_page_status(
        self,
        page_id: str,
        status_column: str,
        status_option: str = "Importado",
    ) -> None:
        """
        Atualiza a coluna de status de uma page Notion.

        Args:
            page_id: ID da page Notion.
            status_column: nome real da coluna de status (do mapeamento do tenant).
            status_option: valor a definir (default: "Importado").
        """
        if not status_column:
            return
        try:
            resp = await self._client.patch(
                f"/pages/{page_id}",
                json={
                    "properties": {
                        status_column: {
                            "select": {"name": status_option},
                        }
                    }
                },
            )
            resp.raise_for_status()
            logger.info("notion.page_status_updated", page_id=page_id, status=status_option)
        except Exception as exc:
            logger.warning("notion.page_status_update_failed", page_id=page_id, error=str(exc))

    async def fetch_page_blocks_as_text(self, page_id: str) -> str:
        """Busca o conteudo da page como Markdown. Retorna string vazia em caso de erro."""
        md, _ = await self._fetch_page_blocks_raw(page_id)
        return md

    async def _fetch_page_blocks_raw(self, page_id: str) -> tuple[str, str]:
        """Retorna (markdown, html) dos blocos da page. Tupla vazia em caso de erro."""
        try:
            resp = await self._client.get(
                f"/blocks/{page_id}/children", params={"page_size": 100}
            )
            resp.raise_for_status()
            blocks: list[dict[str, Any]] = resp.json().get("results", [])
            return _blocks_to_markdown(blocks), _blocks_to_html(blocks)
        except Exception as exc:
            logger.warning("notion.blocks_fetch_failed", page_id=page_id, error=str(exc))
            return "", ""

    def _extract_fields(self, page: dict[str, Any], mapping: dict[str, str]) -> NotionPageData:
        """Mapeia propriedades de uma page Notion para NotionPageData usando o mapping do tenant."""
        props: dict[str, Any] = page.get("properties", {})
        page_id: str = page["id"]

        title_col = mapping.get("title", "")
        title = _get_title(props.get(title_col, {})) if title_col else ""
        # Fallback: no Notion, toda database tem exatamente uma propriedade tipo "title".
        # Se o nome configurado não bater, busca automaticamente pela propriedade de tipo title.
        if not title:
            title = _find_title_fallback(props)

        body_col = mapping.get("body", "")
        body = _get_rich_text(props.get(body_col, {})) if body_col else ""

        pillar_col = mapping.get("pillar", "")
        pillar_raw = _get_select(props.get(pillar_col, {})) if pillar_col else None
        pillar = _PILLAR_MAP.get(pillar_raw or "", "vision")

        status_col = mapping.get("status", "")
        status_raw = _get_select(props.get(status_col, {})) if status_col else None
        status_notion = _STATUS_MAP.get(status_raw or "Rascunho", "draft")

        publish_date: str | None = None
        date_col = mapping.get("publish_date", "")
        if date_col and date_col in props:
            date_val = props[date_col].get("date")
            if date_val:
                publish_date = date_val.get("start")

        week_number: int | None = None
        week_col = mapping.get("week_number", "")
        if week_col and week_col in props:
            week_number = props[week_col].get("number")

        hashtags: str | None = None
        hashtags_col = mapping.get("hashtags", "")
        if hashtags_col and hashtags_col in props:
            hashtags = _get_rich_text(props[hashtags_col]) or None

        return NotionPageData(
            page_id=page_id,
            title=title,
            body=body,
            pillar=pillar,
            status_notion=status_notion,
            publish_date=publish_date,
            week_number=week_number,
            hashtags=hashtags,
        )


def _get_title(prop: dict[str, Any]) -> str:
    parts: list[dict[str, Any]] = prop.get("title", [])
    return "".join(t.get("plain_text", "") for t in parts).strip()


def _find_title_fallback(props: dict[str, Any]) -> str:
    """Busca a primeira propriedade de tipo 'title' no dict de props da page.

    No Notion, toda database tem exatamente uma propriedade tipo title.
    Usada como fallback quando o nome mapeado não corresponde a nenhuma coluna.
    """
    for prop in props.values():
        if isinstance(prop, dict) and prop.get("type") == "title":
            return _get_title(prop)
    return ""


def _get_rich_text(prop: dict[str, Any]) -> str:
    parts: list[dict[str, Any]] = prop.get("rich_text", [])
    return "".join(t.get("plain_text", "") for t in parts).strip()


def _get_select(prop: dict[str, Any]) -> str | None:
    sel = prop.get("select")
    if sel is None:
        return None
    return sel.get("name")


# ─────────────────────────────────────────────────────────────────────
# Newsletter support
# ─────────────────────────────────────────────────────────────────────

# Mapeamento padrão para o banco de dados de newsletters.
# O usuário pode configurar nomes diferentes em content_settings.
DEFAULT_NEWSLETTER_MAPPING: dict[str, str] = {
    "title": "Título",
    "subtitle": "Subtítulo",
    "edition_number": "Edição #",
    "status": "Status",
    "scheduled_for": "Data de publicação",
    "body": "Conteúdo",
}


@dataclass
class NotionNewsletterPageData:
    """Dados extraídos de uma page Notion prontos para criar um ContentNewsletter."""

    page_id: str
    title: str
    subtitle: str | None
    edition_number: int | None
    status_notion: str | None
    scheduled_for: str | None
    body: str
    body_html: str = ""


_NL_STATUS_MAP: dict[str, str] = {
    "Rascunho": "draft",
    "Draft": "draft",
    "Aprovado": "approved",
    "Aprovada": "approved",
    "Agendado": "scheduled",
    "Agendada": "scheduled",
    "Publicado": "published",
    "Publicada": "published",
}


class NotionNewsletterClient(NotionClient):
    """
    Extensão do NotionClient com suporte específico para newsletters.
    Reutiliza autenticação e paginação do cliente base.
    """

    async def __aenter__(self) -> "NotionNewsletterClient":
        return self

    async def query_newsletter_database(
        self,
        database_id: str,
        mapping: dict[str, str] | None = None,
    ) -> list[NotionNewsletterPageData]:
        """
        Consulta todas as pages de um banco de dados Notion de newsletters.

        O campo 'title' é obrigatório no mapeamento.
        """
        resolved: dict[str, str] = {**DEFAULT_NEWSLETTER_MAPPING, **(mapping or {})}

        missing = [f for f in ("title",) if not resolved.get(f)]
        if missing:
            raise NotionMissingFieldsError(missing)

        db_id = _clean_db_id(database_id)
        pages: list[dict[str, Any]] = []
        cursor: str | None = None

        while True:
            body_payload: dict[str, Any] = {"page_size": 100}
            if cursor:
                body_payload["start_cursor"] = cursor

            resp = await self._client.post(
                f"/databases/{db_id}/query", json=body_payload
            )
            resp.raise_for_status()
            data = resp.json()

            pages.extend(data.get("results", []))
            if not data.get("has_more"):
                break
            cursor = data.get("next_cursor")

        logger.info(
            "notion.newsletter_database_queried",
            database_id=database_id,
            total_pages=len(pages),
        )
        extracted = [self._extract_newsletter_fields(p, resolved) for p in pages]

        # Corpo da newsletter fica nos blocos da page, nao nas propriedades.
        # Busca markdown + html em paralelo para nao serializar N requests.
        raw_results = await asyncio.gather(
            *[self._fetch_page_blocks_raw(p.page_id) for p in extracted],
            return_exceptions=True,
        )
        result: list[NotionNewsletterPageData] = []
        for page_data, raw in zip(extracted, raw_results):
            if isinstance(raw, tuple):
                md, html = raw
            else:
                md, html = "", ""
            result.append(dc_replace(page_data, body=md, body_html=html))
        return result

    def _extract_newsletter_fields(
        self,
        page: dict[str, Any],
        mapping: dict[str, str],
    ) -> NotionNewsletterPageData:
        """Mapeia propriedades de uma page Notion para NotionNewsletterPageData."""
        props: dict[str, Any] = page.get("properties", {})
        page_id: str = page["id"]

        # Título
        title_col = mapping.get("title", "")
        title = _get_title(props.get(title_col, {})) if title_col else ""
        if not title:
            title = _find_title_fallback(props)

        # Subtítulo
        subtitle_col = mapping.get("subtitle", "")
        subtitle = _get_rich_text(props.get(subtitle_col, {})) if subtitle_col else None
        subtitle = subtitle or None

        # Edição #
        edition_number: int | None = None
        edition_col = mapping.get("edition_number", "")
        if edition_col and edition_col in props:
            edition_number = props[edition_col].get("number")

        # Status
        status_col = mapping.get("status", "")
        status_raw = _get_select(props.get(status_col, {})) if status_col else None
        status_notion = _NL_STATUS_MAP.get(status_raw or "", "draft") if status_raw else None

        # Data de publicação / agendamento
        scheduled_for: str | None = None
        date_col = mapping.get("scheduled_for", "")
        if date_col and date_col in props:
            date_val = props[date_col].get("date")
            if date_val:
                scheduled_for = date_val.get("start")

        # Corpo (conteúdo)
        body_col = mapping.get("body", "")
        body = _get_rich_text(props.get(body_col, {})) if body_col else ""

        return NotionNewsletterPageData(
            page_id=page_id,
            title=title,
            subtitle=subtitle,
            edition_number=edition_number,
            status_notion=status_notion,
            scheduled_for=scheduled_for,
            body=body,
        )

