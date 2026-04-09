"""
api/routes/content/calculator.py

Calculadora pública de ROI e métricas internas.
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_effective_tenant_id, get_session_flexible, get_session_no_auth
from core.config import settings
from models.content_calculator_result import ContentCalculatorResult
from models.content_lead_magnet import ContentLeadMagnet
from models.tenant import Tenant
from schemas.content_inbound import (
    CalculatorCalculateRequest,
    CalculatorCalculateResponse,
    CalculatorConfigResponse,
    CalculatorConvertRequest,
    CalculatorConvertResponse,
    CalculatorMetricsResponse,
    CalculatorProcessType,
    InvestmentRangeResponse,
)
from services.content.lead_magnet_service import (
    convert_inbound_contact_to_prospect,
    convert_lm_lead_to_prospect,
    queue_sendpulse_sync,
    upsert_lm_capture,
)
from services.content.lm_calculator import calculate_roi, get_calculator_config
from services.notification import (
    send_calculator_diagnosis_email,
    send_calculator_submission_notification,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/calculator", tags=["Content Hub — Calculator"])


async def _resolve_public_calculator_context(
    db: AsyncSession,
    lead_magnet_id: uuid.UUID | None,
) -> tuple[uuid.UUID, ContentLeadMagnet | None]:
    if lead_magnet_id is not None:
        result = await db.execute(
            select(ContentLeadMagnet).where(ContentLeadMagnet.id == lead_magnet_id)
        )
        lead_magnet = result.scalar_one_or_none()
        if lead_magnet is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Lead magnet não encontrado"
            )
        return lead_magnet.tenant_id, lead_magnet

    tenant_result = await db.execute(
        select(Tenant.id)
        .where(Tenant.is_active.is_(True))
        .order_by((Tenant.slug == settings.DEFAULT_TENANT_SLUG).desc(), Tenant.created_at.asc())
        .limit(1)
    )
    tenant_id = tenant_result.scalar_one_or_none()
    if tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Nenhum tenant ativo disponível"
        )
    return tenant_id, None


@router.get("/config", response_model=CalculatorConfigResponse)
async def get_config() -> CalculatorConfigResponse:
    role_costs, process_ranges = get_calculator_config()
    typed_process_ranges: dict[CalculatorProcessType, InvestmentRangeResponse] = {
        key: InvestmentRangeResponse(min=value[0], max=value[1])
        for key, value in process_ranges.items()
    }
    return CalculatorConfigResponse(
        role_hourly_costs=role_costs,
        process_investment_ranges=typed_process_ranges,
    )


@router.post(
    "/calculate", response_model=CalculatorCalculateResponse, status_code=status.HTTP_201_CREATED
)
async def calculate(
    body: CalculatorCalculateRequest,
    request: Request,
    db: AsyncSession = Depends(get_session_no_auth),
) -> CalculatorCalculateResponse:
    tenant_id, lead_magnet = await _resolve_public_calculator_context(db, body.lead_magnet_id)
    computation = calculate_roi(
        pessoas=body.pessoas,
        horas_semana=body.horas_semana,
        custo_hora=body.custo_hora,
        cargo=body.cargo,
        retrabalho_pct=body.retrabalho_pct,
        tipo_processo=body.tipo_processo,
        company_segment=body.company_segment,
        company_size=body.company_size,
        process_area_span=body.process_area_span,
    )

    result = ContentCalculatorResult(
        tenant_id=tenant_id,
        lead_magnet_id=lead_magnet.id if lead_magnet else None,
        pessoas=body.pessoas,
        horas_semana=body.horas_semana,
        custo_hora=computation.custo_hora_sugerido,
        cargo=body.cargo,
        retrabalho_pct=body.retrabalho_pct,
        tipo_processo=body.tipo_processo,
        company_segment=body.company_segment,
        company_size=body.company_size,
        process_area_span=body.process_area_span,
        custo_mensal=computation.custo_mensal,
        custo_retrabalho=computation.custo_retrabalho,
        custo_total_mensal=computation.custo_total_mensal,
        custo_anual=computation.custo_anual,
        investimento_estimado_min=computation.investimento_estimado_min,
        investimento_estimado_max=computation.investimento_estimado_max,
        roi_estimado=computation.roi_estimado,
        payback_meses=computation.payback_meses,
        ip_address=request.client.host if request.client else None,
        session_id=body.session_id,
    )
    db.add(result)
    await db.commit()
    await db.refresh(result)
    logger.info("content.calculator.calculated", result_id=str(result.id), tenant_id=str(tenant_id))

    return CalculatorCalculateResponse(
        result_id=result.id,
        custo_hora_sugerido=computation.custo_hora_sugerido,
        custo_mensal=computation.custo_mensal,
        custo_retrabalho=computation.custo_retrabalho,
        custo_total_mensal=computation.custo_total_mensal,
        custo_anual=computation.custo_anual,
        investimento_estimado_min=computation.investimento_estimado_min,
        investimento_estimado_max=computation.investimento_estimado_max,
        roi_estimado=computation.roi_estimado,
        payback_meses=computation.payback_meses,
        mensagem_resultado=computation.mensagem_resultado,
    )


@router.post("/convert", response_model=CalculatorConvertResponse)
async def convert_calculator_result(
    body: CalculatorConvertRequest,
    db: AsyncSession = Depends(get_session_no_auth),
) -> CalculatorConvertResponse:
    result_query = await db.execute(
        select(ContentCalculatorResult).where(ContentCalculatorResult.id == body.result_id)
    )
    result = result_query.scalar_one_or_none()
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resultado da calculadora não encontrado"
        )

    result.name = body.name
    result.email = body.email
    result.company = body.company
    result.role = body.role
    result.phone = body.phone

    lm_lead = None
    should_sync = False
    lead = None

    lead_magnet = None
    if result.lead_magnet_id is not None:
        lm_result = await db.execute(
            select(ContentLeadMagnet).where(ContentLeadMagnet.id == result.lead_magnet_id)
        )
        lead_magnet = lm_result.scalar_one_or_none()

    if lead_magnet is not None:
        lm_lead, _, should_sync = await upsert_lm_capture(
            db,
            lead_magnet=lead_magnet,
            name=body.name,
            email=body.email,
            origin="calculator",
            company=body.company,
            role=body.role,
            phone=body.phone,
            capture_metadata={
                "calculator_result_id": str(result.id),
                "roi_estimado": float(result.roi_estimado),
                "custo_anual": float(result.custo_anual),
                "company_segment": result.company_segment,
                "company_size": result.company_size,
                "process_area_span": result.process_area_span,
            },
        )

    if body.create_prospect:
        context_suffix_parts = [
            f"ROI estimado: {float(result.roi_estimado):.2f}%",
            f"Payback: {float(result.payback_meses):.1f} meses",
        ]
        if result.company_segment:
            context_suffix_parts.append(f"Segmento: {result.company_segment}")
        if result.company_size:
            context_suffix_parts.append(f"Porte: {result.company_size}")
        if result.process_area_span:
            context_suffix_parts.append(f"Áreas: {result.process_area_span}")
        note_suffix = " | ".join(context_suffix_parts)
        if lm_lead is not None and lead_magnet is not None:
            lead = await convert_lm_lead_to_prospect(
                db,
                lm_lead=lm_lead,
                lead_magnet_title=lead_magnet.title,
                note_suffix=note_suffix,
                extra_tags=["calculator_conversion"],
            )
        else:
            lead = await convert_inbound_contact_to_prospect(
                db,
                tenant_id=result.tenant_id,
                name=body.name,
                email=body.email,
                company=body.company,
                role=body.role,
                phone=body.phone,
                note=f"Origem inbound: calculadora de ROI | {note_suffix}",
                extra_tags=["calculator_conversion"],
            )

    if lead is not None:
        result.converted_to_lead = True
        result.lead_id = lead.id

    await db.commit()
    await db.refresh(result)
    if lm_lead is not None:
        await db.refresh(lm_lead)
        if should_sync:
            await queue_sendpulse_sync(lm_lead)

    diagnosis_email_sent = await send_calculator_diagnosis_email(
        result=result,
        lead_magnet_title=lead_magnet.title if lead_magnet else None,
    )
    notification_sent = await send_calculator_submission_notification(
        result=result,
        lead_magnet_title=lead_magnet.title if lead_magnet else None,
        lm_lead_id=lm_lead.id if lm_lead else None,
        sendpulse_sync_status=lm_lead.sendpulse_sync_status if lm_lead else None,
        diagnosis_email_sent=diagnosis_email_sent,
    )

    logger.info(
        "content.calculator.converted",
        result_id=str(result.id),
        lead_id=str(lead.id) if lead else None,
        diagnosis_email_sent=diagnosis_email_sent,
        notification_sent=notification_sent,
    )
    return CalculatorConvertResponse.model_validate(
        {
            "result_id": result.id,
            "lm_lead_id": lm_lead.id if lm_lead else None,
            "lead_id": lead.id if lead else None,
            "sendpulse_sync_status": lm_lead.sendpulse_sync_status if lm_lead else None,
            "diagnosis_email_sent": diagnosis_email_sent,
            "internal_notification_sent": notification_sent,
        }
    )


@router.get("/metrics", response_model=CalculatorMetricsResponse)
async def get_metrics(
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> CalculatorMetricsResponse:
    result = await db.execute(
        select(ContentCalculatorResult)
        .where(ContentCalculatorResult.tenant_id == tenant_id)
        .order_by(ContentCalculatorResult.created_at.desc())
    )
    items = result.scalars().all()
    total_simulations = len(items)
    total_captured_contacts = len([item for item in items if item.email])
    total_converted_to_lead = len([item for item in items if item.converted_to_lead])
    conversion_rate = None
    if total_simulations > 0:
        conversion_rate = round((total_converted_to_lead / total_simulations) * 100.0, 2)
    return CalculatorMetricsResponse(
        total_simulations=total_simulations,
        total_captured_contacts=total_captured_contacts,
        total_converted_to_lead=total_converted_to_lead,
        conversion_rate=conversion_rate,
    )
