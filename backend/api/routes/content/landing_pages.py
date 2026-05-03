"""
api/routes/content/landing_pages.py

Configuração interna e captura pública de landing pages de lead magnets.
"""

from __future__ import annotations

import uuid
from typing import Literal, cast

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_effective_tenant_id, get_llm_registry, get_session_flexible, get_session_no_auth
from core.file_security import detect_image_content_type, pick_image_extension
from integrations.llm import LLMMessage, LLMRegistry, LLMResponse
from models.content_landing_page import ContentLandingPage
from models.content_lead_magnet import ContentLeadMagnet
from schemas.content_inbound import (
    ContentLandingPageResponse,
    ContentLandingPageUpsert,
    LandingPageFormField,
    LandingPagePublicCaptureRequest,
    LandingPagePublicCaptureResponse,
    LandingPagePublicResponse,
    LeadMagnetType,
    LMSendPulseSyncStatus,
    LPImageUploadResponse,
    LPImproveFieldRequest,
    LPImproveFieldResponse,
)
from services.content.lead_magnet_service import (
    build_public_landing_page_url,
    queue_lm_delivery_email,
    queue_sendpulse_sync,
    recalculate_conversion_rate,
    update_landing_page_submission_stats,
    upsert_lm_capture,
)
from services.llm_config import resolve_tenant_llm_config

logger = structlog.get_logger()

router = APIRouter(prefix="/landing-pages", tags=["Content Hub — Landing Pages"])

_DEFAULT_FORM_FIELDS_BY_TYPE: dict[str, list[LandingPageFormField]] = {
    "link": [
        LandingPageFormField(key="name", required=True),
        LandingPageFormField(key="email", required=True),
    ],
    "pdf": [
        LandingPageFormField(key="name", required=True),
        LandingPageFormField(key="email", required=True),
        LandingPageFormField(key="company", required=True),
    ],
    "email_sequence": [
        LandingPageFormField(key="name", required=True),
        LandingPageFormField(key="email", required=True),
        LandingPageFormField(key="company", required=True),
        LandingPageFormField(key="role", required=True),
    ],
    "calculator": [
        LandingPageFormField(key="name", required=True),
        LandingPageFormField(key="email", required=True),
        LandingPageFormField(key="company", required=True),
        LandingPageFormField(key="role", required=True),
    ],
}


async def _get_lead_magnet_or_404(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    lead_magnet_id: uuid.UUID,
) -> ContentLeadMagnet:
    result = await db.execute(
        select(ContentLeadMagnet).where(
            ContentLeadMagnet.id == lead_magnet_id,
            ContentLeadMagnet.tenant_id == tenant_id,
        )
    )
    lead_magnet = result.scalar_one_or_none()
    if lead_magnet is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lead magnet não encontrado"
        )
    return lead_magnet


async def _get_landing_page_by_lead_magnet(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    lead_magnet_id: uuid.UUID,
) -> ContentLandingPage | None:
    result = await db.execute(
        select(ContentLandingPage).where(
            ContentLandingPage.tenant_id == tenant_id,
            ContentLandingPage.lead_magnet_id == lead_magnet_id,
        )
    )
    return result.scalar_one_or_none()


async def _get_public_page_or_404(
    db: AsyncSession,
    *,
    slug: str,
) -> tuple[ContentLandingPage, ContentLeadMagnet]:
    result = await db.execute(
        select(ContentLandingPage, ContentLeadMagnet)
        .join(ContentLeadMagnet, ContentLeadMagnet.id == ContentLandingPage.lead_magnet_id)
        .where(
            ContentLandingPage.slug == slug,
            ContentLandingPage.published.is_(True),
            ContentLeadMagnet.status == "active",
        )
    )
    row = result.first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Landing page não encontrada"
        )
    return cast(tuple[ContentLandingPage, ContentLeadMagnet], (row[0], row[1]))


def _validate_capture_fields_for_type(
    *,
    lead_magnet_type: str,
    form_fields: list[dict] | None,
    body: LandingPagePublicCaptureRequest,
) -> None:
    missing: list[str] = []
    configured_fields = _resolve_form_fields(lead_magnet_type=lead_magnet_type, form_fields=form_fields)
    for field in configured_fields:
        if field.key in {"name", "email"}:
            continue
        if field.required and not (getattr(body, field.key) or "").strip():
            missing.append(field.key)

    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Campos obrigatórios ausentes: {', '.join(missing)}",
        )


