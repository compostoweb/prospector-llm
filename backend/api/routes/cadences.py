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

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_effective_tenant_id, get_session_flexible
from models.cadence import Cadence
from schemas.cadence import CadenceCreateRequest, CadenceResponse, CadenceUpdateRequest
from services.cadence_manager import serialize_steps_template
from services.llm_config import resolve_tenant_llm_config

logger = structlog.get_logger()

router = APIRouter(prefix="/cadences", tags=["Cadences"])


# ── Listagem ──────────────────────────────────────────────────────────


@router.get("", response_model=list[CadenceResponse])
async def list_cadences(
    cadence_type: str | None = Query(
        default=None, description="Filtrar por tipo: 'mixed' | 'email_only'"
    ),
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> list[CadenceResponse]:
    stmt = select(Cadence).where(Cadence.tenant_id == tenant_id)
    if cadence_type:
        stmt = stmt.where(Cadence.cadence_type == cadence_type)
    result = await db.execute(stmt.order_by(Cadence.created_at.desc()))
    cadences = result.scalars().all()
    return [CadenceResponse.model_validate(c) for c in cadences]


# ── Criação ───────────────────────────────────────────────────────────


@router.post("", response_model=CadenceResponse, status_code=status.HTTP_201_CREATED)
async def create_cadence(
    body: CadenceCreateRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> CadenceResponse:
    llm_config = body.llm
    if llm_config is None:
        scope = "cold_email" if body.cadence_type == "email_only" else "system"
        llm_config = await resolve_tenant_llm_config(db, tenant_id, scope=scope)

    cadence = Cadence(
        tenant_id=tenant_id,
        name=body.name,
        description=body.description,
        allow_personal_email=body.allow_personal_email,
        mode=body.mode.value,
        cadence_type=body.cadence_type,
        llm_provider=llm_config.provider,
        llm_model=llm_config.model,
        llm_temperature=llm_config.temperature,
        llm_max_tokens=llm_config.max_tokens,
        tts_provider=body.tts_provider,
        tts_voice_id=body.tts_voice_id,
        tts_speed=body.tts_speed,
        tts_pitch=body.tts_pitch,
        lead_list_id=body.lead_list_id,
        email_account_id=body.email_account_id,
        linkedin_account_id=body.linkedin_account_id,
        target_segment=body.target_segment,
        persona_description=body.persona_description,
        offer_description=body.offer_description,
        tone_instructions=body.tone_instructions,
        steps_template=(
            serialize_steps_template([s.model_dump(mode="json") for s in body.steps_template])
            if body.steps_template
            else None
        ),
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
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> CadenceResponse:
    cadence = await _get_cadence_or_404(cadence_id, tenant_id, db)
    return CadenceResponse.model_validate(cadence)


# ── Atualização parcial ───────────────────────────────────────────────


@router.patch("/{cadence_id}", response_model=CadenceResponse)
async def update_cadence(
    cadence_id: uuid.UUID,
    body: CadenceUpdateRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> CadenceResponse:
    cadence = await _get_cadence_or_404(cadence_id, tenant_id, db)

    updates = body.model_dump(
        exclude_unset=True,
        exclude={
            "llm",
            "steps_template",
            "tts_provider",
            "tts_voice_id",
            "lead_list_id",
            "email_account_id",
            "linkedin_account_id",
            "target_segment",
            "persona_description",
            "offer_description",
            "tone_instructions",
            "cadence_type",
        },
    )
    for field, value in updates.items():
        setattr(cadence, field, value)

    if body.steps_template is not None:
        cadence.steps_template = serialize_steps_template(
            [s.model_dump(mode="json") for s in body.steps_template]
        )

    if body.llm is not None:
        cadence.llm_provider = body.llm.provider
        cadence.llm_model = body.llm.model
        cadence.llm_temperature = body.llm.temperature
        cadence.llm_max_tokens = body.llm.max_tokens

    # Campos que precisam de tratamento especial (set explicit, inclusive None)
    raw = body.model_dump(exclude_unset=True)

    # Campos de contexto de prospecção
    for ctx_field in (
        "target_segment",
        "persona_description",
        "offer_description",
        "tone_instructions",
    ):
        if ctx_field in raw:
            setattr(cadence, ctx_field, getattr(body, ctx_field))

    # TTS fields — atualiza se informado (mesmo que None para limpar)
    if "tts_provider" in raw:
        cadence.tts_provider = body.tts_provider
    if "tts_voice_id" in raw:
        cadence.tts_voice_id = body.tts_voice_id
    if "tts_speed" in raw:
        cadence.tts_speed = body.tts_speed
    if "tts_pitch" in raw:
        cadence.tts_pitch = body.tts_pitch
    if "lead_list_id" in raw:
        cadence.lead_list_id = body.lead_list_id
    if "email_account_id" in raw:
        cadence.email_account_id = body.email_account_id
    if "linkedin_account_id" in raw:
        cadence.linkedin_account_id = body.linkedin_account_id
    if "cadence_type" in raw and body.cadence_type is not None:
        cadence.cadence_type = body.cadence_type

    await db.commit()
    await db.refresh(cadence)

    logger.info("cadence.updated", cadence_id=str(cadence_id))
    return CadenceResponse.model_validate(cadence)


# ── Desativação ───────────────────────────────────────────────────────


@router.delete("/{cadence_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def deactivate_cadence(
    cadence_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
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
