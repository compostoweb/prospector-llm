"""
api/routes/email_templates.py

CRUD de templates de e-mail reutilizáveis.

Endpoints:
  GET    /email-templates           — listagem com filtro por category/is_active
  POST   /email-templates           — cria template
  GET    /email-templates/{id}      — detalhes
  PATCH  /email-templates/{id}      — atualização parcial
  DELETE /email-templates/{id}      — soft delete (is_active=False)
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_effective_tenant_id, get_session_flexible
from models.email_template import EmailTemplate
from schemas.email_template import (
    EmailTemplateCreateRequest,
    EmailTemplateResponse,
    EmailTemplateUpdateRequest,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/email-templates", tags=["Email Templates"])


def _get_or_404(template: EmailTemplate | None, template_id: uuid.UUID) -> EmailTemplate:
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template {template_id} não encontrado",
        )
    return template


# ── Listagem ──────────────────────────────────────────────────────────

@router.get("", response_model=list[EmailTemplateResponse])
async def list_email_templates(
    category: str | None = Query(default=None),
    active_only: bool = Query(default=True),
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> list[EmailTemplateResponse]:
    q = select(EmailTemplate).where(EmailTemplate.tenant_id == tenant_id)
    if active_only:
        q = q.where(EmailTemplate.is_active.is_(True))
    if category:
        q = q.where(EmailTemplate.category == category)
    q = q.order_by(EmailTemplate.created_at.desc())
    result = await db.execute(q)
    return [EmailTemplateResponse.model_validate(t) for t in result.scalars().all()]


# ── Criação ───────────────────────────────────────────────────────────

@router.post("", response_model=EmailTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_email_template(
    body: EmailTemplateCreateRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> EmailTemplateResponse:
    template = EmailTemplate(
        tenant_id=tenant_id,
        name=body.name,
        description=body.description,
        category=body.category,
        subject=body.subject,
        body_html=body.body_html,
    )
    db.add(template)
    await db.flush()
    logger.info("email_template.created", template_id=str(template.id), tenant_id=str(tenant_id))
    return EmailTemplateResponse.model_validate(template)


# ── Detalhe ───────────────────────────────────────────────────────────

@router.get("/{template_id}", response_model=EmailTemplateResponse)
async def get_email_template(
    template_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> EmailTemplateResponse:
    result = await db.execute(
        select(EmailTemplate).where(
            EmailTemplate.id == template_id,
            EmailTemplate.tenant_id == tenant_id,
        )
    )
    return EmailTemplateResponse.model_validate(
        _get_or_404(result.scalar_one_or_none(), template_id)
    )


# ── Atualização parcial ───────────────────────────────────────────────

@router.patch("/{template_id}", response_model=EmailTemplateResponse)
async def update_email_template(
    template_id: uuid.UUID,
    body: EmailTemplateUpdateRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> EmailTemplateResponse:
    result = await db.execute(
        select(EmailTemplate).where(
            EmailTemplate.id == template_id,
            EmailTemplate.tenant_id == tenant_id,
        )
    )
    template = _get_or_404(result.scalar_one_or_none(), template_id)

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(template, field, value)

    await db.flush()
    return EmailTemplateResponse.model_validate(template)


# ── Exclusão (soft delete) ────────────────────────────────────────────

@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_email_template(
    template_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> None:
    result = await db.execute(
        select(EmailTemplate).where(
            EmailTemplate.id == template_id,
            EmailTemplate.tenant_id == tenant_id,
        )
    )
    template = _get_or_404(result.scalar_one_or_none(), template_id)
    template.is_active = False
    await db.flush()
    logger.info("email_template.deleted", template_id=str(template_id), tenant_id=str(tenant_id))