def _resolve_form_fields(
    *,
    lead_magnet_type: str,
    form_fields: list[dict] | None,
) -> list[LandingPageFormField]:
    if not form_fields:
        return _DEFAULT_FORM_FIELDS_BY_TYPE.get(
            lead_magnet_type,
            _DEFAULT_FORM_FIELDS_BY_TYPE["pdf"],
        )

    resolved: list[LandingPageFormField] = []
    seen: set[str] = set()
    for raw_field in form_fields:
        field = LandingPageFormField.model_validate(raw_field)
        if field.key in seen:
            continue
        resolved.append(field)
        seen.add(field.key)

    for required_key in ("name", "email"):
        if required_key not in seen:
            resolved.insert(0 if required_key == "name" else 1, LandingPageFormField(key=required_key, required=True))
    return resolved


@router.get("/{lead_magnet_id}", response_model=ContentLandingPageResponse)
async def get_landing_page(
    lead_magnet_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ContentLandingPageResponse:
    await _get_lead_magnet_or_404(db, tenant_id=tenant_id, lead_magnet_id=lead_magnet_id)
    landing_page = await _get_landing_page_by_lead_magnet(
        db, tenant_id=tenant_id, lead_magnet_id=lead_magnet_id
    )
    if landing_page is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Landing page não configurada"
        )
    return ContentLandingPageResponse.model_validate(landing_page)


@router.put("/{lead_magnet_id}", response_model=ContentLandingPageResponse)
async def upsert_landing_page(
    lead_magnet_id: uuid.UUID,
    body: ContentLandingPageUpsert,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ContentLandingPageResponse:
    await _get_lead_magnet_or_404(db, tenant_id=tenant_id, lead_magnet_id=lead_magnet_id)
    existing_page = await _get_landing_page_by_lead_magnet(
        db, tenant_id=tenant_id, lead_magnet_id=lead_magnet_id
    )

    slug_check = await db.execute(
        select(ContentLandingPage.id).where(ContentLandingPage.slug == body.slug)
    )
    conflicting_id = slug_check.scalar_one_or_none()
    if conflicting_id is not None and (existing_page is None or conflicting_id != existing_page.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Slug já utilizado por outra landing page"
        )

    if existing_page is None:
        existing_page = ContentLandingPage(
            tenant_id=tenant_id,
            lead_magnet_id=lead_magnet_id,
            **body.model_dump(),
        )
        db.add(existing_page)
    else:
        for field, value in body.model_dump().items():
            setattr(existing_page, field, value)

    await db.commit()
    await db.refresh(existing_page)
    logger.info(
        "content.landing_page.upserted",
        lead_magnet_id=str(lead_magnet_id),
        tenant_id=str(tenant_id),
    )
    return ContentLandingPageResponse.model_validate(existing_page)


@router.get("/public/{slug}", response_model=LandingPagePublicResponse)
async def get_public_landing_page(
    slug: str,
    db: AsyncSession = Depends(get_session_no_auth),
) -> LandingPagePublicResponse:
    landing_page, lead_magnet = await _get_public_page_or_404(db, slug=slug)
    await update_landing_page_submission_stats(landing_page, increment_views=1)
    lead_magnet.conversion_rate = recalculate_conversion_rate(
        lead_magnet.total_leads_captured,
        landing_page.total_views,
    )
    await db.commit()

    return LandingPagePublicResponse(
        id=landing_page.id,
        lead_magnet_id=lead_magnet.id,
        lead_magnet_type=cast(LeadMagnetType, lead_magnet.type),
        lead_magnet_title=lead_magnet.title,
        lead_magnet_description=lead_magnet.description,
        file_url=lead_magnet.file_url,
        cta_text=lead_magnet.cta_text,
        slug=landing_page.slug,
        title=landing_page.title,
        subtitle=landing_page.subtitle,
        hero_image_url=landing_page.hero_image_url,
        benefits=landing_page.benefits,
        social_proof_count=landing_page.social_proof_count,
        author_bio=landing_page.author_bio,
        author_photo_url=landing_page.author_photo_url,
        meta_title=landing_page.meta_title,
        meta_description=landing_page.meta_description,
        publisher_name=landing_page.publisher_name,
        features=landing_page.features,
        expected_result=landing_page.expected_result,
        badge_text=landing_page.badge_text,
        form_fields=_resolve_form_fields(
            lead_magnet_type=lead_magnet.type,
            form_fields=landing_page.form_fields,
        ),
        public_url=build_public_landing_page_url(landing_page.slug),
    )


@router.post("/{lead_magnet_id}/upload-lp-image", response_model=LPImageUploadResponse)
async def upload_lp_image(
    lead_magnet_id: uuid.UUID,
    file: UploadFile = File(...),
    image_field: Literal["hero", "author"] = Query(default="hero"),
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> LPImageUploadResponse:
    await _get_lead_magnet_or_404(db, tenant_id=tenant_id, lead_magnet_id=lead_magnet_id)

    allowed_mime = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed_mime:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Formato inválido. Use JPEG, PNG ou WebP.",
        )

    image_bytes = await file.read()
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Imagem muito grande. Máximo 10 MB.",
        )

    detected_content_type = detect_image_content_type(image_bytes)
    if detected_content_type is None or detected_content_type not in allowed_mime:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Conteudo do arquivo nao corresponde a uma imagem suportada.",
        )

    if detected_content_type != file.content_type:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Conteudo do arquivo nao corresponde ao content_type enviado. "
                f"Detectado: {detected_content_type}; recebido: {file.content_type}."
            ),
        )

    ext = pick_image_extension(
        content_type=detected_content_type,
        original_filename=file.filename or f"{image_field}.jpg",
    ).lstrip(".")
    s3_key = f"lm-images/{tenant_id}/{lead_magnet_id}-{image_field}.{ext}"

    from integrations.s3_client import S3Client

    s3 = S3Client()
    s3.upload_bytes(image_bytes, s3_key, detected_content_type)
    url = s3.get_masked_url(s3_key)

    logger.info(
        "content.landing_page.image_uploaded",
        lead_magnet_id=str(lead_magnet_id),
        image_field=image_field,
        tenant_id=str(tenant_id),
    )
    return LPImageUploadResponse(url=url)


