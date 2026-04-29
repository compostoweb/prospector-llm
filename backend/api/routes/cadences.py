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

import json
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, Literal, cast

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.dependencies import get_effective_tenant_id, get_llm_registry, get_session_flexible
from integrations.llm import LLMRegistry
from models.cadence import Cadence
from models.cadence_step import CadenceStep
from models.email_template import EmailTemplate
from models.enums import Channel, InteractionDirection, StepType
from models.interaction import Interaction
from models.lead import Lead
from models.tenant import TenantIntegration
from schemas.cadence import (
    CadenceCreateRequest,
    CadenceDeliveryBudgetItemResponse,
    CadenceDeliveryBudgetResponse,
    CadenceReplyAuditItemResponse,
    CadenceReplyEventResponse,
    CadenceReplyManagementResponse,
    CadenceResponse,
    CadenceUpdateRequest,
    StepComposeRequest,
    StepComposeResponse,
    StepPreviewRequest,
    StepPreviewResponse,
    StepSendTestEmailRequest,
    StepSendTestEmailResponse,
    TemplateVariableResponse,
)
from services.ai_composer import AIComposer
from services.cadence_delivery_budget import build_cadence_delivery_budget_snapshots
from services.cadence_manager import (
    CadenceManager,
    get_previous_template_channel,
    get_template_step_config,
    get_total_template_steps,
    serialize_steps_template,
    sync_pending_steps_with_template,
)
from services.lead_management import load_active_cadences_for_leads, serialize_lead
from services.llm_config import resolve_tenant_llm_config
from services.message_quality import build_fallback_email_subject
from services.message_template_renderer import (
    get_template_variable_catalog,
    render_message_template,
    render_saved_email_template,
)
from services.reply_matching import (
    LOW_CONFIDENCE_EMAIL_REPLY_SOURCE,
    pending_reply_audit_interaction_condition,
)
from services.test_email_service import send_test_email

logger = structlog.get_logger()

router = APIRouter(prefix="/cadences", tags=["Cadences"])
_cadence_manager = CadenceManager()


