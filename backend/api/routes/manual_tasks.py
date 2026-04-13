"""
api/routes/manual_tasks.py

Rotas REST para tarefas manuais da cadência semi-automática.

Endpoints:
  GET    /tasks           — listar tarefas (filtros: cadence_id, status, channel)
  GET    /tasks/stats     — estatísticas
  GET    /tasks/{id}      — detalhe da tarefa com dados do lead
  POST   /tasks/{id}/generate    — gerar conteúdo LLM
  POST   /tasks/{id}/regenerate  — regerar conteúdo
  PATCH  /tasks/{id}      — atualizar texto editado
  POST   /tasks/{id}/send — enviar via sistema (Unipile)
  POST   /tasks/{id}/done — marcar como executada externamente
  POST   /tasks/{id}/skip — pular tarefa
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_effective_tenant_id, get_llm_registry, get_session_flexible
from integrations.llm import LLMRegistry
from models.enums import Channel, ManualTaskStatus
from schemas.manual_task import (
    ManualTaskDoneExternalRequest,
    ManualTaskListResponse,
    ManualTaskResponse,
    ManualTaskStatsResponse,
    ManualTaskUpdateRequest,
)
from services.manual_task_service import ManualTaskService

logger = structlog.get_logger()

router = APIRouter(prefix="/tasks", tags=["Manual Tasks"])

_service = ManualTaskService()


@router.get("", response_model=ManualTaskListResponse)
async def list_tasks(
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
    cadence_id: uuid.UUID | None = Query(default=None),
    task_status: ManualTaskStatus | None = Query(default=None, alias="status"),
    channel: Channel | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> ManualTaskListResponse:
    result = await _service.list_tasks(
        tenant_id=tenant_id,
        db=db,
        cadence_id=cadence_id,
        status=task_status,
        channel=channel,
        page=page,
        page_size=page_size,
    )
    return ManualTaskListResponse(
        items=[ManualTaskResponse.model_validate(t) for t in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.get("/stats", response_model=ManualTaskStatsResponse)
async def get_stats(
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ManualTaskStatsResponse:
    stats = await _service.get_stats(tenant_id, db)
    return ManualTaskStatsResponse(**stats)


@router.get("/{task_id}", response_model=ManualTaskResponse)
async def get_task(
    task_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ManualTaskResponse:
    try:
        task = await _service._get_task(task_id, db, tenant_id=tenant_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarefa não encontrada")
    return ManualTaskResponse.model_validate(task)


@router.post("/{task_id}/generate", response_model=ManualTaskResponse)
async def generate_content(
    task_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
    registry: LLMRegistry = Depends(get_llm_registry),
) -> ManualTaskResponse:
    try:
        task = await _service.generate_content(task_id, tenant_id, db, registry)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return ManualTaskResponse.model_validate(task)


@router.post("/{task_id}/regenerate", response_model=ManualTaskResponse)
async def regenerate_content(
    task_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
    registry: LLMRegistry = Depends(get_llm_registry),
) -> ManualTaskResponse:
    try:
        task = await _service.regenerate_content(task_id, tenant_id, db, registry)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return ManualTaskResponse.model_validate(task)


@router.patch("/{task_id}", response_model=ManualTaskResponse)
async def update_task(
    task_id: uuid.UUID,
    body: ManualTaskUpdateRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ManualTaskResponse:
    try:
        task = await _service.update_content(task_id, tenant_id, body.edited_text, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return ManualTaskResponse.model_validate(task)


@router.post("/{task_id}/send", response_model=ManualTaskResponse)
async def send_task(
    task_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ManualTaskResponse:
    try:
        task = await _service.send_via_system(task_id, tenant_id, db)
    except ValueError as e:
        error_message = str(e)
        if "não encontrada" in error_message:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_message)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_message)
    return ManualTaskResponse.model_validate(task)


@router.post("/{task_id}/done", response_model=ManualTaskResponse)
async def mark_done(
    task_id: uuid.UUID,
    body: ManualTaskDoneExternalRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ManualTaskResponse:
    try:
        task = await _service.mark_done_external(task_id, tenant_id, body.notes, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return ManualTaskResponse.model_validate(task)


@router.post("/{task_id}/skip", response_model=ManualTaskResponse)
async def skip_task(
    task_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ManualTaskResponse:
    try:
        task = await _service.skip(task_id, tenant_id, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return ManualTaskResponse.model_validate(task)
