"""
api/routes/lead_lists.py

CRUD de listas de leads + gerenciamento de membros.
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.dependencies import get_current_tenant_flexible as get_current_tenant, get_session_flexible as get_session
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
    leads_items = [LeadListLeadItem.model_validate(lead) for lead in (ll.leads or [])]
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
    await db.commit()
    logger.info(
        "lead_list.members_added",
        list_id=str(list_id),
        count=len(body.lead_ids),
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