_LP_FIELD_PROMPTS: dict[str, str] = {
    "title": (
        "Você é copywriter B2B. Melhore o título de landing page abaixo para o lead magnet "
        "'{lm_title}' (tipo: {lm_type}). Seja direto, resultado-orientado, 8 a 15 palavras. "
        "Retorne APENAS o título melhorado, sem aspas.\n\nTítulo atual: {current_value}"
    ),
    "subtitle": (
        "Você é copywriter B2B. Melhore este subtítulo de landing page. 1 a 2 frases práticas "
        "e convincentes. Retorne APENAS o subtítulo, sem aspas.\n\nSubtítulo atual: {current_value}"
    ),
    "benefits": (
        "Você é copywriter B2B. Melhore estes benefícios de landing page para '{lm_title}'. "
        "Retorne 1 benefício por linha, sem marcadores, sem numeração, sem linhas em branco. "
        "Benefícios atuais:\n{current_value}"
    ),
    "meta_title": (
        "Você é especialista em SEO. Gere um meta title de até 60 caracteres para a landing page "
        "do lead magnet '{lm_title}'. Retorne APENAS o meta title, sem aspas."
    ),
    "meta_description": (
        "Você é especialista em SEO. Gere uma meta description de até 155 caracteres com CTA "
        "para a landing page do lead magnet '{lm_title}'. Retorne APENAS a meta description."
    ),
    "features": (
        "Você é copywriter B2B. Gere 2 cards de destaque para a landing page do lead magnet "
        "'{lm_title}' (tipo: {lm_type}). Cada card tem título curto (3-5 palavras) e descrição "
        "(2-3 frases práticas, resultado-orientadas). "
        "Retorne APENAS um JSON array válido, sem code block, neste exato formato:\n"
        '[{{"title": "...", "description": "..."}}, {{"title": "...", "description": "..."}}]'
        "\n\nValores atuais:\n{current_value}"
    ),
    "expected_result": (
        "Você é copywriter B2B. Escreva o texto do card 'Resultado esperado' para a landing page "
        "do lead magnet '{lm_title}'. 2-3 frases diretas descrevendo o resultado prático que o "
        "lead vai obter. Retorne APENAS o texto, sem aspas."
        "\n\nTexto atual: {current_value}"
    ),
    "badge_text": (
        "Você é copywriter B2B. Escreva uma frase curta de posicionamento (até 12 palavras) para o "
        "badge exibido acima do título da landing page do lead magnet '{lm_title}' (tipo: {lm_type}). "
        "Deve comunicar o perfil do público ou o benefício central — sem verbos de ação, sem pontuação "
        "final. Retorne APENAS o texto do badge, sem aspas."
        "\n\nTexto atual: {current_value}"
    ),
    "email_subject": (
        "Você é copywriter B2B especialista em email marketing. Escreva um assunto de e-mail "
        "transacional para o lead magnet '{lm_title}' (tipo: {lm_type}). "
        "O e-mail é enviado automaticamente após o lead se cadastrar na landing page para receber o material. "
        "Máximo 70 caracteres. Tom direto e pessoal. Retorne APENAS o assunto, sem aspas."
        "\n\nAssunto atual: {current_value}"
    ),
    "email_headline": (
        "Você é copywriter B2B. Escreva o headline principal (H1) do e-mail de entrega do lead magnet "
        "'{lm_title}' (tipo: {lm_type}). Máximo 10 palavras, tom direto, transmite clareza e valor imediato. "
        "Retorne APENAS o headline, sem aspas."
        "\n\nHeadline atual: {current_value}"
    ),
    "email_body_text": (
        "Você é copywriter B2B. Escreva o corpo do e-mail de entrega do lead magnet '{lm_title}' (tipo: {lm_type}). "
        "O texto vem APÓS o prefixo '{nome},' que é inserido automaticamente — portanto escreva apenas o "
        "complemento: comece com letra minúscula, como continuação natural da frase após o nome. "
        "2 a 3 frases curtas, tom pessoal, foca no benefício imediato e instrui o próximo passo. "
        "Retorne APENAS o texto complementar, sem aspas."
        "\n\nTexto atual: {current_value}"
    ),
    "email_cta_label": (
        "Você é copywriter B2B. Escreva o texto do botão de CTA do e-mail de entrega do lead magnet "
        "'{lm_title}' (tipo: {lm_type}). Máximo 30 caracteres, imperativo, orientado à ação. "
        "Exemplos: 'Baixar material', 'Acessar agora', 'Ver diagnóstico'. "
        "Retorne APENAS o texto do botão, sem aspas."
        "\n\nTexto atual: {current_value}"
    ),
}


