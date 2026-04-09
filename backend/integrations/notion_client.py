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

from dataclasses import dataclass
from typing import Any

import httpx
import structlog

logger = structlog.get_logger()

_BASE_URL = "https://api.notion.com/v1"
_NOTION_VERSION = "2022-06-28"

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
        resp = await self._client.get(f"/databases/{database_id}")
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

        pages: list[dict[str, Any]] = []
        cursor: str | None = None

        while True:
            body_payload: dict[str, Any] = {"page_size": 100}
            if cursor:
                body_payload["start_cursor"] = cursor

            resp = await self._client.post(
                f"/databases/{database_id}/query", json=body_payload
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
