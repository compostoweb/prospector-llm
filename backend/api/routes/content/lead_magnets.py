"""
api/routes/content/lead_magnets.py

CRUD e gestão de lead magnets do subsistema inbound do Content Hub.
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_effective_tenant_id, get_session_flexible
from models.content_lead_magnet import ContentLeadMagnet
from models.content_lm_lead import ContentLMLead
from models.content_lm_post import ContentLMPost
from models.content_post import ContentPost
from schemas.content_inbound import (
    ContentLeadMagnetCreate,
    ContentLeadMagnetResponse,
    ContentLeadMagnetStatusUpdate,
    ContentLeadMagnetUpdate,
    ContentLMLeadConvertResponse,
    ContentLMLeadCreate,
    ContentLMLeadResponse,
    ContentLMPostCreate,
    ContentLMPostResponse,
    LeadMagnetMetricsResponse,
)
from services.content.lead_magnet_service import (
    convert_lm_lead_to_prospect,
    get_lead_magnet_metrics,
    queue_sendpulse_sync,
    upsert_lm_capture,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/lead-magnets", tags=["Content Hub — Lead Magnets"])


async def _get_lead_magnet_or_404(
    lead_magnet_id: uuid.UUID,
    tenant_id: uuid.UUID,
    db: AsyncSession,
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


async def _get_lm_lead_or_404(
    lm_lead_id: uuid.UUID,
    lead_magnet_id: uuid.UUID,
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> ContentLMLead:
    result = await db.execute(
        select(ContentLMLead).where(
            ContentLMLead.id == lm_lead_id,
            ContentLMLead.lead_magnet_id == lead_magnet_id,
            ContentLMLead.tenant_id == tenant_id,
        )
    )
    lm_lead = result.scalar_one_or_none()
    if lm_lead is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lead capturado não encontrado"
        )
    return lm_lead


async def _validate_content_post(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    content_post_id: uuid.UUID,
) -> None:
    result = await db.execute(
        select(ContentPost.id).where(
            ContentPost.id == content_post_id,
            ContentPost.tenant_id == tenant_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post do calendário editorial não encontrado",
        )


@router.get("", response_model=list[ContentLeadMagnetResponse])
async def list_lead_magnets(
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> list[ContentLeadMagnetResponse]:
    result = await db.execute(
        select(ContentLeadMagnet)
        .where(ContentLeadMagnet.tenant_id == tenant_id)
        .order_by(ContentLeadMagnet.created_at.desc())
    )
    return [ContentLeadMagnetResponse.model_validate(item) for item in result.scalars().all()]


@router.post("", response_model=ContentLeadMagnetResponse, status_code=status.HTTP_201_CREATED)
async def create_lead_magnet(
    body: ContentLeadMagnetCreate,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ContentLeadMagnetResponse:
    lead_magnet = ContentLeadMagnet(tenant_id=tenant_id, **body.model_dump())
    db.add(lead_magnet)
    await db.commit()
    await db.refresh(lead_magnet)
    logger.info(
        "content.lead_magnet.created", lead_magnet_id=str(lead_magnet.id), tenant_id=str(tenant_id)
    )
    return ContentLeadMagnetResponse.model_validate(lead_magnet)


@router.get("/{lead_magnet_id}", response_model=ContentLeadMagnetResponse)
async def get_lead_magnet(
    lead_magnet_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ContentLeadMagnetResponse:
    lead_magnet = await _get_lead_magnet_or_404(lead_magnet_id, tenant_id, db)
    return ContentLeadMagnetResponse.model_validate(lead_magnet)


@router.put("/{lead_magnet_id}", response_model=ContentLeadMagnetResponse)
async def update_lead_magnet(
    lead_magnet_id: uuid.UUID,
    body: ContentLeadMagnetUpdate,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ContentLeadMagnetResponse:
    lead_magnet = await _get_lead_magnet_or_404(lead_magnet_id, tenant_id, db)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(lead_magnet, field, value)
    await db.commit()
    await db.refresh(lead_magnet)
    logger.info(
        "content.lead_magnet.updated", lead_magnet_id=str(lead_magnet_id), tenant_id=str(tenant_id)
    )
    return ContentLeadMagnetResponse.model_validate(lead_magnet)


@router.patch("/{lead_magnet_id}/status", response_model=ContentLeadMagnetResponse)
async def update_lead_magnet_status(
    lead_magnet_id: uuid.UUID,
    body: ContentLeadMagnetStatusUpdate,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ContentLeadMagnetResponse:
    lead_magnet = await _get_lead_magnet_or_404(lead_magnet_id, tenant_id, db)
    lead_magnet.status = body.status
    await db.commit()
    await db.refresh(lead_magnet)
    logger.info(
        "content.lead_magnet.status_updated",
        lead_magnet_id=str(lead_magnet_id),
        tenant_id=str(tenant_id),
        status=body.status,
    )
    return ContentLeadMagnetResponse.model_validate(lead_magnet)


@router.get("/{lead_magnet_id}/posts", response_model=list[ContentLMPostResponse])
async def list_lead_magnet_posts(
    lead_magnet_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> list[ContentLMPostResponse]:
    await _get_lead_magnet_or_404(lead_magnet_id, tenant_id, db)
    result = await db.execute(
        select(ContentLMPost)
        .where(
            ContentLMPost.tenant_id == tenant_id,
            ContentLMPost.lead_magnet_id == lead_magnet_id,
        )
        .order_by(ContentLMPost.created_at.desc())
    )
    return [ContentLMPostResponse.model_validate(item) for item in result.scalars().all()]


@router.post(
    "/{lead_magnet_id}/posts",
    response_model=ContentLMPostResponse,
    status_code=status.HTTP_201_CREATED,
)
async def link_post_to_lead_magnet(
    lead_magnet_id: uuid.UUID,
    body: ContentLMPostCreate,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ContentLMPostResponse:
    await _get_lead_magnet_or_404(lead_magnet_id, tenant_id, db)
    if body.content_post_id is not None:
        await _validate_content_post(db, tenant_id=tenant_id, content_post_id=body.content_post_id)

    linked_post = ContentLMPost(
        tenant_id=tenant_id,
        lead_magnet_id=lead_magnet_id,
        **body.model_dump(),
    )
    db.add(linked_post)
    await db.commit()
    await db.refresh(linked_post)
    logger.info(
        "content.lead_magnet.post_linked",
        lead_magnet_id=str(lead_magnet_id),
        tenant_id=str(tenant_id),
    )
    return ContentLMPostResponse.model_validate(linked_post)


@router.get("/{lead_magnet_id}/leads", response_model=list[ContentLMLeadResponse])
async def list_captured_leads(
    lead_magnet_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> list[ContentLMLeadResponse]:
    await _get_lead_magnet_or_404(lead_magnet_id, tenant_id, db)
    result = await db.execute(
        select(ContentLMLead)
        .where(
            ContentLMLead.tenant_id == tenant_id,
            ContentLMLead.lead_magnet_id == lead_magnet_id,
        )
        .order_by(ContentLMLead.created_at.desc())
    )
    return [ContentLMLeadResponse.model_validate(item) for item in result.scalars().all()]


@router.post("/{lead_magnet_id}/leads", response_model=ContentLMLeadResponse)
async def create_manual_lm_lead(
    lead_magnet_id: uuid.UUID,
    body: ContentLMLeadCreate,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ContentLMLeadResponse:
    lead_magnet = await _get_lead_magnet_or_404(lead_magnet_id, tenant_id, db)
    lm_lead, _, should_sync = await upsert_lm_capture(
        db,
        lead_magnet=lead_magnet,
        name=body.name,
        email=body.email,
        origin=body.origin,
        lm_post_id=body.lm_post_id,
        linkedin_profile_url=body.linkedin_profile_url,
        company=body.company,
        role=body.role,
        phone=body.phone,
        capture_metadata=body.capture_metadata,
    )
    await db.commit()
    await db.refresh(lm_lead)
    if should_sync:
        await queue_sendpulse_sync(lm_lead)
    logger.info(
        "content.lead_magnet.lead_captured",
        lead_magnet_id=str(lead_magnet_id),
        lm_lead_id=str(lm_lead.id),
        tenant_id=str(tenant_id),
    )
    return ContentLMLeadResponse.model_validate(lm_lead)


@router.patch(
    "/{lead_magnet_id}/leads/{lm_lead_id}/convert", response_model=ContentLMLeadConvertResponse
)
async def convert_captured_lead(
    lead_magnet_id: uuid.UUID,
    lm_lead_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ContentLMLeadConvertResponse:
    lead_magnet = await _get_lead_magnet_or_404(lead_magnet_id, tenant_id, db)
    lm_lead = await _get_lm_lead_or_404(lm_lead_id, lead_magnet_id, tenant_id, db)
    lead = await convert_lm_lead_to_prospect(
        db,
        lm_lead=lm_lead,
        lead_magnet_title=lead_magnet.title,
        extra_tags=[f"lm_{lead_magnet.type}"],
    )
    await db.commit()
    logger.info(
        "content.lead_magnet.lead_converted",
        lead_magnet_id=str(lead_magnet_id),
        lm_lead_id=str(lm_lead_id),
        lead_id=str(lead.id),
        tenant_id=str(tenant_id),
    )
    return ContentLMLeadConvertResponse(lm_lead_id=lm_lead.id, lead_id=lead.id)


@router.get("/{lead_magnet_id}/metrics", response_model=LeadMagnetMetricsResponse)
async def get_metrics(
    lead_magnet_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> LeadMagnetMetricsResponse:
    await _get_lead_magnet_or_404(lead_magnet_id, tenant_id, db)
    metrics = await get_lead_magnet_metrics(db, tenant_id=tenant_id, lead_magnet_id=lead_magnet_id)
    return LeadMagnetMetricsResponse(**metrics)
