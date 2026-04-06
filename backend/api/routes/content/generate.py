"""
api/routes/content/generate.py

Endpoints de geração de conteúdo com IA:
  POST /content/generate               — gera N variações de post
  POST /content/generate/improve       — melhora um post existente
  POST /content/generate/suggest-themes — sugere temas com base nos leads
  POST /content/generate/vary-theme    — gera variação de um tema com IA
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import (
    get_effective_tenant_id,
    get_llm_registry,
    get_session_flexible,
)
from core.config import settings
from integrations.llm import LLMRegistry
from models.content_post import ContentPost
from models.content_reference import ContentReference
from models.content_settings import ContentSettings
from models.content_theme import ContentTheme
from models.enums import LeadStatus
from models.lead import Lead
from schemas.content import (
    ContentThemeResponse,
    GeneratePostRequest,
    GeneratePostResponse,
    GeneratePostVariation,
    ImprovePostRequest,
    ImprovePostResponse,
    ThemeSuggestion,
    VaryThemeRequest,
    VaryThemeResponse,
)
from services.content.llm_generator import (
    GeneratedVariation,
    ReferenceExample,
    generate_post,
    improve_post,
)
from services.content.rules import count_characters, validate_post

logger = structlog.get_logger()

router = APIRouter(prefix="/generate", tags=["Content Hub — IA"])


# ── Helpers ───────────────────────────────────────────────────────────


async def _get_settings_or_defaults(
    db: AsyncSession,
    tenant_id: uuid.UUID,
) -> tuple[str, str]:
    """
    Retorna (author_name, author_voice) do ContentSettings do tenant.
    Usa fallback genérico se ainda não configurado.
    """
    result = await db.execute(select(ContentSettings).where(ContentSettings.tenant_id == tenant_id))
    content_settings = result.scalar_one_or_none()

    author_name = (
        content_settings.author_name
        if content_settings and content_settings.author_name
        else "o autor"
    )
    author_voice = (
        content_settings.author_voice
        if content_settings and content_settings.author_voice
        else (
            "Profissional sênior com experiência prática no setor. "
            "Tom direto, sem jargão vazio. Foco em resultados concretos."
        )
    )
    return author_name, author_voice


# ── POST /content/generate ────────────────────────────────────────────


@router.post(
    "",
    response_model=GeneratePostResponse,
    summary="Gera variações de post para LinkedIn",
)
async def generate_content(
    body: GeneratePostRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
    registry: LLMRegistry = Depends(get_llm_registry),
) -> GeneratePostResponse:
    """
    Gera N variações de post sobre um tema usando LLM.

    - `variations`: 1–5 (padrão 3)
    - `use_references`: carrega posts de referência cadastrados para few-shot
    - `provider`/`model`: sobrescreve a config padrão do sistema
    """
    author_name, author_voice = await _get_settings_or_defaults(db, tenant_id)

    # Carrega referências se solicitado
    references: list[ReferenceExample] = []
    if body.use_references:
        refs_result = await db.execute(
            select(ContentReference)
            .where(ContentReference.tenant_id == tenant_id)
            .where(ContentReference.pillar == body.pillar)
            .order_by(ContentReference.engagement_score.desc().nullslast())
            .limit(5)
        )
        refs = refs_result.scalars().all()
        references = [
            {
                "body": r.body,
                "hook_type": r.hook_type,
                "pillar": r.pillar,
            }
            for r in refs
        ]

    provider = body.provider or settings.CONTENT_GEN_PROVIDER
    model = body.model or settings.CONTENT_GEN_MODEL

    logger.info(
        "content.generate.start",
        tenant_id=str(tenant_id),
        theme=body.theme,
        pillar=body.pillar,
        variations=body.variations,
        provider=provider,
        model=model,
    )

    raw_variations: list[GeneratedVariation] = await generate_post(
        theme=body.theme,
        pillar=body.pillar,
        hook_type=body.hook_type,
        author_name=author_name,
        author_voice=author_voice,
        variations=body.variations,
        references=references,
        registry=registry,
        provider=provider,
        model=model,
        temperature=body.temperature,
    )

    logger.info(
        "content.generate.done",
        tenant_id=str(tenant_id),
        count=len(raw_variations),
    )

    return GeneratePostResponse(
        variations=[
            GeneratePostVariation(
                text=v["text"],
                character_count=v["character_count"],
                hook_type_used=v["hook_type_used"],
                violations=v["violations"],
            )
            for v in raw_variations
        ]
    )


# ── POST /content/generate/improve ───────────────────────────────────


@router.post(
    "/improve",
    response_model=ImprovePostResponse,
    summary="Melhora um post existente com instrução específica",
)
async def improve_content(
    body: ImprovePostRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
    registry: LLMRegistry = Depends(get_llm_registry),
) -> ImprovePostResponse:
    """
    Melhora um post com base em uma instrução (ex: "tornar mais direto").

    Aceita `post_id` (carrega body do BD) ou `body` (texto direto).
    Pelo menos um dos dois deve ser fornecido.
    """
    if body.post_id is None and body.body is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Informe post_id ou body.",
        )

    post_body: str
    if body.post_id is not None:
        result = await db.execute(
            select(ContentPost).where(
                ContentPost.id == body.post_id,
                ContentPost.tenant_id == tenant_id,
            )
        )
        post = result.scalar_one_or_none()
        if post is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post não encontrado.",
            )
        post_body = post.body
    else:
        if body.body is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Informe post_id ou body.",
            )
        post_body = body.body

    author_name, author_voice = await _get_settings_or_defaults(db, tenant_id)

    provider = body.provider or settings.CONTENT_GEN_PROVIDER
    model = body.model or settings.CONTENT_GEN_MODEL

    logger.info(
        "content.improve.start",
        tenant_id=str(tenant_id),
        instruction=body.instruction,
        provider=provider,
        model=model,
    )

    improved_text = await improve_post(
        body=post_body,
        instruction=body.instruction,
        author_name=author_name,
        author_voice=author_voice,
        registry=registry,
        provider=provider,
        model=model,
    )

    return ImprovePostResponse(
        text=improved_text,
        character_count=count_characters(improved_text),
        violations=validate_post(improved_text),
    )


# ── POST /content/generate/suggest-themes ────────────────────────────


@router.post(
    "/suggest-themes",
    response_model=list[ThemeSuggestion],
    summary="Sugere temas não utilizados com base nos leads em cadência",
)
async def suggest_themes(
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> list[ThemeSuggestion]:
    """
    Agrupa leads ativos (`in_cadence` | `enriched`) por setor (industry)
    e sugere temas não utilizados para os 3 principais setores.
    """
    # Top 3 setores com mais leads ativos
    active_statuses = [LeadStatus.IN_CADENCE, LeadStatus.ENRICHED]
    sector_query = (
        select(Lead.industry, func.count(Lead.id).label("lead_count"))
        .where(
            Lead.tenant_id == tenant_id,
            Lead.status.in_(active_statuses),
            Lead.industry.is_not(None),
        )
        .group_by(Lead.industry)
        .order_by(func.count(Lead.id).desc())
        .limit(3)
    )
    sector_result = await db.execute(sector_query)
    top_sectors = sector_result.all()  # [(industry, lead_count), ...]

    if not top_sectors:
        return []

    # Para cada setor, busca temas não utilizados (sem repetir IDs)
    suggestions: list[ThemeSuggestion] = []
    seen_theme_ids: set[uuid.UUID] = set()
    for industry, lead_count in top_sectors:
        themes_result = await db.execute(
            select(ContentTheme)
            .where(
                ContentTheme.tenant_id == tenant_id,
                ContentTheme.used.is_(False),
                ContentTheme.id.notin_(seen_theme_ids) if seen_theme_ids else True,
            )
            .order_by(ContentTheme.created_at.asc())
            .limit(8)
        )
        themes = themes_result.scalars().all()
        for theme in themes:
            if theme.id in seen_theme_ids:
                continue
            seen_theme_ids.add(theme.id)
            suggestions.append(
                ThemeSuggestion(
                    theme=ContentThemeResponse.model_validate(theme),
                    reason=(f"{lead_count} lead(s) do setor '{industry}' em cadência esta semana."),
                    lead_count=lead_count,
                    sector=industry,
                )
            )

    return suggestions


# ── POST /content/generate/vary-theme ────────────────────────────────


PILLAR_LABELS = {
    "authority": "Autoridade",
    "case": "Caso de sucesso",
    "vision": "Visão de mercado",
}


@router.post(
    "/vary-theme",
    response_model=VaryThemeResponse,
    summary="Gera uma variação de um tema com IA",
)
async def vary_theme(
    body: VaryThemeRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    registry: LLMRegistry = Depends(get_llm_registry),
) -> VaryThemeResponse:
    """
    Recebe o título de um tema e retorna uma variação com ângulo diferente,
    mantendo o mesmo pilar e essência do assunto original.
    """
    pillar_label = PILLAR_LABELS.get(body.pillar, body.pillar)

    prompt = (
        f"Você é um especialista em marketing de conteúdo B2B para LinkedIn.\n"
        f"Pilar: {pillar_label}\n"
        f"Tema original: {body.theme_title}\n\n"
        "Crie UMA variação desse tema com um ângulo ou abordagem diferente, "
        "mantendo a essência e o pilar. "
        "Responda apenas com o novo título do tema, sem explicações, aspas ou formatação extra. "
        "Máximo 120 caracteres."
    )

    from integrations.llm import LLMMessage  # local import para evitar circular

    messages = [LLMMessage(role="user", content=prompt)]

    response = await registry.complete(
        messages=messages,
        provider=settings.CONTENT_GEN_PROVIDER,
        model=settings.CONTENT_GEN_MODEL,
        temperature=0.9,
        max_tokens=128,
    )

    variation = response.text.strip().strip('"').strip("'").strip()
    logger.info("vary_theme.done", tenant_id=tenant_id, original=body.theme_title)

    return VaryThemeResponse(variation=variation)