@router.get("/template-variables", response_model=list[TemplateVariableResponse])
async def list_template_variables() -> list[TemplateVariableResponse]:
    return [TemplateVariableResponse(**item) for item in get_template_variable_catalog()]


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
    if body.llm is None:
        scope: Literal["system", "cold_email"] = (
            "cold_email" if body.cadence_type == "email_only" else "system"
        )
        resolved_config = await resolve_tenant_llm_config(
            db,
            tenant_id,
            scope=scope,
        )
        llm_provider = resolved_config.provider
        llm_model = resolved_config.model
        llm_temperature = resolved_config.temperature
        llm_max_tokens = resolved_config.max_tokens
    else:
        llm_provider = body.llm.provider
        llm_model = body.llm.model
        llm_temperature = body.llm.temperature
        llm_max_tokens = body.llm.max_tokens

    cadence = Cadence(
        tenant_id=tenant_id,
        name=body.name,
        description=body.description,
        allow_personal_email=body.allow_personal_email,
        mode=body.mode.value,
        cadence_type=body.cadence_type,
        llm_provider=llm_provider,
        llm_model=llm_model,
        llm_temperature=llm_temperature,
        llm_max_tokens=llm_max_tokens,
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


@router.get("/{cadence_id}/delivery-budget", response_model=CadenceDeliveryBudgetResponse)
async def get_cadence_delivery_budget(
    cadence_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> CadenceDeliveryBudgetResponse:
    cadence = await _get_cadence_or_404(cadence_id, tenant_id, db)
    integration_result = await db.execute(
        select(TenantIntegration).where(TenantIntegration.tenant_id == tenant_id)
    )
    integration = integration_result.scalar_one_or_none()
    snapshots = await build_cadence_delivery_budget_snapshots(db, cadence, integration)
    return CadenceDeliveryBudgetResponse(
        cadence_id=cadence.id,
        generated_at=snapshots[0].generated_at if snapshots else datetime.now(tz=UTC),
        items=[
            CadenceDeliveryBudgetItemResponse(
                channel=item.channel,
                scope_type=item.scope_type,
                scope_label=item.scope_label,
                configured_limit=item.configured_limit,
                daily_budget=item.daily_budget,
                used_today=item.used_today,
                remaining_today=item.remaining_today,
                usage_pct=item.usage_pct,
            )
            for item in snapshots
        ],
    )


@router.get("/{cadence_id}/reply-management", response_model=CadenceReplyManagementResponse)
async def get_cadence_reply_management(
    cadence_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> CadenceReplyManagementResponse:
    await _get_cadence_or_404(cadence_id, tenant_id, db)

    reply_q = await db.execute(
        select(Interaction, CadenceStep.step_number)
        .join(CadenceStep, CadenceStep.id == Interaction.cadence_step_id)
        .where(
            Interaction.tenant_id == tenant_id,
            Interaction.direction == InteractionDirection.INBOUND,
            ~(
                (Interaction.channel == Channel.EMAIL)
                & (Interaction.reply_match_source == LOW_CONFIDENCE_EMAIL_REPLY_SOURCE)
            ),
            CadenceStep.tenant_id == tenant_id,
            CadenceStep.cadence_id == cadence_id,
        )
        .order_by(Interaction.created_at.desc())
    )
    reply_rows = reply_q.all()

    cadence_lead_exists = exists(
        select(CadenceStep.id).where(
            CadenceStep.tenant_id == tenant_id,
            CadenceStep.cadence_id == cadence_id,
            CadenceStep.lead_id == Interaction.lead_id,
        )
    )
    audit_q = await db.execute(
        select(Interaction)
        .where(
            Interaction.tenant_id == tenant_id,
            pending_reply_audit_interaction_condition(),
            cadence_lead_exists,
        )
        .order_by(Interaction.created_at.desc())
    )
    audit_items = audit_q.scalars().all()

    lead_ids = list(
        dict.fromkeys(
            [interaction.lead_id for interaction, _step_number in reply_rows]
            + [interaction.lead_id for interaction in audit_items]
        )
    )

    lead_map: dict[uuid.UUID, Lead] = {}
    active_cadences_by_lead: dict[uuid.UUID, list] = {}
    if lead_ids:
        leads_q = await db.execute(
            select(Lead)
            .where(Lead.tenant_id == tenant_id, Lead.id.in_(lead_ids))
            .options(
                selectinload(Lead.lists),
                selectinload(Lead.emails),
                selectinload(Lead.contact_points),
            )
        )
        leads = leads_q.scalars().all()
        lead_map = {lead.id: lead for lead in leads}
        active_cadences_by_lead = await load_active_cadences_for_leads(
            db,
            tenant_id=tenant_id,
            lead_ids=lead_ids,
        )

    replies = [
        CadenceReplyEventResponse(
            interaction_id=interaction.id,
            lead=serialize_lead(
                lead_map[interaction.lead_id],
                active_cadences_by_lead=active_cadences_by_lead,
            ),
            channel=interaction.channel,
            step_number=step_number,
            replied_at=interaction.created_at,
            intent=interaction.intent.value if interaction.intent else None,
            reply_text=interaction.content_text,
            reply_match_source=interaction.reply_match_source,
        )
        for interaction, step_number in reply_rows
        if interaction.lead_id in lead_map
    ]
    audit = [
        CadenceReplyAuditItemResponse(
            interaction_id=interaction.id,
            lead=serialize_lead(
                lead_map[interaction.lead_id],
                active_cadences_by_lead=active_cadences_by_lead,
            ),
            channel=interaction.channel,
            created_at=interaction.created_at,
            reply_match_status=(
                "low_confidence"
                if interaction.reply_match_source == LOW_CONFIDENCE_EMAIL_REPLY_SOURCE
                else interaction.reply_match_status or "unmatched"
            ),
            reply_match_source=interaction.reply_match_source,
            reply_match_sent_cadence_count=interaction.reply_match_sent_cadence_count,
            content_text=interaction.content_text,
        )
        for interaction in audit_items
        if interaction.lead_id in lead_map
    ]

    return CadenceReplyManagementResponse(replies=replies, audit_items=audit)


@router.post("/{cadence_id}/steps/{step_index}/compose", response_model=StepComposeResponse)
async def compose_cadence_step(
    cadence_id: uuid.UUID,
    step_index: int,
    body: StepComposeRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
    registry: LLMRegistry = Depends(get_llm_registry),
) -> StepComposeResponse:
    cadence = await _get_cadence_or_404(cadence_id, tenant_id, db)

    if step_index < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="step_index deve ser >= 0.",
        )

    step_number = step_index + 1
    template_step = get_template_step_config(cadence, step_number)
    if template_step is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Passo não encontrado nesta cadência.",
        )

    channel = Channel(str(template_step.get("channel")))
    if channel in {Channel.MANUAL_TASK, Channel.LINKEDIN_POST_REACTION}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este canal não suporta geração de texto na sidebar.",
        )

    if body.action == "improve" and not (body.current_text and body.current_text.strip()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A ação improve exige current_text preenchido.",
        )

    configured_step_type = template_step.get("step_type")
    step_type = StepType(str(configured_step_type)) if configured_step_type else None
    previous_channel = get_previous_template_channel(cadence, step_number)
    total_steps = get_total_template_steps(cadence)
    use_voice = bool(template_step.get("use_voice", False))

    composer = AIComposer(registry=registry)
    template_lead = _build_template_lead(cadence)
    editor_cadence = _build_editor_cadence(
        cadence,
        channel=channel,
        action=body.action,
        current_text=body.current_text,
        current_subject=body.current_subject,
    )

    if channel == Channel.EMAIL:
        subject, message_template = await cast(Any, composer).compose_email(
            lead=cast(Any, template_lead),
            step_number=step_number,
            context={},
            cadence=cast(Any, editor_cadence),
            step_type=step_type.value if step_type else None,
            total_steps=total_steps,
            previous_channel=previous_channel,
        )
    else:
        message_template = await cast(Any, composer).compose(
            lead=cast(Any, template_lead),
            channel=channel.value,
            step_number=step_number,
            context={},
            cadence=cast(Any, editor_cadence),
            total_steps=total_steps,
            use_voice=use_voice,
            previous_channel=previous_channel,
            step_type=step_type.value if step_type else None,
        )
        subject = None

    return StepComposeResponse(
        action=body.action,
        channel=channel,
        step_number=step_number,
        step_type=step_type,
        message_template=message_template,
        subject=subject,
        variables=[item["token"] for item in get_template_variable_catalog()],
    )


