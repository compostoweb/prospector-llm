"""
api/routes/content/references.py

Posts de referencia de alta performance para uso como few-shot no LLM.

GET    /content/references      — listar
POST   /content/references      — adicionar
DELETE /content/references/{id} — remover
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_effective_tenant_id, get_session_flexible
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
        .order_by(ContentReference.engagement_score.desc().nulls_last(), ContentReference.created_at.desc())
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Referencia nao encontrada")
    await db.delete(ref)
    await db.commit()
    logger.info("content.reference_deleted", reference_id=str(reference_id), tenant_id=str(tenant_id))
