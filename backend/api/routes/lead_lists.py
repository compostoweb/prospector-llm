"""
api/routes/lead_lists.py

CRUD de listas de leads + gerenciamento de membros.
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.dependencies import get_current_tenant_flexible as get_current_tenant
from api.dependencies import get_session_flexible as get_session
from models.lead_list import LeadList, lead_list_members
from models.tenant import Tenant
from schemas.lead_list import (
    LeadListCreateRequest,
    LeadListDetailResponse,
    LeadListLeadItem,
    LeadListMembersRequest,
    LeadListResponse,
    LeadListUpdateRequest,
)
from services.cadence_manager import auto_enroll_linked_cadences_for_list
from services.lead_management import load_active_cadences_for_leads

logger = structlog.get_logger()

router = APIRouter(prefix="/lead-lists", tags=["lead-lists"])


def _to_response(ll: LeadList) -> LeadListResponse:
    data = LeadListResponse.model_validate(ll, from_attributes=True)
    data.lead_count = len(ll.leads) if ll.leads else 0
    return data


@router.get("", response_model=list[LeadListResponse])
async def list_lead_lists(
    db: AsyncSession = Depends(get_session),
    tenant: Tenant = Depends(get_current_tenant),
) -> list[LeadListResponse]:
    result = await db.execute(
        select(LeadList)
        .where(LeadList.tenant_id == tenant.id)
        .options(selectinload(LeadList.leads))
        .order_by(LeadList.created_at.desc())
    )
    lists = result.scalars().all()
    return [_to_response(ll) for ll in lists]


@router.post("", response_model=LeadListResponse, status_code=status.HTTP_201_CREATED)
async def create_lead_list(
    body: LeadListCreateRequest,
    db: AsyncSession = Depends(get_session),
    tenant: Tenant = Depends(get_current_tenant),
) -> LeadListResponse:
    ll = LeadList(
        tenant_id=tenant.id,
        name=body.name,
        description=body.description,
    )
    db.add(ll)
    await db.commit()
    await db.refresh(ll, attribute_names=["leads"])
    logger.info("lead_list.created", list_id=str(ll.id), tenant_id=str(tenant.id))
    return _to_response(ll)


@router.get("/{list_id}", response_model=LeadListDetailResponse)
async def get_lead_list(
    list_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    tenant: Tenant = Depends(get_current_tenant),
) -> LeadListDetailResponse:
    result = await db.execute(
        select(LeadList)
        .where(LeadList.id == list_id, LeadList.tenant_id == tenant.id)
        .options(selectinload(LeadList.leads))
    )
    ll = result.scalar_one_or_none()
    if not ll:
        raise HTTPException(status_code=404, detail="Lista não encontrada")
    active_cadences_by_lead = await load_active_cadences_for_leads(
        db,
        tenant_id=tenant.id,
        lead_ids=[lead.id for lead in (ll.leads or [])],
    )
    leads_items: list[LeadListLeadItem] = []
    for lead in ll.leads or []:
        item_data = LeadListLeadItem.model_validate(lead).model_dump()
        active_cadences = active_cadences_by_lead.get(lead.id, [])
        item_data["active_cadence_count"] = len(active_cadences)
        item_data["active_cadences"] = [
            {"id": cadence.id, "name": cadence.name} for cadence in active_cadences
        ]
        item_data["has_multiple_active_cadences"] = len(active_cadences) > 1
        leads_items.append(LeadListLeadItem(**item_data))
    data = LeadListDetailResponse.model_validate(ll, from_attributes=True)
    data.lead_count = len(leads_items)
    data.leads = leads_items
    return data


@router.put("/{list_id}", response_model=LeadListResponse)
async def update_lead_list(
    list_id: uuid.UUID,
    body: LeadListUpdateRequest,
    db: AsyncSession = Depends(get_session),
    tenant: Tenant = Depends(get_current_tenant),
) -> LeadListResponse:
    result = await db.execute(
        select(LeadList)
        .where(LeadList.id == list_id, LeadList.tenant_id == tenant.id)
        .options(selectinload(LeadList.leads))
    )
    ll = result.scalar_one_or_none()
    if not ll:
        raise HTTPException(status_code=404, detail="Lista não encontrada")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(ll, key, value)

    await db.commit()
    await db.refresh(ll, attribute_names=["leads"])
    return _to_response(ll)


@router.delete("/{list_id}")
async def delete_lead_list(
    list_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    tenant: Tenant = Depends(get_current_tenant),
) -> Response:
    result = await db.execute(
        select(LeadList).where(LeadList.id == list_id, LeadList.tenant_id == tenant.id)
    )
    ll = result.scalar_one_or_none()
    if not ll:
        raise HTTPException(status_code=404, detail="Lista não encontrada")
    await db.delete(ll)
    await db.commit()
    logger.info("lead_list.deleted", list_id=str(list_id), tenant_id=str(tenant.id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{list_id}/members")
async def add_members(
    list_id: uuid.UUID,
    body: LeadListMembersRequest,
    db: AsyncSession = Depends(get_session),
    tenant: Tenant = Depends(get_current_tenant),
) -> Response:
    result = await db.execute(
        select(LeadList).where(LeadList.id == list_id, LeadList.tenant_id == tenant.id)
    )
    ll = result.scalar_one_or_none()
    if not ll:
        raise HTTPException(status_code=404, detail="Lista não encontrada")

    # Usar INSERT ... ON CONFLICT DO NOTHING para idempotência
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    for lead_id in body.lead_ids:
        stmt = (
            pg_insert(lead_list_members)
            .values(lead_list_id=list_id, lead_id=lead_id)
            .on_conflict_do_nothing()
        )
        await db.execute(stmt)

    enrolled_count = await auto_enroll_linked_cadences_for_list(
        db,
        list_id=list_id,
        lead_ids=list(body.lead_ids),
    )
    await db.commit()
    logger.info(
        "lead_list.members_added",
        list_id=str(list_id),
        count=len(body.lead_ids),
        enrolled_in_cadences=enrolled_count,
        tenant_id=str(tenant.id),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{list_id}/members")
async def remove_members(
    list_id: uuid.UUID,
    body: LeadListMembersRequest,
    db: AsyncSession = Depends(get_session),
    tenant: Tenant = Depends(get_current_tenant),
) -> Response:
    result = await db.execute(
        select(LeadList).where(LeadList.id == list_id, LeadList.tenant_id == tenant.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Lista não encontrada")

    await db.execute(
        delete(lead_list_members).where(
            lead_list_members.c.lead_list_id == list_id,
            lead_list_members.c.lead_id.in_(body.lead_ids),
        )
    )
    await db.commit()
    logger.info(
        "lead_list.members_removed",
        list_id=str(list_id),
        count=len(body.lead_ids),
        tenant_id=str(tenant.id),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