@router.post("/{cadence_id}/steps/{step_index}/preview", response_model=StepPreviewResponse)
async def preview_cadence_step(
    cadence_id: uuid.UUID,
    step_index: int,
    body: StepPreviewRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> StepPreviewResponse:
    cadence = await _get_cadence_or_404(cadence_id, tenant_id, db)

    preview_response, _preview_lead = await _render_step_preview_response(
        cadence=cadence,
        step_index=step_index,
        body=body,
        tenant_id=tenant_id,
        db=db,
    )
    return preview_response


@router.post(
    "/{cadence_id}/steps/{step_index}/send-test-email",
    response_model=StepSendTestEmailResponse,
)
async def send_cadence_step_test_email(
    cadence_id: uuid.UUID,
    step_index: int,
    body: StepSendTestEmailRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> StepSendTestEmailResponse:
    cadence = await _get_cadence_or_404(cadence_id, tenant_id, db)

    preview_response, preview_lead = await _render_step_preview_response(
        cadence=cadence,
        step_index=step_index,
        body=body,
        tenant_id=tenant_id,
        db=db,
    )
    if preview_response.channel != Channel.EMAIL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Envio de teste por e-mail disponível apenas para passos EMAIL.",
        )

    subject = preview_response.subject or build_fallback_email_subject(
        getattr(preview_lead, "company", None) or getattr(preview_lead, "name", None),
        preview_response.step_number,
    )
    result = await send_test_email(
        db=db,
        cadence=cadence,
        tenant_id=tenant_id,
        to_email=str(body.to_email),
        subject=subject,
        body=preview_response.body,
        body_is_html=preview_response.body_is_html,
    )
    return StepSendTestEmailResponse(
        to_email=result.to_email,
        subject=result.subject,
        provider_type=result.provider_type,
        body_is_html=result.body_is_html,
    )


# ── Atualização parcial ───────────────────────────────────────────────


@router.patch("/{cadence_id}", response_model=CadenceResponse)
async def update_cadence(
    cadence_id: uuid.UUID,
    body: CadenceUpdateRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> CadenceResponse:
    cadence = await _get_cadence_or_404(cadence_id, tenant_id, db)
    previous_lead_list_id = cadence.lead_list_id
    steps_template_updated = body.steps_template is not None

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
        if body.tts_speed is not None:
            cadence.tts_speed = body.tts_speed
    if "tts_pitch" in raw:
        if body.tts_pitch is not None:
            cadence.tts_pitch = body.tts_pitch
    if "lead_list_id" in raw:
        cadence.lead_list_id = uuid.UUID(body.lead_list_id) if body.lead_list_id else None
    if "email_account_id" in raw:
        cadence.email_account_id = (
            uuid.UUID(body.email_account_id) if body.email_account_id else None
        )
    if "linkedin_account_id" in raw:
        cadence.linkedin_account_id = (
            uuid.UUID(body.linkedin_account_id) if body.linkedin_account_id else None
        )
    if "cadence_type" in raw and body.cadence_type is not None:
        cadence.cadence_type = body.cadence_type

    rescheduled_pending_steps = 0
    if steps_template_updated:
        rescheduled_pending_steps = await sync_pending_steps_with_template(cadence, db)

    enrolled_from_list = 0
    if cadence.lead_list_id and cadence.lead_list_id != previous_lead_list_id:
        enrolled_from_list = await _cadence_manager.auto_enroll_list_members(cadence, db)

    await db.commit()

    logger.info(
        "cadence.updated",
        cadence_id=str(cadence_id),
        enrolled_from_list=enrolled_from_list,
        rescheduled_pending_steps=rescheduled_pending_steps,
    )
    return CadenceResponse.model_validate(cadence)


# ── Exclusão ──────────────────────────────────────────────────────────


@router.delete("/{cadence_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def deactivate_cadence(
    cadence_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> None:
    cadence = await _get_cadence_or_404(cadence_id, tenant_id, db)
    await db.delete(cadence)
    await db.commit()
    logger.info("cadence.deleted", cadence_id=str(cadence_id))


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


def _build_template_lead(cadence: Cadence) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=cadence.tenant_id,
        name="{lead_name}",
        first_name="{first_name}",
        last_name="{last_name}",
        company="{company}",
        job_title="{job_title}",
        industry="{industry}",
        city="{city}",
        location="{location}",
        segment="{segment}",
        company_domain="{company_domain}",
        website=None,
        email_corporate="{email}",
        email_personal=None,
        linkedin_url=None,
        linkedin_recent_posts_json=None,
        company_size=None,
    )


async def _resolve_preview_lead(
    lead_id: uuid.UUID | None,
    tenant_id: uuid.UUID,
    db: AsyncSession,
    cadence: Cadence,
) -> Lead | SimpleNamespace:
    if lead_id is None:
        return _build_template_lead(cadence)

    result = await db.execute(
        select(Lead).where(
            Lead.id == lead_id,
            Lead.tenant_id == tenant_id,
        )
    )
    lead = result.scalar_one_or_none()
    if lead is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead da prévia não encontrado.",
        )
    return lead


async def _get_email_template_or_404(
    template_id: str,
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> EmailTemplate:
    try:
        template_uuid = uuid.UUID(str(template_id))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="current_email_template_id inválido.",
        ) from exc

    result = await db.execute(
        select(EmailTemplate).where(
            EmailTemplate.id == template_uuid,
            EmailTemplate.tenant_id == tenant_id,
            EmailTemplate.is_active.is_(True),
        )
    )
    template = result.scalar_one_or_none()
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template de e-mail não encontrado.",
        )
    return template


