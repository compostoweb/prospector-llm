"""
api/routes/leads.py

Rotas REST para gerenciamento de leads.

Endpoints:
  GET    /leads              — listagem paginada (filtros: status, source, min_score)
  POST   /leads              — criação manual + enrich opcional
  GET    /leads/{id}         — detalhes
  PATCH  /leads/{id}         — atualização parcial
  DELETE /leads/{id}         — arquiva (status=ARCHIVED, não apaga)
  POST   /leads/{id}/enroll  — inscreve em cadência
  GET    /leads/{id}/interactions — histórico de interações paginado
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_effective_tenant_id, get_session_flexible
from models.cadence import Cadence
from models.enums import LeadSource, LeadStatus
from models.interaction import Interaction
from models.lead import Lead
from schemas.interaction import InteractionListResponse, InteractionResponse
from schemas.lead import (
    LeadCreateRequest,
    LeadEnrollRequest,
    LeadListResponse,
    LeadResponse,
    LeadUpdateRequest,
)
from services.cadence_manager import CadenceManager
from workers.enrich import enrich_lead

logger = structlog.get_logger()

router = APIRouter(prefix="/leads", tags=["Leads"])

_cadence_manager = CadenceManager()


# ── Listagem paginada ─────────────────────────────────────────────────

@router.get("", response_model=LeadListResponse)
async def list_leads(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status_filter: Annotated[LeadStatus | None, Query(alias="status")] = None,
    source_filter: Annotated[LeadSource | None, Query(alias="source")] = None,
    min_score: Annotated[float | None, Query(ge=0.0, le=1.0)] = None,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> LeadListResponse:
    query = select(Lead).where(Lead.tenant_id == tenant_id)

    if status_filter is not None:
        query = query.where(Lead.status == status_filter)
    if source_filter is not None:
        query = query.where(Lead.source == source_filter)
    if min_score is not None:
        query = query.where(Lead.score >= min_score)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(query.order_by(Lead.created_at.desc()).offset(offset).limit(page_size))
    leads = result.scalars().all()

    return LeadListResponse(
        items=[LeadResponse.model_validate(lead) for lead in leads],
        total=total,
        page=page,
        page_size=page_size,
    )


# ── Criação ───────────────────────────────────────────────────────────

@router.post("", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
async def create_lead(
    body: LeadCreateRequest,
    enrich: Annotated[bool, Query()] = False,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> LeadResponse:
    # Verifica duplicidade por linkedin_url se fornecido
    if body.linkedin_url:
        existing = await db.execute(
            select(Lead).where(
                Lead.tenant_id == tenant_id,
                Lead.linkedin_url == body.linkedin_url,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Lead com este LinkedIn já existe para este tenant.",
            )

    lead = Lead(
        tenant_id=tenant_id,
        name=body.name,
        company=body.company,
        website=body.website,
        linkedin_url=body.linkedin_url,
        city=body.city,
        segment=body.segment,
        phone=body.phone,
        email_corporate=body.email_corporate,
        email_personal=body.email_personal,
        notes=body.notes,
        source=body.source,
    )
    db.add(lead)
    await db.commit()
    await db.refresh(lead)

    logger.info("lead.created", lead_id=str(lead.id), tenant_id=str(tenant_id))

    if enrich:
        enrich_lead.delay(str(lead.id), str(tenant_id))
        logger.info("lead.enrich_queued", lead_id=str(lead.id))

    return LeadResponse.model_validate(lead)


# ── Detalhes ──────────────────────────────────────────────────────────

@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(
    lead_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> LeadResponse:
    lead = await _get_lead_or_404(lead_id, tenant_id, db)
    return LeadResponse.model_validate(lead)


# ── Atualização parcial ───────────────────────────────────────────────

@router.patch("/{lead_id}", response_model=LeadResponse)
async def update_lead(
    lead_id: uuid.UUID,
    body: LeadUpdateRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> LeadResponse:
    lead = await _get_lead_or_404(lead_id, tenant_id, db)

    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(lead, field, value)

    await db.commit()
    await db.refresh(lead)

    logger.info("lead.updated", lead_id=str(lead_id), fields=list(updates.keys()))
    return LeadResponse.model_validate(lead)


# ── Arquivamento ──────────────────────────────────────────────────────

@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def archive_lead(
    lead_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> None:
    lead = await _get_lead_or_404(lead_id, tenant_id, db)
    lead.status = LeadStatus.ARCHIVED
    await db.commit()
    logger.info("lead.archived", lead_id=str(lead_id))


# ── Enrollment em cadência ────────────────────────────────────────────

@router.post("/{lead_id}/enroll", response_model=dict[str, Any], status_code=status.HTTP_200_OK)
async def enroll_lead(
    lead_id: uuid.UUID,
    body: LeadEnrollRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> dict[str, Any]:
    lead = await _get_lead_or_404(lead_id, tenant_id, db)

    # Verifica se a cadência pertence ao tenant
    cadence_result = await db.execute(
        select(Cadence).where(
            Cadence.id == body.cadence_id,
            Cadence.tenant_id == tenant_id,
            Cadence.is_active.is_(True),
        )
    )
    cadence = cadence_result.scalar_one_or_none()
    if cadence is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cadência não encontrada ou inativa.",
        )

    if lead.status == LeadStatus.ARCHIVED:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Lead arquivado não pode ser inscrito em cadência.",
        )

    try:
        steps = await _cadence_manager.enroll(lead, cadence, db)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    logger.info(
        "lead.enrolled",
        lead_id=str(lead_id),
        cadence_id=str(body.cadence_id),
        steps=len(steps),
    )
    return {"enrolled": True, "steps_created": len(steps)}


# ── Histórico de interações ───────────────────────────────────────────

@router.get("/{lead_id}/interactions", response_model=InteractionListResponse)
async def list_lead_interactions(
    lead_id: uuid.UUID,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> InteractionListResponse:
    await _get_lead_or_404(lead_id, tenant_id, db)  # garante 404 se não existir

    query = select(Interaction).where(
        Interaction.lead_id == lead_id,
        Interaction.tenant_id == tenant_id,
    )

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(Interaction.created_at.desc()).offset(offset).limit(page_size)
    )
    interactions = result.scalars().all()

    return InteractionListResponse(
        items=[InteractionResponse.model_validate(i) for i in interactions],
        total=total,
    )


# ── Helper ────────────────────────────────────────────────────────────

async def _get_lead_or_404(
    lead_id: uuid.UUID,
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> Lead:
    result = await db.execute(
        select(Lead).where(Lead.id == lead_id, Lead.tenant_id == tenant_id)
    )
    lead = result.scalar_one_or_none()
    if lead is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead não encontrado.",
        )
    return lead
