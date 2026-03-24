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
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_effective_tenant_id, get_session_flexible
from models.cadence import Cadence
from models.cadence_step import CadenceStep
from models.enums import LeadSource, LeadStatus
from models.interaction import Interaction
from models.lead import Lead
from schemas.interaction import InteractionListResponse, InteractionResponse
from schemas.lead import (
    LeadCreateRequest,
    LeadEnrollRequest,
    LeadImportRequest,
    LeadImportResponse,
    LeadListResponse,
    LeadResponse,
    LeadStepResponse,
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
    search: Annotated[str | None, Query(max_length=200)] = None,
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
    if search:
        pattern = f"%{search}%"
        query = query.where(
            or_(
                Lead.name.ilike(pattern),
                Lead.company.ilike(pattern),
                Lead.job_title.ilike(pattern),
            )
        )

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
        first_name=body.first_name,
        last_name=body.last_name,
        job_title=body.job_title,
        company=body.company,
        company_domain=body.company_domain,
        website=body.website,
        industry=body.industry,
        company_size=body.company_size,
        linkedin_url=body.linkedin_url,
        city=body.city,
        location=body.location,
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


# ── Steps de cadência (timeline) ──────────────────────────────────────

@router.get("/{lead_id}/steps", response_model=list[LeadStepResponse])
async def list_lead_steps(
    lead_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> list[LeadStepResponse]:
    """Retorna os steps de cadência do lead com dados de interação associados."""
    await _get_lead_or_404(lead_id, tenant_id, db)

    steps_result = await db.execute(
        select(CadenceStep)
        .where(
            CadenceStep.lead_id == lead_id,
            CadenceStep.tenant_id == tenant_id,
        )
        .order_by(CadenceStep.step_number.asc())
    )
    steps = steps_result.scalars().all()

    # Busca interactions outbound/inbound para enriquecer os steps
    interactions_result = await db.execute(
        select(Interaction)
        .where(
            Interaction.lead_id == lead_id,
            Interaction.tenant_id == tenant_id,
        )
        .order_by(Interaction.created_at.asc())
    )
    interactions = interactions_result.scalars().all()

    # Mapear interactions por channel+direction para cada step
    outbound_by_channel: dict[str, list[Interaction]] = {}
    inbound_by_channel: dict[str, list[Interaction]] = {}
    for ix in interactions:
        bucket = outbound_by_channel if ix.direction.value == "outbound" else inbound_by_channel
        bucket.setdefault(ix.channel.value, []).append(ix)

    result: list[LeadStepResponse] = []
    outbound_idx: dict[str, int] = {}
    inbound_idx: dict[str, int] = {}

    for step in steps:
        ch = step.channel.value
        # Match outbound message to step (in order)
        ob_list = outbound_by_channel.get(ch, [])
        ob_i = outbound_idx.get(ch, 0)
        message_content: str | None = None
        if ob_i < len(ob_list):
            message_content = ob_list[ob_i].content_text
            outbound_idx[ch] = ob_i + 1

        # Match inbound reply
        ib_list = inbound_by_channel.get(ch, [])
        ib_i = inbound_idx.get(ch, 0)
        reply_content: str | None = None
        intent: str | None = None
        if ib_i < len(ib_list):
            reply_content = ib_list[ib_i].content_text
            intent = ib_list[ib_i].intent.value if ib_list[ib_i].intent else None
            inbound_idx[ch] = ib_i + 1

        result.append(LeadStepResponse(
            id=step.id,
            lead_id=step.lead_id,
            cadence_id=step.cadence_id,
            step_number=step.step_number,
            channel=ch,
            status=step.status.value,
            use_voice=step.use_voice,
            day_offset=step.day_offset,
            scheduled_at=step.scheduled_at,
            sent_at=step.sent_at,
            message_content=message_content,
            reply_content=reply_content,
            intent=intent,
        ))

    return result


# ── Importação em lote ────────────────────────────────────────────────

@router.post("/import", response_model=LeadImportResponse)
async def import_leads(
    body: LeadImportRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> LeadImportResponse:
    """Importa leads em lote. Deduplica por linkedin_url (quando presente) dentro do tenant."""
    # Busca linkedin_urls já existentes no tenant
    urls = [item.linkedin_url for item in body.items if item.linkedin_url]
    existing_urls: set[str] = set()
    if urls:
        existing_result = await db.execute(
            select(Lead.linkedin_url).where(
                Lead.tenant_id == tenant_id,
                Lead.linkedin_url.in_(urls),
            )
        )
        existing_urls = {row[0] for row in existing_result.all() if row[0]}

    imported = 0
    duplicates = 0
    errors: list[str] = []
    seen_urls: set[str] = set()

    for i, item in enumerate(body.items):
        if item.linkedin_url and (item.linkedin_url in existing_urls or item.linkedin_url in seen_urls):
            duplicates += 1
            continue
        try:
            lead = Lead(
                tenant_id=tenant_id,
                name=item.name,
                first_name=item.first_name,
                last_name=item.last_name,
                job_title=item.job_title,
                company=item.company,
                company_domain=item.company_domain,
                website=item.website,
                industry=item.industry,
                company_size=item.company_size,
                linkedin_url=item.linkedin_url,
                city=item.city,
                location=item.location,
                segment=item.segment,
                phone=item.phone,
                email_corporate=item.email_corporate,
                email_personal=item.email_personal,
                notes=item.notes,
                source=LeadSource.IMPORT,
            )
            db.add(lead)
            if item.linkedin_url:
                seen_urls.add(item.linkedin_url)
            imported += 1
        except Exception as exc:
            errors.append(f"Linha {i + 1}: {exc!s}")

    if imported > 0:
        await db.commit()

    logger.info(
        "leads.imported",
        tenant_id=str(tenant_id),
        imported=imported,
        duplicates=duplicates,
        errors=len(errors),
    )
    return LeadImportResponse(imported=imported, duplicates=duplicates, errors=errors)


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