@router.post("/ai/improve-field", response_model=LPImproveFieldResponse)
async def improve_lp_field(
    body: LPImproveFieldRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
    registry: LLMRegistry = Depends(get_llm_registry),
) -> LPImproveFieldResponse:
    llm_config = await resolve_tenant_llm_config(db, tenant_id, scope="system")

    prompt_template = _LP_FIELD_PROMPTS[body.field]
    prompt = prompt_template.format(
        lm_title=body.lead_magnet_title,
        lm_type=body.lead_magnet_type,
        current_value=body.current_value,
    )
    if body.context:
        prompt += f"\n\nContexto adicional: {body.context}"

    messages = [LLMMessage(role="user", content=prompt)]
    llm_response: LLMResponse = await registry.complete(
        messages=messages,
        provider=llm_config.provider,
        model=llm_config.model,
        temperature=0.7,
        max_tokens=512,
    )

    improved = llm_response.text.strip()
    logger.info(
        "content.landing_page.ai_improved",
        field=body.field,
        tenant_id=str(tenant_id),
    )
    return LPImproveFieldResponse(improved=improved)


@router.post("/public/{slug}/capture", response_model=LandingPagePublicCaptureResponse)
async def capture_public_lead(
    slug: str,
    body: LandingPagePublicCaptureRequest,
    request: Request,
    db: AsyncSession = Depends(get_session_no_auth),
) -> LandingPagePublicCaptureResponse:
    landing_page, lead_magnet = await _get_public_page_or_404(db, slug=slug)
    _validate_capture_fields_for_type(
        lead_magnet_type=lead_magnet.type,
        form_fields=landing_page.form_fields,
        body=body,
    )
    lm_lead, _, should_sync = await upsert_lm_capture(
        db,
        lead_magnet=lead_magnet,
        name=body.name,
        email=body.email,
        origin="landing_page",
        linkedin_profile_url=body.linkedin_profile_url,
        company=body.company,
        role=body.role,
        phone=body.phone,
        capture_metadata={
            "session_id": body.session_id,
            "ip_address": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
        },
    )
    await update_landing_page_submission_stats(landing_page, increment_submissions=1)
    lead_magnet.conversion_rate = recalculate_conversion_rate(
        lead_magnet.total_leads_captured,
        landing_page.total_views,
    )
    await db.commit()
    await db.refresh(lm_lead)

    if should_sync:
        await queue_sendpulse_sync(lm_lead)

    if lead_magnet.type != "calculator":
        await queue_lm_delivery_email(lm_lead)

    logger.info(
        "content.landing_page.captured",
        slug=slug,
        lm_lead_id=str(lm_lead.id),
        lead_magnet_id=str(lead_magnet.id),
    )
    return LandingPagePublicCaptureResponse(
        lm_lead_id=lm_lead.id,
        sendpulse_sync_status=cast(LMSendPulseSyncStatus, lm_lead.sendpulse_sync_status),
    )
