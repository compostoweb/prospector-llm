"""
services/anthropic_batch_service.py

Serviço para análise de leads via Anthropic Message Batches API.

A Batch API processa até 100.000 requests de forma assíncrona (até 24h),
com desconto de 50% sobre os preços padrão da Anthropic.

Fluxo:
  1. submit_lead_analysis_batch()  → submete batch, persiste AnthropicBatchJob
  2. poll_batch()                  → verifica status (chamado pelo worker periódico)
  3. process_batch_results()       → parse dos resultados JSONL + atualiza leads

ICP da Composto Web (MVP fixo):
  - Setores primários: financeiro, jurídico, saúde, indústria, varejo, TI
  - Cargos decisores: CFO, Controller, COO, CEO, CTO, Sócio, Diretor
  - Tamanho: médias e grandes empresas (50+ funcionários)
  - País: Brasil
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import structlog
from anthropic import AsyncAnthropic
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request as BatchRequest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.anthropic_batch_job import AnthropicBatchJob
from models.lead import Lead
from services.llm_config import resolve_anthropic_batch_model

if TYPE_CHECKING:
    pass

logger = structlog.get_logger()

# Prompt do sistema para análise de ICP
_ICP_SYSTEM_PROMPT = """Você é um especialista em qualificação de leads B2B para a Composto Web, empresa de tecnologia brasileira especializada em automação e sistemas de gestão empresarial.

ICP (Perfil Ideal de Cliente) da Composto Web:
- Setores prioritários: financeiro/contabilidade, jurídico/advocacia, saúde, indústria/manufatura, varejo/e-commerce, tecnologia
- Cargos decisores: CFO, Controller, COO, CEO, CTO, Diretor Financeiro, Diretor de Operações, Sócio, Gerente Financeiro
- Tamanho ideal: 50–5000 funcionários (médias e grandes empresas)
- País: Brasil (prioridade)
- Dores: processos manuais/Excel, fechamento demorado, falta de integração de sistemas, relatórios imprecisos

Sua tarefa: analisar os dados de um lead e retornar um JSON com a avaliação de fit."""

_ICP_USER_TEMPLATE = """Analise este lead e retorne um JSON com exatamente estas chaves:

Lead:
- Nome: {name}
- Cargo: {job_title}
- Empresa: {company}
- Setor/Indústria: {industry}
- Tamanho da empresa: {company_size}
- Localização: {location}
- Website: {website}

