"""
api/routes/content/references.py

Posts de referencia de alta performance para uso como few-shot no LLM.

GET    /content/references      — listar
POST   /content/references      — adicionar
DELETE /content/references/{id} — remover
"""

from __future__ import annotations

import json
import re
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
        author_company=body.author_company,
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
    author_company: str | None = None
    hook_type: str | None = None
    pillar: str | None = None
    engagement_score: int | None = None
    notes: str | None = None


def _extract_linkedin_profile_url(post_url: str, content: str) -> str | None:
    """
    Extrai a URL do perfil público do autor a partir do URL do post ou do
    conteúdo Jina renderizado.

    Perfis LinkedIn públicos expõem o headline/empresa — ao contrário dos
    posts, onde LinkedIn esconde o headline de visitantes não logados.
    """
    # 1. Do conteúdo Jina: href de link para /in/username
    m = re.search(
        r"https?://(?:[a-z]{2}\.)?linkedin\.com/in/([a-zA-Z0-9_%-]+)",
        content,
    )
    if m:
        slug = m.group(1).rstrip("/")
        return f"https://www.linkedin.com/in/{slug}/"

    # 2. Do URL do post: linkedin.com/posts/{username}_...
    m = re.search(r"linkedin\.com/posts/([a-zA-Z0-9_%-]+?)_", post_url)
    if m:
        slug = m.group(1)
        return f"https://www.linkedin.com/in/{slug}/"

    return None


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

    fetcher = ContextFetcher()
    content = await fetcher.fetch_from_website(body.url)
    if not content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Não foi possível extrair conteúdo da URL",
        )

    # LinkedIn esconde o headline do autor em posts públicos.
    # Usa a API Unipile (que tem sessão autenticada) para buscar cargo e empresa.
    # Fallback: anexa conteúdo do perfil via Jina se Unipile não estiver configurado.
    profile_context = ""
    unipile_author_title: str | None = None
    unipile_author_company: str | None = None

    profile_url = _extract_linkedin_profile_url(body.url, content)
    if profile_url and "linkedin.com" in body.url:
        # 1. Tentar via Unipile (tem autenticação real no LinkedIn)
        try:
            from core.config import settings as _settings
            from integrations.unipile_client import UnipileClient

            _acc = _settings.UNIPILE_ACCOUNT_ID_LINKEDIN or ""
            if _acc:
                _unipile = UnipileClient()
                _profile = await _unipile.get_linkedin_profile(
                    account_id=_acc,
                    linkedin_url=profile_url,
                )
                await _unipile._client.aclose()
                if _profile:
                    unipile_author_title = _profile.headline
                    unipile_author_company = _profile.company
                    logger.debug(
                        "content.analyze_url_profile_unipile_ok",
                        profile_url=profile_url,
                        headline=_profile.headline,
                        company=_profile.company,
                    )
        except Exception as exc:
            logger.debug("content.analyze_url_profile_unipile_failed", error=str(exc))

        # 2. Fallback: Jina — só usa se não for authwall
        if unipile_author_title is None:
            try:
                profile_content = await fetcher.fetch_from_website(profile_url)
                _authwall = "Sign Up | LinkedIn" in (profile_content or "")[:400]
                if profile_content and not _authwall:
                    profile_context = (
                        f"\n\n--- Perfil público do autor ({profile_url}) ---\n"
                        + profile_content[:2000]
                    )
                    logger.debug(
                        "content.analyze_url_profile_jina_ok",
                        profile_url=profile_url,
                        chars=len(profile_content),
                    )
                else:
                    logger.debug(
                        "content.analyze_url_profile_authwall",
                        profile_url=profile_url,
                    )
            except Exception as exc:
                logger.debug("content.analyze_url_profile_fetch_failed", error=str(exc))

    # Se Unipile forneceu dados, injeta no prompt para o GPT não precisar adivinhar
    unipile_hint = ""
    if unipile_author_title or unipile_author_company:
        unipile_hint = "\n\nDados do perfil LinkedIn (fonte confiável, use diretamente):\n"
        if unipile_author_title:
            unipile_hint += f"- author_title: {unipile_author_title}\n"
        if unipile_author_company:
            unipile_hint += f"- author_company: {unipile_author_company}\n"

    messages: list[LLMMessage] = [
        LLMMessage(
            role="system",
            content="Você é um analista de conteúdo especializado em posts do LinkedIn.",
        ),
        LLMMessage(
            role="user",
            content=(
                "Analise o conteúdo abaixo e retorne um JSON com os seguintes campos:\n"
                "- body: texto COMPLETO do post. Reconstrua a formatação LinkedIn original:\n"
                "  * Parágrafos separados por \\n\\n\n"
                "  * Cada bullet/item de lista (→, •, -, ■) em linha própria, precedido de \\n\n"
                "  * Preserve emojis e símbolos especiais. (string)\n"
                "- author_name: primeiro nome e sobrenome do autor (string ou null)\n"
                "- author_title: cargo principal do autor, ex: 'CEO', 'Founder', 'Head de Marketing'.\n"
                "  Extraia do perfil se disponível. Se não encontrar, retorne null. (string ou null)\n"
                "- author_company: empresa ou organização atual do autor.\n"
                "  Extraia do perfil se disponível. Se não encontrar, retorne null. (string ou null)\n"
                "- hook_type: tipo de gancho — um de: loop_open, contrarian, identification, "
                "shortcut, benefit, data (string ou null)\n"
                "- pillar: pilar de conteúdo — um de: authority, case, vision (string ou null)\n"
                "- engagement_score: estimativa de engajamento de 0 a 100 (int ou null)\n"
                "- notes: 1-2 frases sobre estrutura e técnicas usadas (string ou null)\n\n"
                f"Conteúdo do post (primeiros 6000 chars):\n{content[:6000]}"
                f"{profile_context}"
                f"{unipile_hint}"
            ),
        ),
    ]

    resp = await registry.complete(
        messages=messages,
        provider="openai",
        model="gpt-4o-mini",
        temperature=0.3,
        max_tokens=1500,
        json_mode=True,
    )

    try:
        data = json.loads(resp.text)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.error("content.analyze_url_parse_error", error=str(exc), url=body.url)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Erro ao interpretar resposta da IA",
        ) from exc

    # Dados do Unipile têm precedência sobre a inferência da IA
    if unipile_author_title:
        data["author_title"] = unipile_author_title
    if unipile_author_company:
        data["author_company"] = unipile_author_company

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
