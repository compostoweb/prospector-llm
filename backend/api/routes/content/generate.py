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
from typing import cast

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import (
    get_effective_tenant_id,
    get_llm_registry,
    get_session_flexible,
)
from integrations.llm import LLMRegistry
from models.content_lead_magnet import ContentLeadMagnet
from models.content_post import ContentPost
from models.content_reference import ContentReference
from models.content_settings import ContentSettings
from models.content_theme import ContentTheme
from models.enums import LeadStatus
from models.lead import Lead
from schemas.content import (
    ContentThemeResponse,
    DetectHookRequest,
    DetectHookResponse,
    GeneratePostImageRequest,
    GeneratePostImageResponse,
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
    LeadMagnetPromptContext,
    ReferenceExample,
    generate_post,
    improve_post,
)
from services.content.rules import count_characters, validate_post
from services.llm_config import merge_llm_config, resolve_tenant_llm_config

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


async def _resolve_content_llm_config(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    provider: str | None = None,
    model: str | None = None,
) -> tuple[str, str, float, int]:
    config = await resolve_tenant_llm_config(db, tenant_id)
    merged = merge_llm_config(config, provider=provider, model=model)
    return merged.provider, merged.model, merged.temperature, merged.max_tokens


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

    provider, model, _, max_tokens = await _resolve_content_llm_config(
        db,
        tenant_id,
        provider=body.provider,
        model=body.model,
    )
    lead_magnet_context: LeadMagnetPromptContext | None = None

    if body.content_goal == "lead_magnet_launch":
        if body.lead_magnet_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Informe lead_magnet_id para gerar um lançamento de lead magnet.",
            )

        lead_magnet_result = await db.execute(
            select(ContentLeadMagnet).where(
                ContentLeadMagnet.id == body.lead_magnet_id,
                ContentLeadMagnet.tenant_id == tenant_id,
            )
        )
        lead_magnet = lead_magnet_result.scalar_one_or_none()
        if lead_magnet is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lead magnet não encontrado.",
            )

        lead_magnet_context = LeadMagnetPromptContext(
            title=lead_magnet.title,
            description=lead_magnet.description,
            cta_text=lead_magnet.cta_text,
            type=lead_magnet.type,
            distribution_type=body.launch_distribution_type,
            trigger_word=body.launch_trigger_word,
        )

    logger.info(
        "content.generate.start",
        tenant_id=str(tenant_id),
        theme=body.theme,
        pillar=body.pillar,
        content_goal=body.content_goal,
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
        tenant_id=str(tenant_id),
        provider=provider,
        model=model,
        temperature=body.temperature,
        max_tokens=max_tokens,
        content_goal=body.content_goal,
        lead_magnet_context=lead_magnet_context,
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

    provider, model, temperature, max_tokens = await _resolve_content_llm_config(
        db,
        tenant_id,
        provider=body.provider,
        model=body.model,
    )

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
        tenant_id=str(tenant_id),
        provider=provider,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
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
        themes_query = (
            select(ContentTheme)
            .where(ContentTheme.tenant_id == tenant_id)
            .where(ContentTheme.used.is_(False))
            .order_by(ContentTheme.created_at.asc())
            .limit(8)
        )
        if seen_theme_ids:
            themes_query = themes_query.where(
                ContentTheme.id.notin_(cast(set[object], seen_theme_ids))
            )
        themes_result = await db.execute(themes_query)
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
    db: AsyncSession = Depends(get_session_flexible),
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

    from integrations.llm import LLMMessage, LLMUsageContext  # local import para evitar circular

    messages = [LLMMessage(role="user", content=prompt)]
    provider, model, _, _ = await _resolve_content_llm_config(db, tenant_id)

    response = await registry.complete(
        messages=messages,
        provider=provider,
        model=model,
        temperature=0.9,
        max_tokens=48,
        usage_context=LLMUsageContext(
            tenant_id=str(tenant_id),
            module="content_hub",
            task_type="vary_theme",
            feature=body.pillar,
            metadata={"theme_title": body.theme_title[:160]},
        ),
    )

    variation = response.text.strip().strip('"').strip("'").strip()
    logger.info("vary_theme.done", tenant_id=tenant_id, original=body.theme_title)

    return VaryThemeResponse(variation=variation)


# ── POST /content/generate/detect-hook ─────────────────────────────────────────────

HOOK_DESCRIPTIONS = (
    "- loop_open: abre uma história ou pergunta que só será respondida no final\n"
    "- contrarian: vai contra uma crença popular do mercado\n"
    "- identification: leía se identifica diretamente (dor, situção, perfil)\n"
    "- shortcut: promete um caminho mais rápido ou mais fácil para algo\n"
    "- benefit: apresenta um benefício claro e direto na primeira linha\n"
    "- data: abre com um número, estatística ou dado concreto\n"
)


@router.post(
    "/detect-hook",
    response_model=DetectHookResponse,
    summary="Detecta o tipo de gancho de um post com IA",
)
async def detect_hook(
    body: DetectHookRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
    registry: LLMRegistry = Depends(get_llm_registry),
) -> DetectHookResponse:
    """
    Analisa as primeiras linhas do post e classifica o tipo de gancho
    em um dos 6 tipos disponíveis.
    """
    from integrations.llm import LLMMessage, LLMUsageContext

    # Usa apenas as primeiras 3 linhas não vazias — o gancho é sempre no início
    first_lines = "\n".join([l for l in body.body.strip().splitlines() if l.strip()][:3])

    prompt = (
        "Você é especialista em copywriting para LinkedIn.\n"
        "Analise as primeiras linhas do post abaixo e classifique o tipo de gancho.\n\n"
        f"Tipos disponíveis:\n{HOOK_DESCRIPTIONS}\n"
        f"Primeiras linhas do post:\n{first_lines}\n\n"
        "Responda APENAS com a chave do tipo (ex: loop_open), sem explicações."
    )

    messages = [LLMMessage(role="user", content=prompt)]
    provider, model, _, _ = await _resolve_content_llm_config(db, tenant_id)
    response = await registry.complete(
        messages=messages,
        provider=provider,
        model=model,
        temperature=0.1,
        max_tokens=8,
        usage_context=LLMUsageContext(
            tenant_id=str(tenant_id),
            module="content_hub",
            task_type="detect_hook",
            feature="hook_classification",
        ),
    )

    valid_hooks = {"loop_open", "contrarian", "identification", "shortcut", "benefit", "data"}
    detected = response.text.strip().lower().split()[0].rstrip(".")
    if detected not in valid_hooks:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Não foi possível detectar o tipo de gancho. Resposta recebida: {response.text!r}",
        )

    logger.info("detect_hook.done", hook_type=detected, tenant_id=str(tenant_id))
    return DetectHookResponse(hook_type=detected)


