"""
api/routes/content/landing_pages.py

Configuração interna e captura pública de landing pages de lead magnets.
"""

from __future__ import annotations

import uuid
from typing import cast

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_effective_tenant_id, get_session_flexible, get_session_no_auth
from models.content_landing_page import ContentLandingPage
from models.content_lead_magnet import ContentLeadMagnet
from schemas.content_inbound import (
    ContentLandingPageResponse,
    ContentLandingPageUpsert,
    LandingPagePublicCaptureRequest,
    LandingPagePublicCaptureResponse,
    LandingPagePublicResponse,
    LeadMagnetType,
    LMSendPulseSyncStatus,
)
from services.content.lead_magnet_service import (
    build_public_landing_page_url,
    queue_sendpulse_sync,
    recalculate_conversion_rate,
    update_landing_page_submission_stats,
    upsert_lm_capture,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/landing-pages", tags=["Content Hub — Landing Pages"])


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
        public_url=build_public_landing_page_url(landing_page.slug),
    )


@router.post("/public/{slug}/capture", response_model=LandingPagePublicCaptureResponse)
async def capture_public_lead(
    slug: str,
    body: LandingPagePublicCaptureRequest,
    request: Request,
    db: AsyncSession = Depends(get_session_no_auth),
) -> LandingPagePublicCaptureResponse:
    landing_page, lead_magnet = await _get_public_page_or_404(db, slug=slug)
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