async def _render_step_preview_response(
    *,
    cadence: Cadence,
    step_index: int,
    body: StepPreviewRequest,
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> tuple[StepPreviewResponse, Lead | SimpleNamespace]:
    if step_index < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="step_index deve ser >= 0.",
        )

    step_number = step_index + 1
    template_step = get_template_step_config(cadence, step_number)
    if template_step is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Passo não encontrado nesta cadência.",
        )

    channel = Channel(str(template_step.get("channel")))
    if channel in {Channel.MANUAL_TASK, Channel.LINKEDIN_POST_REACTION}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este canal não possui prévia textual na sidebar.",
        )

    preview_lead = await _resolve_preview_lead(body.lead_id, tenant_id, db, cadence)

    configured_text = template_step.get("message_template") if template_step else None
    configured_subjects = template_step.get("subject_variants") if template_step else None
    configured_email_template_id = template_step.get("email_template_id") if template_step else None

    preview_text = body.current_text if body.current_text is not None else configured_text
    preview_subject = (
        body.current_subject
        if body.current_subject is not None
        else _pick_first_subject_variant(configured_subjects)
    )
    preview_email_template_id = (
        body.current_email_template_id
        if body.current_email_template_id is not None
        else configured_email_template_id
    )

    rendered_subject: str | None = None
    rendered_body = ""
    body_is_html = False
    method = "manual_template"

    if channel == Channel.EMAIL and preview_email_template_id:
        email_template = await _get_email_template_or_404(
            preview_email_template_id,
            tenant_id,
            db,
        )
        rendered_subject, rendered_body = render_saved_email_template(email_template, preview_lead)
        body_is_html = True
        method = "saved_email_template"
    elif channel == Channel.LINKEDIN_INMAIL:
        rendered_payload = render_message_template(preview_text, preview_lead) or ""
        rendered_subject, rendered_body = _parse_inmail_preview(rendered_payload)
        method = "linkedin_inmail_json"
    else:
        rendered_subject = render_message_template(preview_subject, preview_lead)
        rendered_body = render_message_template(preview_text, preview_lead) or ""
        method = "manual_template" if preview_text else "empty"

    return (
        StepPreviewResponse(
            channel=channel,
            step_number=step_number,
            lead_id=getattr(preview_lead, "id", None),
            lead_name=getattr(preview_lead, "name", None),
            subject=rendered_subject,
            body=rendered_body,
            body_is_html=body_is_html,
            variables=[item["token"] for item in get_template_variable_catalog()],
            method=method,
        ),
        preview_lead,
    )


