"""
api/routes/warmup.py

Endpoints para gerenciamento de campanhas de warmup de e-mail.

Rotas:
  GET    /warmup                   — lista campanhas do tenant
  POST   /warmup                   — cria nova campanha
  GET    /warmup/{id}              — detalhe da campanha
  PATCH  /warmup/{id}              — pausa/retoma/edita campanha
  DELETE /warmup/{id}              — remove campanha
  GET    /warmup/{id}/stats        — métricas consolidadas
  GET    /warmup/{id}/logs         — logs de envio paginados
  POST   /warmup/{id}/start        — inicia campanha pausada
  POST   /warmup/{id}/pause        — pausa campanha ativa

Autenticação: user token ou tenant token (get_session_flexible).
"""

from __future__ import annotations

import uuid
from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_effective_tenant_id, get_session_flexible
from models.warmup import WarmupCampaign, WarmupLog
from models.enums import WarmupStatus

router = APIRouter(prefix="/warmup", tags=["Warmup"])
logger = structlog.get_logger()


# ── Schemas inline (warmupo é auto-contido) ───────────────────────────

class WarmupCampaignCreateRequest(BaseModel):
    email_account_id: uuid.UUID
    daily_volume_start: int = Field(default=5, ge=1, le=100)
    daily_volume_target: int = Field(default=80, ge=5, le=500)
    ramp_days: int = Field(default=30, ge=7, le=90)


class WarmupCampaignUpdateRequest(BaseModel):
    daily_volume_start: int | None = Field(default=None, ge=1, le=100)
    daily_volume_target: int | None = Field(default=None, ge=5, le=500)
    ramp_days: int | None = Field(default=None, ge=7, le=90)


class WarmupCampaignResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    email_account_id: uuid.UUID
    status: str
    current_day: int
    ramp_days: int
    daily_volume_start: int
    daily_volume_target: int
    total_sent: int
    total_replied: int
    spam_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WarmupLogResponse(BaseModel):
    id: uuid.UUID
    direction: str
    status: str
    partner_email: str
    message_id_sent: str | None
    sent_at: datetime | None
    replied_at: datetime | None

    model_config = {"from_attributes": True}


# ── Listagem ──────────────────────────────────────────────────────────

