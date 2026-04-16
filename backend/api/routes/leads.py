"""
api/routes/leads.py

Rotas REST para gerenciamento de leads.

Endpoints:
  GET    /leads              — listagem paginada (filtros: status, source, min_score)
  POST   /leads              — criação manual + enrich opcional
  GET    /leads/{id}         — detalhes
  PATCH  /leads/{id}         — atualização parcial
  DELETE /leads/{id}         — arquiva (status=ARCHIVED, não apaga)
    POST   /leads/{id}/enrich  — dispara enriquecimento manual
  POST   /leads/{id}/enroll  — inscreve em cadência
  GET    /leads/{id}/interactions — histórico de interações paginado
"""

from __future__ import annotations

import uuid
from importlib import import_module
from typing import Annotated, Any, cast

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.dependencies import get_effective_tenant_id, get_session_flexible
from models.cadence import Cadence
from models.cadence_step import CadenceStep
from models.enums import LeadSource, LeadStatus
from models.interaction import Interaction
from models.lead import Lead
from models.lead_list import LeadList
from schemas.interaction import InteractionListResponse, InteractionResponse
from schemas.lead import (
    LeadCreateRequest,
    LeadEnrollRequest,
    LeadGenerationImportRequest,
    LeadGenerationImportResponse,
    LeadGenerationPreviewRequest,
    LeadGenerationPreviewResponse,
    LeadImportRequest,
    LeadImportResponse,
    LeadListResponse,
    LeadMergeRequest,
    LeadMergeResponse,
    LeadResponse,
    LeadStepResponse,
    LeadUpdateRequest,
)
from services.cadence_manager import CadenceManager
from services.lead_generation import preview_generated_leads
from services.lead_management import (
    additional_lead_email_specs,
    apply_candidate_to_lead,
    build_lead_email_specs,
    delete_lead_permanently,
    ensure_list_membership,
    find_existing_lead,
    get_lead_with_lists,
    get_or_create_list,
    merge_leads,
    replace_lead_email_records,
    serialize_lead,
)
from services.lead_scorer import lead_scorer

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
    min_score: Annotated[float | None, Query(ge=0.0, le=100.0)] = None,
    score_min: Annotated[float | None, Query(alias="score_min", ge=0.0, le=100.0)] = None,
    score_max: Annotated[float | None, Query(alias="score_max", ge=0.0, le=100.0)] = None,
    cadence_id: uuid.UUID | None = Query(default=None),
    list_id: uuid.UUID | None = Query(default=None),
    segment: Annotated[str | None, Query(max_length=200)] = None,
    search: Annotated[str | None, Query(max_length=200)] = None,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> LeadListResponse:
    query = (
        select(Lead)
        .where(Lead.tenant_id == tenant_id)
        .options(selectinload(Lead.lists), selectinload(Lead.emails))
    )  # type: ignore[arg-type]
    effective_min_score = score_min if score_min is not None else min_score

    if status_filter is not None:
        query = query.where(Lead.status == status_filter)
    if source_filter is not None:
        query = query.where(Lead.source == source_filter)
    if effective_min_score is not None:
        query = query.where(Lead.score >= effective_min_score)
    if score_max is not None:
        query = query.where(Lead.score <= score_max)
    if cadence_id is not None:
        enrolled_subquery = (
            select(CadenceStep.lead_id)
            .where(
                CadenceStep.tenant_id == tenant_id,
                CadenceStep.cadence_id == cadence_id,
            )
            .distinct()
        )
        query = query.where(Lead.id.in_(enrolled_subquery))
    if list_id is not None:
        query = query.where(Lead.lists.any(LeadList.id == list_id))
    if segment:
        query = query.where(Lead.segment.ilike(f"%{segment}%"))
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
    result = await db.execute(
        query.order_by(Lead.created_at.desc()).offset(offset).limit(page_size)
    )
    leads = result.scalars().all()

    return LeadListResponse(
        items=[serialize_lead(lead) for lead in leads],
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
    await db.flush()
    await replace_lead_email_records(
        db,
        lead=lead,
        specs=build_lead_email_specs(
            email_corporate=body.email_corporate,
            email_personal=body.email_personal,
            extra_emails=body.emails,
        ),
    )
    lead.score = float(lead_scorer.score(lead))
    await db.commit()
    await db.refresh(lead)

    logger.info("lead.created", lead_id=str(lead.id), tenant_id=str(tenant_id))

    if enrich:
        enrichment_task = import_module("workers.enrich").enrich_lead
        enrichment_task.delay(str(lead.id), str(tenant_id))
        logger.info("lead.enrich_queued", lead_id=str(lead.id))

    lead_with_lists = await get_lead_with_lists(lead.id, tenant_id, db)
    if lead_with_lists is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead não encontrado.")
    return serialize_lead(lead_with_lists)


# ── LinkedIn search params (DEVE vir antes de /{lead_id}) ────────────


@router.get("/linkedin-search-params", response_model=dict)
async def linkedin_search_params(
    type: Annotated[str, Query(description="LOCATION | INDUSTRY | COMPANY")],
    query: Annotated[str, Query(description="Texto para busca (obrigatório para COMPANY)")] = "",
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> dict[str, object]:
    """
    Faz lookup de IDs de localização, setor ou empresa no LinkedIn via Unipile.
    Necessário para usar os filtros nativos do LinkedIn Search.
    Para COMPANY, o parâmetro `query` é obrigatório (ex: ?type=COMPANY&query=Petrobras).
    """
    from core.config import settings
    from models.tenant import TenantIntegration

    integ_result = await db.execute(
        select(TenantIntegration).where(TenantIntegration.tenant_id == tenant_id)
    )
    integration = integ_result.scalar_one_or_none()
    linkedin_account_id = (
        (integration and integration.unipile_linkedin_account_id)
        or settings.UNIPILE_ACCOUNT_ID_LINKEDIN
        or ""
    )
    if not linkedin_account_id:
        logger.warning(
            "linkedin_search_params.no_account_id",
            tenant_id=str(tenant_id),
            integration_found=integration is not None,
        )
        return {"items": []}
    from integrations.unipile_client import unipile_client

    logger.debug(
        "linkedin_search_params.calling_unipile",
        param_type=type,
        query=query,
        account_id=linkedin_account_id[:8] + "...",
    )
    return cast(
        dict[str, object],
        await cast(Any, unipile_client).search_linkedin_params(
            account_id=linkedin_account_id,
            param_type=type,
            query=query,
        ),
    )


# ── Detalhes ──────────────────────────────────────────────────────────


@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(
    lead_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> LeadResponse:
    lead = await _get_lead_or_404(lead_id, tenant_id, db)
    return serialize_lead(lead)


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
    email_updates = updates.pop("emails", None)
    for field, value in updates.items():
        setattr(lead, field, value)

    if email_updates is not None:
        await replace_lead_email_records(
            db,
            lead=lead,
            specs=build_lead_email_specs(
                email_corporate=lead.email_corporate,
                email_corporate_source=lead.email_corporate_source,
                email_corporate_verified=lead.email_corporate_verified,
                email_personal=lead.email_personal,
                email_personal_source=lead.email_personal_source,
                extra_emails=email_updates,
            ),
        )
    elif "email_corporate" in updates or "email_personal" in updates:
        await replace_lead_email_records(
            db,
            lead=lead,
            specs=build_lead_email_specs(
                email_corporate=lead.email_corporate,
                email_corporate_source=lead.email_corporate_source,
                email_corporate_verified=lead.email_corporate_verified,
                email_personal=lead.email_personal,
                email_personal_source=lead.email_personal_source,
                extra_emails=additional_lead_email_specs(lead),
            ),
        )

    if _should_recalculate_score(updates) or email_updates is not None:
        lead.score = float(lead_scorer.score(lead))

    await db.commit()
    lead = await _get_lead_or_404(lead_id, tenant_id, db)

    logger.info("lead.updated", lead_id=str(lead_id), fields=list(updates.keys()))
    return serialize_lead(lead)


@router.post("/{lead_id}/enrich")
async def enrich_lead_manually(
    lead_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> dict[str, str]:
    lead = await _get_lead_or_404(lead_id, tenant_id, db)
    enrichment_task = import_module("workers.enrich").enrich_lead
    enrichment_task.delay(str(lead.id), str(tenant_id))
    logger.info("lead.enrich_queued", lead_id=str(lead.id), tenant_id=str(tenant_id))
    return {"status": "queued", "lead_id": str(lead.id)}


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


@router.delete("/{lead_id}/permanent", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def hard_delete_lead(
    lead_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> None:
    lead = await _get_lead_or_404(lead_id, tenant_id, db)
    await delete_lead_permanently(db, lead=lead)
    logger.info("lead.deleted_permanently", lead_id=str(lead_id), tenant_id=str(tenant_id))


@router.post("/merge", response_model=LeadMergeResponse)
async def merge_selected_leads(
    body: LeadMergeRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> LeadMergeResponse:
    if body.primary_lead_id in body.secondary_lead_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="O lead principal não pode aparecer na lista de leads mesclados.",
        )

    primary = await get_lead_with_lists(body.primary_lead_id, tenant_id, db)
    if primary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lead principal não encontrado."
        )

    merged_lead = await merge_leads(
        db,
        tenant_id=tenant_id,
        primary_lead_id=body.primary_lead_id,
        secondary_lead_ids=body.secondary_lead_ids,
    )
    logger.info(
        "lead.merged",
        lead_id=str(body.primary_lead_id),
        merged_count=len(body.secondary_lead_ids),
        tenant_id=str(tenant_id),
    )
    return LeadMergeResponse(
        lead=serialize_lead(merged_lead),
        merged_lead_ids=body.secondary_lead_ids,
    )


# ── Enrollment em cadência ────────────────────────────────────────────


@router.post("/{lead_id}/enroll", response_model=dict[str, Any], status_code=status.HTTP_200_OK)
async def enroll_lead(
    lead_id: uuid.UUID,
    body: LeadEnrollRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> dict[str, Any]:
    lead = await _get_lead_or_404(lead_id, tenant_id, db)

    if lead.status == LeadStatus.ARCHIVED:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Lead arquivado não pode ser inscrito em cadência.",
        )

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
            current_interaction = ib_list[ib_i]
            reply_content = current_interaction.content_text
            interaction_intent = current_interaction.intent
            intent = interaction_intent.value if interaction_intent is not None else None
            inbound_idx[ch] = ib_i + 1

        result.append(
            LeadStepResponse(
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
            )
        )

    return result


# ── Importação em lote ────────────────────────────────────────────────


@router.post("/import", response_model=LeadImportResponse)
async def import_leads(
    body: LeadImportRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> LeadImportResponse:
    """Importa leads em lote. Deduplica por linkedin_url e website dentro do tenant."""
    # Pré-carrega linkedin_urls e websites existentes para dedup em lote
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

    websites = [item.website for item in body.items if item.website]
    existing_websites: set[str] = set()
    if websites:
        ws_result = await db.execute(
            select(Lead.website).where(
                Lead.tenant_id == tenant_id,
                Lead.website.in_(websites),
            )
        )
        existing_websites = {row[0] for row in ws_result.all() if row[0]}

    # Cria ou resolve a lista de destino
    target_list_id: uuid.UUID | None = None
    if body.list_name:
        target_list = await get_or_create_list(db, tenant_id=tenant_id, list_name=body.list_name)
        await db.flush()
        target_list_id = target_list.id
    elif body.list_id:
        list_result = await db.execute(
            select(LeadList).where(
                LeadList.id == body.list_id,
                LeadList.tenant_id == tenant_id,
            )
        )
        found_list = list_result.scalar_one_or_none()
        if found_list is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lista não encontrada.",
            )
        target_list_id = found_list.id

    imported = 0
    duplicates = 0
    errors: list[str] = []
    seen_urls: set[str] = set()
    seen_websites: set[str] = set()
    imported_lead_ids: list[uuid.UUID] = []

    for i, item in enumerate(body.items):
        # Dedup por linkedin_url
        if item.linkedin_url and (
            item.linkedin_url in existing_urls or item.linkedin_url in seen_urls
        ):
            duplicates += 1
            continue
        # Dedup por website
        if item.website and (item.website in existing_websites or item.website in seen_websites):
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
            await db.flush()
            if item.linkedin_url:
                seen_urls.add(item.linkedin_url)
            if item.website:
                seen_websites.add(item.website)
            imported_lead_ids.append(lead.id)
            imported += 1
        except Exception as exc:
            errors.append(f"Linha {i + 1}: {exc!s}")

    # Associa à lista se solicitado
    if target_list_id and imported_lead_ids:
        from models.lead_list import lead_list_members as llm_table

        await db.execute(
            llm_table.insert().values(
                [{"lead_list_id": target_list_id, "lead_id": lid} for lid in imported_lead_ids]
            )
        )

    if imported > 0:
        await db.commit()

    logger.info(
        "leads.imported",
        tenant_id=str(tenant_id),
        imported=imported,
        duplicates=duplicates,
        errors=len(errors),
        list_id=str(target_list_id) if target_list_id else None,
    )
    return LeadImportResponse(
        imported=imported,
        duplicates=duplicates,
        errors=errors,
        list_id=target_list_id,
    )


@router.post("/generate-preview", response_model=LeadGenerationPreviewResponse)
async def generate_leads_preview(
    body: LeadGenerationPreviewRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> LeadGenerationPreviewResponse:
    del tenant_id, db
    try:
        items = await preview_generated_leads(body)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return LeadGenerationPreviewResponse(source=body.source, items=items, total=len(items))


@router.post(
    "/generate-import",
    response_model=LeadGenerationImportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_leads_import(
    body: LeadGenerationImportRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> LeadGenerationImportResponse:
    target_list = await get_or_create_list(
        db,
        tenant_id=tenant_id,
        list_id=body.list_id,
        create_list_name=body.create_list_name,
    )
    if body.list_id and target_list is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lista não encontrada.")

    created = 0
    updated = 0
    duplicates = 0
    lead_ids: list[uuid.UUID] = []

    for item in body.items:
        existing = await find_existing_lead(db, tenant_id, item)
        if existing is not None:
            duplicates += 1
            if body.merge_duplicates:
                apply_candidate_to_lead(
                    existing, item, source=body.source, overwrite_missing_only=True
                )
                await replace_lead_email_records(
                    db,
                    lead=existing,
                    specs=build_lead_email_specs(
                        email_corporate=existing.email_corporate,
                        email_corporate_source=existing.email_corporate_source,
                        email_corporate_verified=existing.email_corporate_verified,
                        email_personal=existing.email_personal,
                        email_personal_source=existing.email_personal_source,
                        extra_emails=additional_lead_email_specs(existing),
                    ),
                )
                updated += 1
                if existing.id not in lead_ids:
                    lead_ids.append(existing.id)
            if target_list is not None:
                await ensure_list_membership(db, lead_id=existing.id, list_id=target_list.id)
            continue

        lead = Lead(
            tenant_id=tenant_id,
            name=item.name,
            source=item.source,
            status=LeadStatus.RAW,
        )
        apply_candidate_to_lead(lead, item, source=body.source, overwrite_missing_only=False)
        db.add(lead)
        await db.flush()
        await replace_lead_email_records(
            db,
            lead=lead,
            specs=build_lead_email_specs(
                email_corporate=lead.email_corporate,
                email_corporate_source=lead.email_corporate_source,
                email_corporate_verified=lead.email_corporate_verified,
                email_personal=lead.email_personal,
                email_personal_source=lead.email_personal_source,
            ),
        )
        if target_list is not None:
            await ensure_list_membership(db, lead_id=lead.id, list_id=target_list.id)
        lead_ids.append(lead.id)
        created += 1

    await db.commit()
    logger.info(
        "lead_generation.imported",
        source=body.source,
        tenant_id=str(tenant_id),
        created=created,
        updated=updated,
        duplicates=duplicates,
        list_id=str(target_list.id) if target_list else None,
    )
    return LeadGenerationImportResponse(
        created=created,
        updated=updated,
        duplicates=duplicates,
        list_id=target_list.id if target_list else None,
        lead_ids=lead_ids,
    )


# ── LinkedIn Search ───────────────────────────────────────────────────

from pydantic import BaseModel as _BaseModel  # noqa: E402


class LinkedInSearchRequest(_BaseModel):
    keywords: str
    # filtros multi-valor (mapeiam para o schema Unipile Classic - People)
    titles: list[str] | None = None  # advanced_keywords.title (OR-joined)
    companies: list[str] | None = None  # advanced_keywords.company texto livre (OR-joined)
    company_ids: list[str] | None = None  # IDs nativos do LinkedIn (filtro COMPANY nativo)
    location_ids: list[str] | None = None  # IDs numéricos do lookup /linkedin-search-params
    industry_ids: list[str] | None = None  # IDs numéricos do lookup /linkedin-search-params
    network_distance: list[int] | None = None  # [1=1º, 2=2º, 3=3º+]
    limit: int = 25
    cursor: str | None = None


class LinkedInImportRequest(_BaseModel):
    profiles: list[dict[str, object]]
    list_id: uuid.UUID | None = None


@router.post("/search-linkedin", response_model=dict)
async def search_linkedin(
    body: LinkedInSearchRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> dict[str, object]:
    """
    Busca perfis LinkedIn via Unipile.
    Não importa — apenas retorna os resultados para preview.
    """
    from core.config import settings
    from models.tenant import TenantIntegration
    from services.linkedin_search_service import search_linkedin_profiles

    integ_result = await db.execute(
        select(TenantIntegration).where(TenantIntegration.tenant_id == tenant_id)
    )
    integration = integ_result.scalar_one_or_none()
    linkedin_account_id = (
        (integration and integration.unipile_linkedin_account_id)
        or settings.UNIPILE_ACCOUNT_ID_LINKEDIN
        or ""
    )

    if not linkedin_account_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Conta LinkedIn não configurada para este tenant.",
        )

    result = cast(
        dict[str, object],
        await search_linkedin_profiles(
            account_id=linkedin_account_id,
            keywords=body.keywords,
            titles=body.titles,
            companies=body.companies,
            company_ids=body.company_ids,
            location_ids=body.location_ids,
            industry_ids=body.industry_ids,
            network_distance=body.network_distance,
            limit=body.limit,
            cursor=body.cursor,
        ),
    )
    return result


@router.post("/import-linkedin", response_model=dict, status_code=status.HTTP_201_CREATED)
async def import_linkedin(
    body: LinkedInImportRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> dict[str, object]:
    """
    Importa perfis selecionados do LinkedIn como leads (source=linkedin_search).
    Deduplica por linkedin_profile_id dentro do tenant.
    """
    from services.linkedin_search_service import import_linkedin_profiles

    return cast(
        dict[str, object],
        await import_linkedin_profiles(
            profiles=body.profiles,
            tenant_id=tenant_id,
            list_id=body.list_id,
            db=db,
        ),
    )


class _LinkedInEnrichRequest(_BaseModel):
    provider_ids: list[str]


@router.post("/linkedin-enrich-companies", response_model=dict)
async def linkedin_enrich_companies(
    body: _LinkedInEnrichRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> dict[str, object]:
    """
    Para cada provider_id fornecido, busca a empresa atual do perfil LinkedIn
    via GET /users/{id}?linkedin_sections=experience (concorrente, máx 5).
    Retorna {"results": [{"provider_id": "...", "company": "..."}]}.
    """
    import asyncio

    from core.config import settings
    from models.tenant import TenantIntegration

    integ_result = await db.execute(
        select(TenantIntegration).where(TenantIntegration.tenant_id == tenant_id)
    )
    integration = integ_result.scalar_one_or_none()
    account_id = (
        (integration and integration.unipile_linkedin_account_id)
        or settings.UNIPILE_ACCOUNT_ID_LINKEDIN
        or ""
    )
    if not account_id:
        logger.warning("linkedin_enrich_companies.no_account_id", tenant_id=str(tenant_id))
        return {"results": []}

    from integrations.unipile_client import unipile_client

    # Limitar a 25 perfis por chamada; semáforo de 5 concorrentes
    ids = body.provider_ids[:25]
    sem = asyncio.Semaphore(5)

    async def fetch_one(pid: str) -> dict[str, object]:
        async with sem:
            company = await cast(Any, unipile_client).fetch_profile_company(account_id, pid)
            return {"provider_id": pid, "company": company}

    raw = await asyncio.gather(*[fetch_one(pid) for pid in ids], return_exceptions=True)
    results = [r for r in raw if isinstance(r, dict)]
    logger.info(
        "linkedin_enrich_companies.done",
        requested=len(ids),
        returned=len(results),
        tenant_id=str(tenant_id),
    )
    return {"results": results}


# ── Helper ────────────────────────────────────────────────────────────


async def _get_lead_or_404(
    lead_id: uuid.UUID,
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> Lead:
    lead = await get_lead_with_lists(lead_id, tenant_id, db)
    if lead is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead não encontrado.",
        )
    return lead


def _should_recalculate_score(updates: dict[str, Any]) -> bool:
    score_fields = {
        "linkedin_url",
        "company",
        "website",
        "phone",
        "segment",
        "city",
        "email_corporate",
        "email_personal",
        "emails",
    }
    return any(field in updates for field in score_fields)
