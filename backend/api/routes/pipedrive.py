"""
api/routes/pipedrive.py

Endpoints proxy para buscar metadados do Pipedrive (pipelines, stages, users).
Usados pelo frontend na configuração de integrações — alimentam dropdowns de seleção.
Usa credenciais do tenant armazenadas no banco (TenantIntegration).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_effective_tenant_id, get_session_flexible
from core.security import UserPayload, get_current_user_payload
from integrations.pipedrive_client import PipedriveClient
from models.tenant import TenantIntegration

router = APIRouter(prefix="/pipedrive", tags=["Pipedrive"])


async def _get_tenant_pd_client(
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> PipedriveClient:
    """Cria PipedriveClient com token/domain do tenant."""
    result = await db.execute(
        select(TenantIntegration).where(TenantIntegration.tenant_id == tenant_id)
    )
    integration = result.scalar_one_or_none()
    if not integration or not integration.pipedrive_api_token:
        raise HTTPException(status_code=400, detail="Pipedrive não configurado para este tenant.")
    return PipedriveClient(
        token=integration.pipedrive_api_token,
        domain=integration.pipedrive_domain,
    )


@router.get("/pipelines", summary="Lista pipelines do Pipedrive")
async def list_pipelines(
    _user: UserPayload = Depends(get_current_user_payload),
    client: PipedriveClient = Depends(_get_tenant_pd_client),
) -> list[dict]:
    return await client.get_pipelines()


@router.get("/stages", summary="Lista stages (opcionalmente por pipeline)")
async def list_stages(
    pipeline_id: int | None = Query(None, description="Filtra stages por pipeline"),
    _user: UserPayload = Depends(get_current_user_payload),
    client: PipedriveClient = Depends(_get_tenant_pd_client),
) -> list[dict]:
    return await client.get_stages(pipeline_id=pipeline_id)


@router.get("/users", summary="Lista usuários ativos do Pipedrive")
async def list_users(
    _user: UserPayload = Depends(get_current_user_payload),
    client: PipedriveClient = Depends(_get_tenant_pd_client),
) -> list[dict]:
    return await client.get_users()
