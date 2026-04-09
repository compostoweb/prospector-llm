"""
api/routes/content/notion_import.py

Endpoints para importação de posts a partir de um banco de dados Notion.

GET  /content/notion/columns  — lista as colunas disponíveis no banco Notion configurado
PUT  /content/notion/mappings — salva o mapeamento de colunas do tenant
GET  /content/notion/preview  — lista as pages do banco Notion configurado (com flag already_imported)
POST /content/notion/import   — importa as pages selecionadas como ContentPost (status=draft)
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_effective_tenant_id, get_session_flexible
from integrations.notion_client import DEFAULT_MAPPING, NotionClient, NotionMissingFieldsError
from models.content_post import ContentPost
from models.content_settings import ContentSettings
from schemas.content import (
    NotionColumnMappings,
    NotionDatabaseColumn,
    NotionImportRequest,
    NotionImportResult,
    NotionPostPreview,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/notion", tags=["Content Hub — Notion Import"])


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────


async def _get_notion_settings(
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> ContentSettings:
    """Busca as settings do tenant e valida que as credenciais Notion estão configuradas."""
    result = await db.execute(
        select(ContentSettings).where(ContentSettings.tenant_id == tenant_id)
    )
    settings_obj = result.scalar_one_or_none()

    if settings_obj is None or not settings_obj.notion_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Integração Notion não configurada. Adicione a API Key nas configurações do Content Hub.",
        )
    if not settings_obj.notion_database_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Database ID do Notion não configurado. Adicione o ID do banco nas configurações do Content Hub.",
        )

    return settings_obj


async def _get_imported_page_ids(
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> set[str]:
    """Retorna o conjunto de notion_page_id já importados por este tenant."""
    result = await db.execute(
        select(ContentPost.notion_page_id).where(
            ContentPost.tenant_id == tenant_id,
            ContentPost.notion_page_id.is_not(None),
        )
    )
    return {row[0] for row in result.fetchall() if row[0]}


def _get_mapping(settings_obj: ContentSettings) -> dict[str, str]:
    """Retorna o mapeamento de colunas do tenant ou o DEFAULT_MAPPING como fallback."""
    if settings_obj.notion_column_mappings:
        try:
            stored = json.loads(settings_obj.notion_column_mappings)
            # Mescla: campos do tenant prevalcem sobre defaults
            return {**DEFAULT_MAPPING, **{k: v for k, v in stored.items() if v}}
        except (json.JSONDecodeError, TypeError):
            pass
    return dict(DEFAULT_MAPPING)


# ─────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────


@router.get("/preview", response_model=list[NotionPostPreview])
async def preview_notion_posts(
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> list[NotionPostPreview]:
    """
    Consulta o banco de dados Notion configurado e retorna preview de todos os posts.

    Posts já importados anteriormente têm already_imported=True (checkbox desabilitado no frontend).

    Erros possíveis:
    - 400: credenciais ou database_id não configurados
    - 401: API key inválida (Notion retorna 401)
    - 422: propriedades esperadas não encontradas no banco Notion
    - 502: falha de comunicação com a API Notion
    """
    settings_obj = await _get_notion_settings(tenant_id, db)
    imported_ids = await _get_imported_page_ids(tenant_id, db)

    mapping = _get_mapping(settings_obj)

    try:
        async with NotionClient(settings_obj.notion_api_key) as client:
            pages = await client.query_database(settings_obj.notion_database_id, mapping=mapping)
    except NotionMissingFieldsError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 401:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API Key do Notion inválida. Verifique o token nas configurações.",
            ) from exc
        if exc.response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Banco de dados Notion não encontrado. Verifique o Database ID e se a integração tem acesso a ele.",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro ao comunicar com o Notion: {exc.response.status_code}",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível conectar à API do Notion. Tente novamente.",
        ) from exc

    previews: list[NotionPostPreview] = []
    for page in pages:
        # Ignora pages sem título E sem corpo — são pages em branco no banco Notion
        if not page.title.strip() and not page.body.strip():
            continue
        body_preview = (page.body[:120] + "…") if len(page.body) > 120 else page.body
        previews.append(
            NotionPostPreview(
                page_id=page.page_id,
                title=page.title,
                pillar=page.pillar,
                status_notion=page.status_notion,
                publish_date=page.publish_date,
                week_number=page.week_number,
                hashtags=page.hashtags,
                body_preview=body_preview,
                body=page.body,
                already_imported=page.page_id in imported_ids,
            )
        )

    logger.info(
        "notion.preview_fetched",
        tenant_id=str(tenant_id),
        total=len(previews),
        already_imported=sum(1 for p in previews if p.already_imported),
    )
    return previews


@router.post("/import", response_model=NotionImportResult)
async def import_notion_posts(
    body: NotionImportRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> NotionImportResult:
    """
    Importa as pages Notion selecionadas como ContentPost (status=draft).

    - Pages já importadas (notion_page_id existente) são contadas como skipped.
    - Após importação bem-sucedida, atualiza o Status da page no Notion para "Importado".
    - Falhas individuais não abortam a importação — são contadas em failed.
    """
    settings_obj = await _get_notion_settings(tenant_id, db)
    imported_ids = await _get_imported_page_ids(tenant_id, db)

    # Busca todas as pages do banco para ter os dados completos das selecionadas
    mapping = _get_mapping(settings_obj)
    status_column = mapping.get("status", "Status")

    try:
        async with NotionClient(settings_obj.notion_api_key) as client:
            all_pages = await client.query_database(settings_obj.notion_database_id, mapping=mapping)
            pages_by_id = {p.page_id: p for p in all_pages}

            imported_count = 0
            skipped_count = 0
            failed_count = 0
            created_post_ids: list[str] = []

            for page_id in body.page_ids:
                # Já importado por este tenant
                if page_id in imported_ids:
                    skipped_count += 1
                    continue

                page_data = pages_by_id.get(page_id)
                if page_data is None:
                    logger.warning(
                        "notion.import_page_not_found",
                        tenant_id=str(tenant_id),
                        page_id=page_id,
                    )
                    failed_count += 1
                    continue

                try:
                    publish_dt: datetime | None = None
                    if page_data.publish_date:
                        publish_dt = datetime.fromisoformat(page_data.publish_date + "T12:00:00").replace(tzinfo=UTC)

                    post = ContentPost(
                        tenant_id=tenant_id,
                        title=page_data.title or "Post importado do Notion",
                        body=page_data.body or "",
                        pillar=page_data.pillar or "vision",
                        status="draft",
                        publish_date=publish_dt,
                        week_number=page_data.week_number,
                        hashtags=page_data.hashtags,
                        notion_page_id=page_id,
                    )
                    db.add(post)
                    await db.flush()  # gera o ID sem commitar ainda

                    created_post_ids.append(str(post.id))
                    imported_count += 1

                    # Atualiza status no Notion (silencia erros)
                    await client.update_page_status(page_id, status_column, "Importado")

                except Exception as exc:
                    logger.error(
                        "notion.import_post_failed",
                        tenant_id=str(tenant_id),
                        page_id=page_id,
                        error=str(exc),
                    )
                    failed_count += 1

            await db.commit()

    except NotionMissingFieldsError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 401:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API Key do Notion inválida. Verifique o token nas configurações.",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro ao comunicar com o Notion: {exc.response.status_code}",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível conectar à API do Notion. Tente novamente.",
        ) from exc

    logger.info(
        "notion.import_completed",
        tenant_id=str(tenant_id),
        imported=imported_count,
        skipped=skipped_count,
        failed=failed_count,
    )

    return NotionImportResult(
        imported=imported_count,
        skipped=skipped_count,
        failed=failed_count,
        post_ids=created_post_ids,
    )


@router.get("/columns", response_model=list[NotionDatabaseColumn])
async def list_notion_columns(
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> list[NotionDatabaseColumn]:
    """
    Retorna as colunas disponíveis no banco de dados Notion configurado.

    Usado para montar a interface de mapeamento de colunas nas configurações.
    """
    settings_obj = await _get_notion_settings(tenant_id, db)

    try:
        async with NotionClient(settings_obj.notion_api_key) as client:
            columns = await client.get_database_properties(settings_obj.notion_database_id)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 401:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API Key do Notion inválida. Verifique o token nas configurações.",
            ) from exc
        if exc.response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Banco de dados Notion não encontrado. Verifique o Database ID.",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro ao comunicar com o Notion: {exc.response.status_code}",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível conectar à API do Notion. Tente novamente.",
        ) from exc

    logger.info("notion.columns_fetched", tenant_id=str(tenant_id), total=len(columns))
    return [NotionDatabaseColumn(**col) for col in columns]


@router.put("/mappings", response_model=dict)
async def save_notion_mappings(
    body: NotionColumnMappings,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> dict:
    """
    Salva o mapeamento de colunas Notion configurado pelo tenant.

    O mapeamento é persistido como JSON em content_settings.notion_column_mappings.
    Somente campos com valor não-nulo são salvos (campos opcionais podem ser omitidos).
    """
    settings_obj = await _get_notion_settings(tenant_id, db)

    # Salva apenas campos não-nulos para economizar espaço e facilitar merge com DEFAULT_MAPPING
    mappings_data = {k: v for k, v in body.model_dump().items() if v is not None}
    settings_obj.notion_column_mappings = json.dumps(mappings_data, ensure_ascii=False)
    await db.commit()

    logger.info(
        "notion.mappings_saved",
        tenant_id=str(tenant_id),
        fields_mapped=list(mappings_data.keys()),
    )
    return {"ok": True, "fields_mapped": list(mappings_data.keys())}