@router.get("", response_model=list[WarmupCampaignResponse])
async def list_campaigns(
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> list[WarmupCampaignResponse]:
    result = await db.execute(
        select(WarmupCampaign)
        .where(WarmupCampaign.tenant_id == tenant_id)
        .order_by(WarmupCampaign.created_at.desc())
    )
    campaigns = result.scalars().all()
    return [WarmupCampaignResponse.model_validate(c) for c in campaigns]


# ── Criar ─────────────────────────────────────────────────────────────

@router.post("", response_model=WarmupCampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    body: WarmupCampaignCreateRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> WarmupCampaignResponse:
    # Verifica se já existe campanha ativa para esta conta
    existing = await db.execute(
        select(WarmupCampaign).where(
            WarmupCampaign.tenant_id == tenant_id,
            WarmupCampaign.email_account_id == body.email_account_id,
            WarmupCampaign.status == WarmupStatus.ACTIVE,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma campanha de warmup ativa para esta conta de e-mail.",
        )

    campaign = WarmupCampaign(
        tenant_id=tenant_id,
        email_account_id=body.email_account_id,
        daily_volume_start=body.daily_volume_start,
        daily_volume_target=body.daily_volume_target,
        ramp_days=body.ramp_days,
    )
    db.add(campaign)
    await db.flush()
    await db.refresh(campaign)
    logger.info(
        "warmup.campaign_created",
        campaign_id=str(campaign.id),
        tenant_id=str(tenant_id),
    )
    return WarmupCampaignResponse.model_validate(campaign)


# ── Detalhe ───────────────────────────────────────────────────────────

@router.get("/{campaign_id}", response_model=WarmupCampaignResponse)
async def get_campaign(
    campaign_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> WarmupCampaignResponse:
    campaign = await _get_or_404(campaign_id, tenant_id, db)
    return WarmupCampaignResponse.model_validate(campaign)


# ── Editar ────────────────────────────────────────────────────────────

@router.patch("/{campaign_id}", response_model=WarmupCampaignResponse)
async def update_campaign(
    campaign_id: uuid.UUID,
    body: WarmupCampaignUpdateRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> WarmupCampaignResponse:
    campaign = await _get_or_404(campaign_id, tenant_id, db)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(campaign, field, value)
    await db.flush()
    await db.refresh(campaign)
    return WarmupCampaignResponse.model_validate(campaign)


# ── Remover ───────────────────────────────────────────────────────────

@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_campaign(
    campaign_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> None:
    campaign = await _get_or_404(campaign_id, tenant_id, db)
    await db.delete(campaign)
    logger.info("warmup.campaign_deleted", campaign_id=str(campaign_id))


# ── Iniciar / Pausar ──────────────────────────────────────────────────

@router.post("/{campaign_id}/start", response_model=WarmupCampaignResponse)
async def start_campaign(
    campaign_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> WarmupCampaignResponse:
    campaign = await _get_or_404(campaign_id, tenant_id, db)
    if campaign.status == WarmupStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Campanha já foi completada. Crie uma nova.",
        )
    campaign.status = WarmupStatus.ACTIVE
    await db.flush()
    await db.refresh(campaign)
    logger.info("warmup.campaign_started", campaign_id=str(campaign_id))
    return WarmupCampaignResponse.model_validate(campaign)


@router.post("/{campaign_id}/pause", response_model=WarmupCampaignResponse)
async def pause_campaign(
    campaign_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> WarmupCampaignResponse:
    campaign = await _get_or_404(campaign_id, tenant_id, db)
    campaign.status = WarmupStatus.PAUSED
    await db.flush()
    await db.refresh(campaign)
    logger.info("warmup.campaign_paused", campaign_id=str(campaign_id))
    return WarmupCampaignResponse.model_validate(campaign)


# ── Estatísticas ──────────────────────────────────────────────────────

@router.get("/{campaign_id}/stats")
async def get_campaign_stats(
    campaign_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> dict:
    """Retorna métricas consolidadas da campanha."""
    from services.warmup_service import get_campaign_stats  # noqa: PLC0415
    stats = await get_campaign_stats(campaign_id, tenant_id, db)
    if not stats:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campanha não encontrada.")
    return stats


# ── Logs ──────────────────────────────────────────────────────────────

@router.get("/{campaign_id}/logs", response_model=list[WarmupLogResponse])
async def get_campaign_logs(
    campaign_id: uuid.UUID,
    direction: str | None = Query(default=None, description="sent | received"),
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> list[WarmupLogResponse]:
    """Lista logs de envio da campanha com filtros opcionais."""
    await _get_or_404(campaign_id, tenant_id, db)

    stmt = (
        select(WarmupLog)
        .where(WarmupLog.campaign_id == campaign_id)
        .order_by(WarmupLog.sent_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if direction:
        stmt = stmt.where(WarmupLog.direction == direction)
    if status_filter:
        stmt = stmt.where(WarmupLog.status == status_filter)

    result = await db.execute(stmt)
    logs = result.scalars().all()
    return [WarmupLogResponse.model_validate(log) for log in logs]


# ── Helper ────────────────────────────────────────────────────────────

async def _get_or_404(
    campaign_id: uuid.UUID,
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> WarmupCampaign:
    result = await db.execute(
        select(WarmupCampaign).where(
            WarmupCampaign.id == campaign_id,
            WarmupCampaign.tenant_id == tenant_id,
        )
    )
    campaign = result.scalar_one_or_none()
    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campanha de warmup não encontrada.",
        )
    return campaign
