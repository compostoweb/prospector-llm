"""
api/routes/cadences.py

Rotas REST para gerenciamento de cadências de prospecção.

Endpoints:
  GET    /cadences            — listagem (todas as cadências do tenant)
  POST   /cadences            — criação
  GET    /cadences/{id}       — detalhes
  PATCH  /cadences/{id}       — atualização parcial
  DELETE /cadences/{id}       — desativa (is_active=False, não apaga)
"""

from __future__ import annotations

import uuid
from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_current_tenant_id, get_session
from models.cadence import Cadence
from schemas.cadence import CadenceCreateRequest, CadenceUpdateRequest

logger = structlog.get_logger()

router = APIRouter(prefix="/cadences", tags=["Cadences"])


# ── Schema de resposta (definido aqui pois é acoplado às rotas) ───────

class CadenceResponse(BaseModel):
    """Representação completa de uma cadência na API."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str | None
    is_active: bool
    allow_personal_email: bool
    llm_provider: str
    llm_model: str
    llm_temperature: float
    llm_max_tokens: int
    created_at: datetime
    updated_at: datetime


# ── Listagem ──────────────────────────────────────────────────────────

@router.get("", response_model=list[CadenceResponse])
async def list_cadences(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_session),
) -> list[CadenceResponse]:
    result = await db.execute(
        select(Cadence)
        .where(Cadence.tenant_id == tenant_id)
        .order_by(Cadence.created_at.desc())
    )
    cadences = result.scalars().all()
    return [CadenceResponse.model_validate(c) for c in cadences]


# ── Criação ───────────────────────────────────────────────────────────

@router.post("", response_model=CadenceResponse, status_code=status.HTTP_201_CREATED)
async def create_cadence(
    body: CadenceCreateRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_session),
) -> CadenceResponse:
    cadence = Cadence(
        tenant_id=tenant_id,
        name=body.name,
        description=body.description,
        allow_personal_email=body.allow_personal_email,
        llm_provider=body.llm.provider,
        llm_model=body.llm.model,
        llm_temperature=body.llm.temperature,
        llm_max_tokens=body.llm.max_tokens,
    )
    db.add(cadence)
    await db.commit()
    await db.refresh(cadence)

    logger.info("cadence.created", cadence_id=str(cadence.id), tenant_id=str(tenant_id))
    return CadenceResponse.model_validate(cadence)


# ── Detalhes ──────────────────────────────────────────────────────────

@router.get("/{cadence_id}", response_model=CadenceResponse)
async def get_cadence(
    cadence_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_session),
) -> CadenceResponse:
    cadence = await _get_cadence_or_404(cadence_id, tenant_id, db)
    return CadenceResponse.model_validate(cadence)


# ── Atualização parcial ───────────────────────────────────────────────

@router.patch("/{cadence_id}", response_model=CadenceResponse)
async def update_cadence(
    cadence_id: uuid.UUID,
    body: CadenceUpdateRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_session),
) -> CadenceResponse:
    cadence = await _get_cadence_or_404(cadence_id, tenant_id, db)

    updates = body.model_dump(exclude_unset=True, exclude={"llm"})
    for field, value in updates.items():
        setattr(cadence, field, value)

    if body.llm is not None:
        cadence.llm_provider = body.llm.provider
        cadence.llm_model = body.llm.model
        cadence.llm_temperature = body.llm.temperature
        cadence.llm_max_tokens = body.llm.max_tokens

    await db.commit()
    await db.refresh(cadence)

    logger.info("cadence.updated", cadence_id=str(cadence_id))
    return CadenceResponse.model_validate(cadence)


# ── Desativação ───────────────────────────────────────────────────────

@router.delete("/{cadence_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def deactivate_cadence(
    cadence_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_session),
) -> None:
    cadence = await _get_cadence_or_404(cadence_id, tenant_id, db)
    cadence.is_active = False
    await db.commit()
    logger.info("cadence.deactivated", cadence_id=str(cadence_id))


# ── Helper ────────────────────────────────────────────────────────────

async def _get_cadence_or_404(
    cadence_id: uuid.UUID,
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> Cadence:
    result = await db.execute(
        select(Cadence).where(
            Cadence.id == cadence_id,
            Cadence.tenant_id == tenant_id,
        )
    )
    cadence = result.scalar_one_or_none()
    if cadence is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cadência não encontrada.",
        )
    return cadence