def _pick_first_subject_variant(subject_variants: object) -> str | None:
    if not isinstance(subject_variants, list):
        return None
    for item in subject_variants:
        text = str(item).strip()
        if text:
            return text
    return None


def _parse_inmail_preview(rendered_payload: str) -> tuple[str | None, str]:
    try:
        data = json.loads(rendered_payload)
    except ValueError:
        return None, rendered_payload

    if not isinstance(data, dict):
        return None, rendered_payload

    subject = data.get("subject")
    body = data.get("body")
    return (
        str(subject).strip() or None if subject is not None else None,
        str(body) if body is not None else rendered_payload,
    )


def _build_editor_cadence(
    cadence: Cadence,
    *,
    channel: Channel,
    action: str,
    current_text: str | None,
    current_subject: str | None,
) -> SimpleNamespace:
    tone_instructions = cadence.tone_instructions or ""
    extra_lines = [
        "Você está escrevendo um template reutilizável de cadência, não uma mensagem final já personalizada para um único lead.",
        "Quando precisar personalização, use apenas placeholders permitidos como {first_name}, {company}, {job_title}, {industry}, {city}, {location}, {segment}, {company_domain}, {website} e {email}.",
        "Não invente fatos específicos de uma empresa real, site ou postagem recente.",
        "O resultado precisa ser seguro para salvar no editor como conteúdo manual do passo.",
    ]
    if channel == Channel.EMAIL:
        extra_lines.append(
            "Para email, gere subject e body que funcionem como template reutilizável para vários leads."
        )
    if action == "improve":
        extra_lines.append(
            "Melhore o rascunho abaixo, preservando placeholders válidos quando existirem."
        )
        if current_subject:
            extra_lines.append(f"Assunto atual:\n{current_subject.strip()}")
        if current_text:
            extra_lines.append(f"Rascunho atual:\n{current_text.strip()}")
    guidance = "\n".join(extra_lines)
    merged_tone = f"{tone_instructions}\n\n{guidance}".strip()

    return SimpleNamespace(
        id=cadence.id,
        tenant_id=cadence.tenant_id,
        llm_provider=cadence.llm_provider,
        llm_model=cadence.llm_model,
        llm_temperature=cadence.llm_temperature,
        llm_max_tokens=cadence.llm_max_tokens,
        target_segment=cadence.target_segment,
        persona_description=cadence.persona_description,
        offer_description=cadence.offer_description,
        tone_instructions=merged_tone,
        cadence_type=getattr(cadence, "cadence_type", "mixed"),
    )
