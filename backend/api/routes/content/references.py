"""
api/routes/content/references.py

Posts de referencia de alta performance para uso como few-shot no LLM.

GET    /content/references      — listar
POST   /content/references      — adicionar
DELETE /content/references/{id} — remover
"""

from __future__ import annotations

import json
import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_effective_tenant_id, get_llm_registry, get_session_flexible
from integrations.llm.registry import LLMRegistry
from models.content_reference import ContentReference
from schemas.content import ContentReferenceCreate, ContentReferenceResponse

logger = structlog.get_logger()

router = APIRouter(prefix="/references", tags=["Content Hub — References"])


@router.get("", response_model=list[ContentReferenceResponse])
async def list_references(
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> list[ContentReferenceResponse]:
    stmt = (
        select(ContentReference)
        .where(ContentReference.tenant_id == tenant_id)
        .order_by(
            ContentReference.engagement_score.desc().nulls_last(),
            ContentReference.created_at.desc(),
        )
    )
    result = await db.execute(stmt)
    return [ContentReferenceResponse.model_validate(r) for r in result.scalars().all()]


@router.post("", response_model=ContentReferenceResponse, status_code=status.HTTP_201_CREATED)
async def create_reference(
    body: ContentReferenceCreate,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ContentReferenceResponse:
    ref = ContentReference(
        tenant_id=tenant_id,
        body=body.body,
        author_name=body.author_name,
        author_title=body.author_title,
        hook_type=body.hook_type,
        pillar=body.pillar,
        engagement_score=body.engagement_score,
        source_url=body.source_url,
        notes=body.notes,
    )
    db.add(ref)
    await db.commit()
    await db.refresh(ref)
    logger.info("content.reference_created", reference_id=str(ref.id), tenant_id=str(tenant_id))
    return ContentReferenceResponse.model_validate(ref)


# ── Analyze URL with AI ────────────────────────────────────────────────────────


class AnalyzeUrlRequest(BaseModel):
    url: str


class AnalyzeUrlResponse(BaseModel):
    body: str
    author_name: str | None = None
    author_title: str | None = None
    hook_type: str | None = None
    pillar: str | None = None
    engagement_score: int | None = None
    notes: str | None = None


@router.post(
    "/analyze-url", response_model=AnalyzeUrlResponse, summary="Analisa URL de post com IA"
)
async def analyze_reference_url(
    body: AnalyzeUrlRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    registry: LLMRegistry = Depends(get_llm_registry),
) -> AnalyzeUrlResponse:
    from integrations.context_fetcher import ContextFetcher
    from integrations.llm.base import LLMMessage

    content = await ContextFetcher().fetch_from_website(body.url)
    if not content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Não foi possível extrair conteúdo da URL",
        )

    messages: list[LLMMessage] = [
        LLMMessage(
            role="system",
            content="Você é um analista de conteúdo especializado em posts do LinkedIn.",
        ),
        LLMMessage(
            role="user",
            content=(
                "Analise o conteúdo abaixo e retorne um JSON com os seguintes campos:\n"
                "- body: texto completo do post (string)\n"
                "- author_name: nome do autor do post (string ou null)\n"
                "- author_title: cargo ou área de atuação do autor (string ou null)\n"
                "- hook_type: tipo de gancho — um de: loop_open, contrarian, identification, "
                "shortcut, benefit, data (string ou null)\n"
                "- pillar: pilar de conteúdo — um de: authority, case, vision (string ou null)\n"
                "- engagement_score: estimativa de engajamento de 0 a 100 (int ou null)\n"
                "- notes: 1-2 frases sobre estrutura e técnicas usadas (string ou null)\n\n"
                f"Conteúdo extraído da URL:\n{content[:6000]}"
            ),
        ),
    ]

    resp = await registry.complete(
        messages=messages,
        provider="openai",
        model="gpt-4o-mini",
        temperature=0.3,
        max_tokens=800,
        json_mode=True,
    )

    try:
        data = json.loads(resp.content)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.error("content.analyze_url_parse_error", error=str(exc), url=body.url)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Erro ao interpretar resposta da IA",
        ) from exc

    logger.info("content.analyze_url_done", url=body.url, tenant_id=str(tenant_id))
    return AnalyzeUrlResponse(**{k: data.get(k) for k in AnalyzeUrlResponse.model_fields})


@router.delete("/{reference_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_reference(
    reference_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> None:
    result = await db.execute(
        select(ContentReference).where(
            ContentReference.id == reference_id,
            ContentReference.tenant_id == tenant_id,
        )
    )
    ref = result.scalar_one_or_none()
    if ref is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Referencia nao encontrada"
        )
    await db.delete(ref)
    await db.commit()
    logger.info(
        "content.reference_deleted", reference_id=str(reference_id), tenant_id=str(tenant_id)
    )
