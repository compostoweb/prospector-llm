"""
api/routes/sandbox.py

Rotas REST para o sistema de sandbox de cadências.

Endpoints:
  POST   /cadences/{cadence_id}/sandbox           — cria sandbox run
  GET    /cadences/{cadence_id}/sandbox            — lista runs da cadência
  GET    /sandbox/{run_id}                         — detalhe do run com steps
  POST   /sandbox/{run_id}/generate                — gera mensagens para todos os steps
  POST   /sandbox/steps/{step_id}/regenerate       — regenera mensagem de um step
  PATCH  /sandbox/steps/{step_id}/approve          — aprova step individual
  PATCH  /sandbox/steps/{step_id}/reject           — rejeita step individual
  PATCH  /sandbox/{run_id}/approve                 — aprova run inteiro (bulk)
  POST   /sandbox/{run_id}/start                   — inicia cadência real
  POST   /sandbox/steps/{step_id}/simulate-reply   — simula reply inbound
  GET    /sandbox/{run_id}/timeline                — timeline com rate limits
  POST   /sandbox/{run_id}/pipedrive-dry-run       — dry-run Pipedrive
  DELETE /sandbox/{run_id}                         — remove sandbox run
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_effective_tenant_id, get_llm_registry, get_session_flexible
from integrations.llm.registry import LLMRegistry
from models.sandbox import SandboxRun
from schemas.sandbox import (
    PipedriveDryRunResponse,
    SandboxApproveResponse,
    SandboxCreateRequest,
    SandboxRegenerateRequest,
    SandboxRunListResponse,
    SandboxRunResponse,
    SandboxStartResponse,
    SandboxStepResponse,
    SimulateReplyRequest,
)
from services.sandbox_service import sandbox_service

logger = structlog.get_logger()

router = APIRouter(tags=["Sandbox"])


# ── Criar sandbox run ────────────────────────────────────────────────

@router.post(
    "/cadences/{cadence_id}/sandbox",
    response_model=SandboxRunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_sandbox_run(
    cadence_id: uuid.UUID,
    body: SandboxCreateRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
    registry: LLMRegistry = Depends(get_llm_registry),
) -> SandboxRunResponse:
    try:
        run = await sandbox_service.create_run(
            cadence_id=cadence_id,
            tenant_id=tenant_id,
            db=db,
            registry=registry,
            lead_ids=body.lead_ids,
            lead_count=body.lead_count,
            use_fictitious=body.use_fictitious,
        )
        await db.commit()
        return SandboxRunResponse.model_validate(run)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── Listar runs de uma cadência ──────────────────────────────────────

@router.get(
    "/cadences/{cadence_id}/sandbox",
    response_model=list[SandboxRunListResponse],
)
async def list_sandbox_runs(
    cadence_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> list[SandboxRunListResponse]:
    result = await db.execute(
        select(SandboxRun)
        .where(
            SandboxRun.cadence_id == cadence_id,
            SandboxRun.tenant_id == tenant_id,
        )
        .order_by(SandboxRun.created_at.desc())
    )
    runs = result.scalars().all()
    return [
        SandboxRunListResponse(
            id=r.id,
            cadence_id=r.cadence_id,
            status=r.status,
            lead_source=r.lead_source,
            steps_count=len(r.steps) if r.steps else 0,
            created_at=r.created_at,
        )
        for r in runs
    ]


# ── Detalhe do run com steps ─────────────────────────────────────────

@router.get("/sandbox/{run_id}", response_model=SandboxRunResponse)
async def get_sandbox_run(
    run_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> SandboxRunResponse:
    try:
        run = await sandbox_service._get_run(run_id, tenant_id, db)
        return SandboxRunResponse.model_validate(run)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sandbox run não encontrado.",
        )


# ── Gerar mensagens ──────────────────────────────────────────────────

@router.post("/sandbox/{run_id}/generate", response_model=SandboxRunResponse)
async def generate_sandbox_steps(
    run_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
    registry: LLMRegistry = Depends(get_llm_registry),
) -> SandboxRunResponse:
    try:
        run = await sandbox_service.generate_all_steps(
            run_id=run_id,
            tenant_id=tenant_id,
            db=db,
            registry=registry,
        )
        await db.commit()
        return SandboxRunResponse.model_validate(run)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── Regenerar step ───────────────────────────────────────────────────

@router.post(
    "/sandbox/steps/{step_id}/regenerate",
    response_model=SandboxStepResponse,
)
async def regenerate_sandbox_step(
    step_id: uuid.UUID,
    body: SandboxRegenerateRequest | None = None,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
    registry: LLMRegistry = Depends(get_llm_registry),
) -> SandboxStepResponse:
    try:
        step = await sandbox_service.regenerate_step(
            step_id=step_id,
            tenant_id=tenant_id,
            db=db,
            registry=registry,
            temperature_override=body.temperature if body else None,
        )
        await db.commit()
        return SandboxStepResponse.model_validate(step)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── Aprovar step ─────────────────────────────────────────────────────

@router.patch(
    "/sandbox/steps/{step_id}/approve",
    response_model=SandboxStepResponse,
)
async def approve_sandbox_step(
    step_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> SandboxStepResponse:
    try:
        step = await sandbox_service.approve_step(step_id, tenant_id, db)
        await db.commit()
        return SandboxStepResponse.model_validate(step)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ── Rejeitar step ────────────────────────────────────────────────────

@router.patch(
    "/sandbox/steps/{step_id}/reject",
    response_model=SandboxStepResponse,
)
async def reject_sandbox_step(
    step_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> SandboxStepResponse:
    try:
        step = await sandbox_service.reject_step(step_id, tenant_id, db)
        await db.commit()
        return SandboxStepResponse.model_validate(step)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ── Aprovar run inteiro ──────────────────────────────────────────────

@router.patch("/sandbox/{run_id}/approve", response_model=SandboxApproveResponse)
async def approve_sandbox_run(
    run_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> SandboxApproveResponse:
    try:
        run, approved_count = await sandbox_service.approve_run(run_id, tenant_id, db)
        await db.commit()
        return SandboxApproveResponse(
            sandbox_run_id=run.id,
            status=run.status,
            steps_approved=approved_count,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ── Iniciar cadência real ────────────────────────────────────────────

@router.post("/sandbox/{run_id}/start", response_model=SandboxStartResponse)
async def start_from_sandbox(
    run_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> SandboxStartResponse:
    try:
        result = await sandbox_service.start_from_sandbox(run_id, tenant_id, db)
        await db.commit()

        run = await sandbox_service._get_run(run_id, tenant_id, db)
        return SandboxStartResponse(
            sandbox_run_id=run.id,
            cadence_id=run.cadence_id,
            leads_enrolled=result["leads_enrolled"],
            steps_created=result["steps_created"],
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── Simular reply ────────────────────────────────────────────────────

@router.post(
    "/sandbox/steps/{step_id}/simulate-reply",
    response_model=SandboxStepResponse,
)
async def simulate_reply(
    step_id: uuid.UUID,
    body: SimulateReplyRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
    registry: LLMRegistry = Depends(get_llm_registry),
) -> SandboxStepResponse:
    if body.mode == "manual" and not body.reply_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="reply_text é obrigatório no modo manual.",
        )

    try:
        if body.mode == "auto":
            step = await sandbox_service.simulate_reply_auto(
                step_id, tenant_id, db, registry
            )
        else:
            step = await sandbox_service.simulate_reply_manual(
                step_id, tenant_id, db, registry, body.reply_text  # type: ignore[arg-type]
            )
        await db.commit()
        return SandboxStepResponse.model_validate(step)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── Timeline com rate limits ─────────────────────────────────────────

@router.get("/sandbox/{run_id}/timeline", response_model=SandboxRunResponse)
async def get_sandbox_timeline(
    run_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> SandboxRunResponse:
    try:
        run = await sandbox_service.calculate_rate_limited_timeline(
            run_id, tenant_id, db
        )
        await db.commit()
        return SandboxRunResponse.model_validate(run)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ── Pipedrive dry-run ────────────────────────────────────────────────

@router.post("/sandbox/{run_id}/pipedrive-dry-run", response_model=PipedriveDryRunResponse)
async def pipedrive_dry_run(
    run_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> PipedriveDryRunResponse:
    try:
        results = await sandbox_service.dry_run_pipedrive(run_id, tenant_id, db)
        await db.commit()
        return PipedriveDryRunResponse(
            sandbox_run_id=run_id,
            leads=results,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── Deletar sandbox run ─────────────────────────────────────────────

@router.delete("/sandbox/{run_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_sandbox_run(
    run_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> None:
    try:
        run = await sandbox_service._get_run(run_id, tenant_id, db)
        await db.delete(run)
        await db.commit()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sandbox run não encontrado.",
        )