Retorne SOMENTE o JSON abaixo, sem texto adicional:
{{
  "icp_score": <número inteiro 0-100>,
  "icp_reasoning": "<frase curta explicando o score, máximo 100 caracteres>",
  "personalization_notes": "<1 a 2 ângulos de personalização específicos para este lead, máximo 200 caracteres>"
}}"""


def _build_lead_user_prompt(lead: Lead) -> str:
    return _ICP_USER_TEMPLATE.format(
        name=lead.name or "—",
        job_title=lead.job_title or "—",
        company=lead.company or "—",
        industry=lead.industry or "—",
        company_size=lead.company_size or "—",
        location=lead.location or lead.city or "—",
        website=lead.website or "—",
    )


async def submit_lead_analysis_batch(
    leads: list[Lead],
    tenant_id: uuid.UUID,
    db: AsyncSession,
    model: str | None = None,
    api_key: str | None = None,
) -> AnthropicBatchJob:
    """
    Submete um batch de leads para análise de ICP via Anthropic Batches API.

    Cada lead gera um request independente com custom_id = str(lead.id).
    Persiste um AnthropicBatchJob no banco para rastrear o status.

    Returns:
        AnthropicBatchJob recém-criado com status='in_progress'
    """
    if not leads:
        raise ValueError("Lista de leads vazia — nenhum batch submetido.")

    from core.config import settings

    effective_key = api_key or settings.ANTHROPIC_API_KEY
    if not effective_key:
        raise RuntimeError("ANTHROPIC_API_KEY não configurada.")

    effective_model = await resolve_anthropic_batch_model(db, tenant_id, model=model)

    client = AsyncAnthropic(api_key=effective_key)

    # Monta os requests do batch
    requests: list[BatchRequest] = []
    for lead in leads:
        user_prompt = _build_lead_user_prompt(lead)
        params: MessageCreateParamsNonStreaming = {
            "model": effective_model,
            "max_tokens": 256,
            "system": _ICP_SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        requests.append(
            BatchRequest(
                custom_id=str(lead.id),
                params=params,
            )
        )

    logger.info(
        "anthropic_batch.submitting",
        tenant_id=str(tenant_id),
        lead_count=len(leads),
        model=effective_model,
    )

    batch = await client.messages.batches.create(requests=requests)

    # Persiste o job no banco
    job = AnthropicBatchJob(
        tenant_id=tenant_id,
        anthropic_batch_id=batch.id,
        job_type="lead_analysis",
        status="in_progress",
        lead_ids_json=json.dumps([str(lead.id) for lead in leads]),
        request_count=len(leads),
        model=effective_model,
    )
    db.add(job)
    await db.flush()

    logger.info(
        "anthropic_batch.submitted",
        batch_id=batch.id,
        job_id=str(job.id),
        count=len(leads),
    )
    return job


async def poll_batch(
    job: AnthropicBatchJob,
    api_key: str | None = None,
) -> bool:
    """
    Verifica o status de um batch junto à Anthropic API.

    Atualiza job.status, job.results_url, job.ended_at e contadores in-place.

    Returns:
        True  se o batch terminou (status = "ended")
        False se ainda está em processamento
    """
    from core.config import settings

    effective_key = api_key or settings.ANTHROPIC_API_KEY
    if not effective_key:
        raise RuntimeError("ANTHROPIC_API_KEY não configurada.")

    client = AsyncAnthropic(api_key=effective_key)

    batch = await client.messages.batches.retrieve(job.anthropic_batch_id)

    job.status = batch.processing_status

    if batch.processing_status == "ended":
        job.ended_at = datetime.now(tz=UTC)
        job.results_url = str(batch.results_url) if batch.results_url else None

        counts = batch.request_counts
        job.succeeded_count = counts.succeeded
        job.failed_count = counts.errored
        job.expired_count = counts.expired

        logger.info(
            "anthropic_batch.ended",
            batch_id=job.anthropic_batch_id,
            succeeded=job.succeeded_count,
            failed=job.failed_count,
        )
        return True

    logger.debug(
        "anthropic_batch.still_processing",
        batch_id=job.anthropic_batch_id,
        status=batch.processing_status,
    )
    return False


async def process_batch_results(
    job: AnthropicBatchJob,
    db: AsyncSession,
    api_key: str | None = None,
) -> int:
    """
    Baixa os resultados JSONL do batch e atualiza os campos LLM dos leads.

    Tolerante a falhas individuais — loga erros mas continua processando.

    Returns:
        Número de leads atualizados com sucesso.
    """
    from core.config import settings

    effective_key = api_key or settings.ANTHROPIC_API_KEY
    if not effective_key:
        raise RuntimeError("ANTHROPIC_API_KEY não configurada.")

    client = AsyncAnthropic(api_key=effective_key)
    updated = 0
    analyzed_at = datetime.now(tz=UTC)

    async for result in await client.messages.batches.results(job.anthropic_batch_id):
        if result.result.type != "succeeded":
            logger.warning(
                "anthropic_batch.result_failed",
                custom_id=result.custom_id,
                result_type=result.result.type,
            )
            continue

        lead_id_str = result.custom_id
        text_parts: list[str] = []
        for block in result.result.message.content:
            block_text = getattr(block, "text", None)
            if isinstance(block_text, str):
                text_parts.append(block_text)
        text = "\n".join(text_parts)

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            logger.warning(
                "anthropic_batch.json_parse_error",
                custom_id=lead_id_str,
                raw=text[:200],
            )
            continue

        try:
            lead_uuid = uuid.UUID(lead_id_str)
        except ValueError:
            logger.warning("anthropic_batch.invalid_lead_id", custom_id=lead_id_str)
            continue

        result_row = await db.execute(
            select(Lead).where(
                Lead.id == lead_uuid,
                Lead.tenant_id == job.tenant_id,
            )
        )
        lead = result_row.scalar_one_or_none()
        if lead is None:
            logger.warning("anthropic_batch.lead_not_found", lead_id=lead_id_str)
            continue

        lead.llm_icp_score = float(parsed.get("icp_score", 0))
        lead.llm_icp_reasoning = str(parsed.get("icp_reasoning", ""))[:500]
        lead.llm_personalization_notes = str(parsed.get("personalization_notes", ""))[:1000]
        lead.llm_analyzed_at = analyzed_at

        updated += 1

    if updated:
        await db.commit()

    logger.info(
        "anthropic_batch.results_processed",
        batch_id=job.anthropic_batch_id,
        updated=updated,
    )
    return updated


async def get_pending_jobs(
    db: AsyncSession,
    limit: int = 50,
) -> list[AnthropicBatchJob]:
    """Retorna todos os jobs com status in_progress para polling."""
    result = await db.execute(
        select(AnthropicBatchJob).where(AnthropicBatchJob.status == "in_progress").limit(limit)
    )
    return list(result.scalars().all())