# ── POST /content/generate/image ─────────────────────────────────────


@router.post(
    "/image",
    response_model=GeneratePostImageResponse,
    summary="Gera imagem para o post via Gemini Nano Banana 2",
)
async def generate_post_image(
    body: GeneratePostImageRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
    registry: LLMRegistry = Depends(get_llm_registry),
) -> GeneratePostImageResponse:
    """
    Gera imagem usando gemini-3.1-flash-image-preview (Nano Banana 2).

    Faz upload para S3/MinIO e atualiza os campos de imagem do post.
    Retorna image_url e o prompt usado (para referência ou regeneração).
    """
    from integrations.s3_client import S3Client
    from services.content.image_generator import generate_post_image as svc_generate_image

    result = await db.execute(
        select(ContentPost).where(
            ContentPost.id == body.post_id,
            ContentPost.tenant_id == tenant_id,
        )
    )
    post = result.scalar_one_or_none()
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post não encontrado.")

    # Deleta imagem anterior do S3 se existir
    if post.image_s3_key:
        try:
            S3Client().delete_object(post.image_s3_key)
        except Exception:
            pass

    try:
        image_bytes, prompt_used = await svc_generate_image(
            post=post,
            style=body.style,
            registry=registry,
            aspect_ratio=body.aspect_ratio,
            sub_type=body.sub_type,
            custom_prompt=body.custom_prompt,
        )
    except ValueError as exc:
        logger.warning("content.image_generation_failed", error=str(exc), post_id=str(body.post_id))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Falha na geração de imagem: {exc}",
        ) from exc
    except Exception as exc:
        exc_str = str(exc)
        logger.error("content.image_generation_error", error=exc_str, post_id=str(body.post_id))
        if "429" in exc_str or "RESOURCE_EXHAUSTED" in exc_str:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Cota da API Gemini esgotada. Verifique seu plano e billing em ai.google.dev.",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro ao gerar imagem: {exc}",
        ) from exc

    s3_key = f"images/{tenant_id}/{body.post_id}.png"
    s3 = S3Client()
    image_url = s3.upload_bytes(image_bytes, s3_key, "image/png")

    post.image_url = image_url
    post.image_s3_key = s3_key
    post.image_style = body.style
    post.image_prompt = prompt_used
    post.image_aspect_ratio = body.aspect_ratio
    post.linkedin_image_urn = None  # URN anterior inválido após nova imagem

    await db.commit()

    logger.info(
        "content.image_generated",
        post_id=str(body.post_id),
        tenant_id=str(tenant_id),
        style=body.style,
        aspect_ratio=body.aspect_ratio,
    )

    return GeneratePostImageResponse(image_url=image_url, image_prompt=prompt_used)
