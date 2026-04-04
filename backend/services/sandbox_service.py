"""
services/sandbox_service.py

Serviço de sandbox para teste de cadências antes de ativação.

Responsabilidades:
  - Criar sandbox runs com leads reais, amostra ou fictícios
  - Gerar mensagens via AIComposer (mesmo pipeline do dispatch)
  - Regenerar steps individualmente
  - Aprovar/rejeitar steps e runs
  - Simular replies automáticas (LLM) e manuais (ReplyParser)
  - Calcular timeline com rate limits simulados
  - Dry-run Pipedrive (busca real, deal de teste)
  - Iniciar cadência real a partir de sandbox aprovado
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.config import settings
from core.redis_client import redis_client
from integrations.context_fetcher import ContextFetcher
from integrations.llm import LLMMessage, LLMRegistry
from integrations.pipedrive_client import PipedriveClient
from models.cadence import Cadence
from models.tenant import TenantIntegration
from models.enums import (
    Channel,
    Intent,
    LeadStatus,
    SandboxLeadSource,
    SandboxRunStatus,
    SandboxStepStatus,
)
from models.lead import Lead
from models.lead_list import lead_list_members
from models.sandbox import SandboxRun, SandboxStep
from services.ai_composer import AIComposer, resolve_step_key, STEP_INSTRUCTIONS
from services.cadence_manager import cadence_manager, _resolve_template, get_template_step_config
from services.message_template_renderer import render_message_template, render_saved_email_template
from services.reply_parser import ReplyParser

logger = structlog.get_logger()

# ── Rate limits por canal ─────────────────────────────────────────────

CHANNEL_LIMITS: dict[str, int] = {
    Channel.LINKEDIN_CONNECT.value: settings.LIMIT_LINKEDIN_CONNECT,
    Channel.LINKEDIN_DM.value: settings.LIMIT_LINKEDIN_DM,
    Channel.EMAIL.value: settings.LIMIT_EMAIL,
}

# ── Templates de leads fictícios ─────────────────────────────────────

_FICTITIOUS_LEAD_TEMPLATES: list[dict[str, str]] = [
    {
        "name": "João Silva",
        "company": "TechCorp Brasil",
        "job_title": "CTO",
        "email": "joao.silva@techcorp.com.br",
        "industry": "Tecnologia",
        "city": "São Paulo",
        "linkedin_url": "https://linkedin.com/in/joaosilva-techcorp",
        "website": "https://techcorp.com.br",
    },
    {
        "name": "Maria Santos",
        "company": "HealthPlus",
        "job_title": "Diretora de Marketing",
        "email": "maria.santos@healthplus.com.br",
        "industry": "Saúde",
        "city": "Rio de Janeiro",
        "linkedin_url": "https://linkedin.com/in/mariasantos-health",
        "website": "https://healthplus.com.br",
    },
    {
        "name": "Carlos Mendes",
        "company": "FinServ Consultoria",
        "job_title": "CEO",
        "email": "carlos@finserv.com.br",
        "industry": "Finanças",
        "city": "Belo Horizonte",
        "linkedin_url": "https://linkedin.com/in/carlosmendes-finserv",
        "website": "https://finserv.com.br",
    },
    {
        "name": "Ana Oliveira",
        "company": "EduTech Academy",
        "job_title": "VP de Produto",
        "email": "ana.oliveira@edutech.com",
        "industry": "Educação",
        "city": "Curitiba",
        "linkedin_url": "https://linkedin.com/in/anaoliveira-edutech",
        "website": "https://edutech.com",
    },
    {
        "name": "Roberto Lima",
        "company": "LogiTrack Soluções",
        "job_title": "Diretor Comercial",
        "email": "roberto.lima@logitrack.com.br",
        "industry": "Logística",
        "city": "Campinas",
        "linkedin_url": "https://linkedin.com/in/robertolima-logi",
        "website": "https://logitrack.com.br",
    },
    {
        "name": "Fernanda Costa",
        "company": "GreenEnergy Brasil",
        "job_title": "Head de Parcerias",
        "email": "fernanda@greenenergy.com.br",
        "industry": "Energia",
        "city": "Florianópolis",
        "linkedin_url": "https://linkedin.com/in/fernandacosta-green",
        "website": "https://greenenergy.com.br",
    },
]

# ── Prompt para gerar variações de leads fictícios ───────────────────

_FICTITIOUS_VARIATION_PROMPT = """
Gere {count} leads fictícios variados para teste de prospecção B2B.
Cada lead deve ser único e diverso em: nome, empresa, cargo, setor, cidade.

IMPORTANTE:
- Nomes brasileiros realistas (diversidade de gênero e região)
- Empresas fictícias mas plausíveis
- Cargos de nível decisor (C-level, VP, Diretor, Head)
- Setores variados
- E-mails corporativos no formato nome@empresa.com.br
- URLs do LinkedIn fictícias no formato https://linkedin.com/in/nome-empresa

Retorne APENAS um JSON array, sem markdown, sem texto extra:
[
  {{"name": "...", "company": "...", "job_title": "...", "email": "...", "industry": "...", "city": "...", "linkedin_url": "...", "website": "..."}}
]
""".strip()

# ── Prompt para simular reply do lead ────────────────────────────────

_SIMULATE_REPLY_PROMPT = """
Você é {lead_name}, {job_title} na empresa {company} ({industry}).
Você recebeu a seguinte mensagem de prospecção via {channel}:

---
{message}
---

Escreva uma resposta realista e natural. Pode ser positiva, negativa, com objeção,
neutra ou qualquer outro tom. Seja breve (1-3 frases). Responda APENAS com o texto
da resposta, sem aspas, sem prefixos.
""".strip()


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


class SandboxService:
    """Orquestra todas as operações do sandbox de cadências."""

    # ── Criação ───────────────────────────────────────────────────────

    async def create_run(
        self,
        cadence_id: uuid.UUID,
        tenant_id: uuid.UUID,
        db: AsyncSession,
        registry: LLMRegistry,
        lead_ids: list[uuid.UUID] | None = None,
        lead_count: int = 3,
        use_fictitious: bool = False,
    ) -> SandboxRun:
        """Cria um sandbox run com steps para cada lead × step do template."""

        # Valida cadência pertence ao tenant
        cadence = await db.get(Cadence, cadence_id)
        if not cadence or cadence.tenant_id != tenant_id:
            raise ValueError("Cadência não encontrada ou acesso negado.")

        template = _resolve_template(cadence)
        now = _utcnow()

        # Determina fonte dos leads e gera dados
        if lead_ids:
            lead_source = SandboxLeadSource.REAL
            leads_data = await self._get_real_leads(lead_ids, tenant_id, db)
        elif use_fictitious:
            lead_source = SandboxLeadSource.FICTITIOUS
            leads_data = await self._generate_fictitious_leads(
                lead_count, registry, cadence
            )
        else:
            lead_source = SandboxLeadSource.SAMPLE
            leads_data = await self._get_sample_leads(
                cadence, tenant_id, db, lead_count
            )

        if not leads_data:
            raise ValueError("Nenhum lead disponível para o sandbox.")

        # Cria o run
        run = SandboxRun(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            cadence_id=cadence_id,
            status=SandboxRunStatus.RUNNING,
            lead_source=lead_source,
        )
        db.add(run)

        # Cria steps para cada lead × step do template
        for lead_data in leads_data:
            lead_id = lead_data.get("lead_id")
            fictitious = lead_data.get("fictitious_data")

            for step_number, (channel, day_offset, use_voice, _audio_file_id, step_type) in enumerate(
                template, start=1
            ):
                step = SandboxStep(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    sandbox_run_id=run.id,
                    lead_id=lead_id,
                    fictitious_lead_data=fictitious,
                    channel=channel,
                    step_number=step_number,
                    day_offset=day_offset,
                    use_voice=use_voice,
                    step_type=step_type,
                    scheduled_at_preview=now + timedelta(days=day_offset),
                    status=SandboxStepStatus.PENDING,
                )
                db.add(step)

        await db.flush()

        logger.info(
            "sandbox.run_created",
            run_id=str(run.id),
            cadence_id=str(cadence_id),
            lead_source=lead_source.value,
            leads=len(leads_data),
            template_steps=len(template),
        )

        # Re-carrega com steps
        await db.refresh(run, attribute_names=["steps"])
        return run

    # ── Geração de mensagens ──────────────────────────────────────────

    async def generate_all_steps(
        self,
        run_id: uuid.UUID,
        tenant_id: uuid.UUID,
        db: AsyncSession,
        registry: LLMRegistry,
    ) -> SandboxRun:
        """Gera mensagens IA para todos os steps pending do run."""

        run = await self._get_run(run_id, tenant_id, db)
        cadence = await db.get(Cadence, run.cadence_id)
        if not cadence:
            raise ValueError("Cadência não encontrada.")

        composer = AIComposer(registry)
        context_fetcher = ContextFetcher()

        # Calcula total de steps por lead para instruções contextuais
        template = _resolve_template(cadence)
        total_steps = len(template)

        # Mapa de canal anterior por step_number (do template)
        prev_channel_map: dict[int, str | None] = {}
        for idx, (ch, _day, _voice, _audio, _stype) in enumerate(template):
            prev_channel_map[idx + 1] = template[idx - 1][0].value if idx > 0 else None

        # Ordena steps por lead + step_number para processamento sequencial
        sorted_steps = sorted(run.steps, key=lambda s: (str(s.lead_id or ""), s.step_number))

        for step in sorted_steps:
            if step.status != SandboxStepStatus.PENDING:
                continue

            step.status = SandboxStepStatus.GENERATING
            await db.flush()

            previous_channel = prev_channel_map.get(step.step_number)

            try:
                content, email_subject, llm_info = await self._compose_step(
                    step, cadence, composer, context_fetcher, registry, db,
                    total_steps=total_steps,
                    previous_channel=previous_channel,
                )
                step.message_content = content
                step.llm_provider = llm_info.get("provider")
                step.llm_model = llm_info.get("model")
                step.tokens_in = llm_info.get("tokens_in")
                step.tokens_out = llm_info.get("tokens_out")

                # Subject extraído do JSON LLM em _compose_step (evita segunda chamada LLM)
                if step.channel == Channel.EMAIL:
                    step.email_subject = email_subject or await self._generate_email_subject(
                        step, cadence, registry, db
                    )

                # Gera áudio TTS para steps com use_voice
                if step.use_voice and step.message_content:
                    try:
                        audio_url = await self._generate_tts_preview(
                            cadence, step.message_content
                        )
                        step.audio_preview_url = audio_url
                    except Exception as tts_exc:
                        logger.warning(
                            "sandbox.tts_preview_error",
                            step_id=str(step.id),
                            error=str(tts_exc),
                        )

                step.status = SandboxStepStatus.GENERATED
            except Exception as exc:
                logger.error(
                    "sandbox.generate_step_error",
                    step_id=str(step.id),
                    error=str(exc),
                )
                step.status = SandboxStepStatus.PENDING  # volta para pending

            await db.flush()

        run.status = SandboxRunStatus.COMPLETED
        await db.flush()
        await db.refresh(run, attribute_names=["steps"])

        logger.info(
            "sandbox.all_steps_generated",
            run_id=str(run_id),
            generated=sum(1 for s in run.steps if s.status == SandboxStepStatus.GENERATED),
        )

        return run

    async def regenerate_step(
        self,
        step_id: uuid.UUID,
        tenant_id: uuid.UUID,
        db: AsyncSession,
        registry: LLMRegistry,
        temperature_override: float | None = None,
    ) -> SandboxStep:
        """Regenera a mensagem de um step específico."""

        step = await self._get_step(step_id, tenant_id, db)
        run = await self._get_run(step.sandbox_run_id, tenant_id, db)
        cadence = await db.get(Cadence, run.cadence_id)
        if not cadence:
            raise ValueError("Cadência não encontrada.")

        # Aplica override de temperatura se fornecido
        original_temp = cadence.llm_temperature
        if temperature_override is not None:
            cadence.llm_temperature = temperature_override

        composer = AIComposer(registry)
        context_fetcher = ContextFetcher()

        template = _resolve_template(cadence)
        total_steps = len(template)

        # Calcula previous_channel a partir do template
        prev_channel: str | None = None
        if step.step_number > 1 and len(template) >= step.step_number:
            prev_ch_enum = template[step.step_number - 2][0]
            prev_channel = prev_ch_enum.value if prev_ch_enum else None

        step.status = SandboxStepStatus.GENERATING
        await db.flush()

        try:
            content, email_subject, llm_info = await self._compose_step(
                step, cadence, composer, context_fetcher, registry, db,
                total_steps=total_steps,
                previous_channel=prev_channel,
            )
            step.message_content = content
            step.llm_provider = llm_info.get("provider")
            step.llm_model = llm_info.get("model")
            step.tokens_in = llm_info.get("tokens_in")
            step.tokens_out = llm_info.get("tokens_out")

            # Subject extraído do JSON LLM em _compose_step (evita segunda chamada LLM)
            if step.channel == Channel.EMAIL:
                step.email_subject = email_subject or await self._generate_email_subject(
                    step, cadence, registry, db
                )

            # Gera áudio TTS para steps com use_voice
            if step.use_voice and step.message_content:
                try:
                    audio_url = await self._generate_tts_preview(
                        cadence, step.message_content
                    )
                    step.audio_preview_url = audio_url
                except Exception as tts_exc:
                    logger.warning(
                        "sandbox.tts_regen_error",
                        step_id=str(step.id),
                        error=str(tts_exc),
                    )

            step.status = SandboxStepStatus.GENERATED
        finally:
            # Restaura temperatura original
            if temperature_override is not None:
                cadence.llm_temperature = original_temp

        await db.flush()
        return step

    # ── Aprovação / Rejeição ──────────────────────────────────────────

    async def approve_step(
        self,
        step_id: uuid.UUID,
        tenant_id: uuid.UUID,
        db: AsyncSession,
    ) -> SandboxStep:
        """Aprova um step individual."""
        step = await self._get_step(step_id, tenant_id, db)
        step.status = SandboxStepStatus.APPROVED
        await db.flush()
        return step

    async def reject_step(
        self,
        step_id: uuid.UUID,
        tenant_id: uuid.UUID,
        db: AsyncSession,
    ) -> SandboxStep:
        """Rejeita um step individual."""
        step = await self._get_step(step_id, tenant_id, db)
        step.status = SandboxStepStatus.REJECTED
        await db.flush()
        return step

    async def approve_run(
        self,
        run_id: uuid.UUID,
        tenant_id: uuid.UUID,
        db: AsyncSession,
    ) -> tuple[SandboxRun, int]:
        """Aprova todos os steps do run e marca run como approved."""
        run = await self._get_run(run_id, tenant_id, db)
        approved_count = 0

        for step in run.steps:
            if step.status in (
                SandboxStepStatus.GENERATED,
                SandboxStepStatus.PENDING,
            ):
                step.status = SandboxStepStatus.APPROVED
                approved_count += 1

        run.status = SandboxRunStatus.APPROVED
        await db.flush()
        await db.refresh(run, attribute_names=["steps"])

        return run, approved_count

    # ── Start real ────────────────────────────────────────────────────

    async def start_from_sandbox(
        self,
        run_id: uuid.UUID,
        tenant_id: uuid.UUID,
        db: AsyncSession,
    ) -> dict[str, int]:
        """Inicia cadência real a partir de sandbox aprovado."""
        run = await self._get_run(run_id, tenant_id, db)

        if run.status not in (SandboxRunStatus.APPROVED, SandboxRunStatus.COMPLETED):
            raise ValueError(
                f"Sandbox run deve estar 'approved' ou 'completed' para iniciar. "
                f"Status atual: {run.status.value}"
            )

        cadence = await db.get(Cadence, run.cadence_id)
        if not cadence:
            raise ValueError("Cadência não encontrada.")

        # Coleta lead_ids únicos (só leads reais)
        real_lead_ids: set[uuid.UUID] = set()
        for step in run.steps:
            if step.lead_id is not None:
                real_lead_ids.add(step.lead_id)

        leads_enrolled = 0
        steps_created = 0

        for lead_id in real_lead_ids:
            lead = await db.get(Lead, lead_id)
            if not lead or lead.tenant_id != tenant_id:
                continue
            if lead.status == LeadStatus.IN_CADENCE:
                continue  # já enrolled

            new_steps = await cadence_manager.enroll(lead, cadence, db)
            if new_steps:
                leads_enrolled += 1
                steps_created += len(new_steps)

        # Ativa cadência se não estiver ativa
        if not cadence.is_active:
            cadence.is_active = True

        await db.flush()

        logger.info(
            "sandbox.started_real_cadence",
            run_id=str(run_id),
            cadence_id=str(cadence.id),
            leads_enrolled=leads_enrolled,
            steps_created=steps_created,
        )

        return {
            "leads_enrolled": leads_enrolled,
            "steps_created": steps_created,
        }

    # ── Simulação de replies ──────────────────────────────────────────

    async def simulate_reply_auto(
        self,
        step_id: uuid.UUID,
        tenant_id: uuid.UUID,
        db: AsyncSession,
        registry: LLMRegistry,
    ) -> SandboxStep:
        """Gera reply automática via LLM e classifica com ReplyParser."""
        step = await self._get_step(step_id, tenant_id, db)

        if not step.message_content:
            raise ValueError("Step ainda não tem mensagem gerada.")

        # Dados do lead
        lead_info = await self._get_lead_info(step, db)

        # Gera reply via LLM
        run = await self._get_run(step.sandbox_run_id, tenant_id, db)
        cadence = await db.get(Cadence, run.cadence_id)
        if not cadence:
            raise ValueError("Cadência não encontrada.")

        prompt = _SIMULATE_REPLY_PROMPT.format(
            lead_name=lead_info["name"],
            job_title=lead_info["job_title"],
            company=lead_info["company"],
            industry=lead_info.get("industry", "Não informado"),
            channel=step.channel.value,
            message=step.message_content,
        )

        from integrations.llm import LLMMessage, LLMResponse

        response: LLMResponse = await registry.complete(
            messages=[LLMMessage(role="user", content=prompt)],
            provider=cadence.llm_provider,
            model=cadence.llm_model,
            temperature=0.8,  # mais criatividade na simulação
            max_tokens=256,
        )

        reply_text = response.text.strip()

        # Classifica com ReplyParser
        return await self._classify_and_save_reply(step, reply_text, lead_info["name"], registry, db)

    async def simulate_reply_manual(
        self,
        step_id: uuid.UUID,
        tenant_id: uuid.UUID,
        db: AsyncSession,
        registry: LLMRegistry,
        reply_text: str,
    ) -> SandboxStep:
        """Classifica reply manual com ReplyParser."""
        step = await self._get_step(step_id, tenant_id, db)
        lead_info = await self._get_lead_info(step, db)

        return await self._classify_and_save_reply(step, reply_text, lead_info["name"], registry, db)

    # ── Rate limits ───────────────────────────────────────────────────

    async def calculate_rate_limited_timeline(
        self,
        run_id: uuid.UUID,
        tenant_id: uuid.UUID,
        db: AsyncSession,
    ) -> SandboxRun:
        """Calcula timeline com rate limits simulados para cada step."""
        run = await self._get_run(run_id, tenant_id, db)

        # Conta envios simulados por canal/dia (dentro do próprio sandbox)
        daily_counts: dict[str, dict[str, int]] = {}  # {date_str: {channel: count}}

        # Primeiro, consulta os rate limits atuais reais do tenant via Redis
        real_usage: dict[str, dict[str, int]] = {}  # {date_str: {channel: current_count}}

        sorted_steps = sorted(run.steps, key=lambda s: s.scheduled_at_preview)

        for step in sorted_steps:
            date_str = step.scheduled_at_preview.strftime("%Y-%m-%d")
            channel_val = step.channel.value
            limit = CHANNEL_LIMITS.get(channel_val, 999)

            # Busca uso real do Redis (cache por data)
            if date_str not in real_usage:
                real_usage[date_str] = {}
            if channel_val not in real_usage[date_str]:
                redis_key = f"ratelimit:{tenant_id}:{channel_val}:{date_str}"
                current = await redis_client.get(redis_key)
                real_usage[date_str][channel_val] = int(current) if current else 0

            # Conta acumulado: real + sandbox
            if date_str not in daily_counts:
                daily_counts[date_str] = {}
            if channel_val not in daily_counts[date_str]:
                daily_counts[date_str][channel_val] = real_usage[date_str][channel_val]

            daily_counts[date_str][channel_val] += 1
            total_for_day = daily_counts[date_str][channel_val]

            if total_for_day > limit:
                step.is_rate_limited = True
                step.rate_limit_reason = (
                    f"Limite de {limit} {channel_val}/dia atingido "
                    f"({total_for_day - 1} já agendados)"
                )
                # Calcula próximo dia com slot livre
                adjusted = self._find_next_available_slot(
                    step.scheduled_at_preview, channel_val, limit, daily_counts, real_usage
                )
                step.adjusted_scheduled_at = adjusted

                # Adiciona ao dia ajustado
                adj_date = adjusted.strftime("%Y-%m-%d")
                if adj_date not in daily_counts:
                    daily_counts[adj_date] = {}
                if channel_val not in daily_counts[adj_date]:
                    daily_counts[adj_date][channel_val] = real_usage.get(adj_date, {}).get(channel_val, 0)
                daily_counts[adj_date][channel_val] += 1
            else:
                step.is_rate_limited = False
                step.rate_limit_reason = None
                step.adjusted_scheduled_at = None

        await db.flush()
        await db.refresh(run, attribute_names=["steps"])
        return run

    # ── Pipedrive dry-run ─────────────────────────────────────────────

    async def dry_run_pipedrive(
        self,
        run_id: uuid.UUID,
        tenant_id: uuid.UUID,
        db: AsyncSession,
    ) -> list[dict]:
        """Faz dry-run de integração Pipedrive para leads com intent relevante."""
        run = await self._get_run(run_id, tenant_id, db)
        client = PipedriveClient()

        # Coleta leads com intent INTEREST ou OBJECTION
        relevant_steps: dict[uuid.UUID | str, SandboxStep] = {}
        for step in run.steps:
            if step.simulated_intent in (Intent.INTEREST, Intent.OBJECTION):
                key = step.lead_id or str(step.id)  # fictícios usam step.id como key
                if key not in relevant_steps:
                    relevant_steps[key] = step

        results: list[dict] = []

        for step in relevant_steps.values():
            lead_info = await self._get_lead_info(step, db)
            email = lead_info.get("email")

            # Busca person real no Pipedrive
            person_id = None
            person_exists = False
            if email:
                person_id = await client.find_person_by_email(email)
                person_exists = person_id is not None

            # Monta preview do deal
            intent_label = step.simulated_intent.value if step.simulated_intent else "unknown"
            stage_id = (
                settings.PIPEDRIVE_STAGE_INTEREST
                if step.simulated_intent == Intent.INTEREST
                else settings.PIPEDRIVE_STAGE_OBJECTION
            )

            deal_title = f"[SANDBOX TEST] Prospector — {lead_info.get('company', 'N/A')}"
            note_content = (
                f"Sandbox dry-run — Lead: {lead_info['name']}\n"
                f"Intent: {intent_label}\n"
                f"Confiança: {step.simulated_confidence or 0:.0%}\n"
                f"Resumo: {step.simulated_reply_summary or 'N/A'}\n"
                f"Mensagem original: {(step.message_content or '')[:200]}..."
            )

            results.append({
                "lead_name": lead_info["name"],
                "lead_company": lead_info.get("company"),
                "intent": intent_label,
                "person": {
                    "name": lead_info["name"],
                    "email": email,
                    "person_exists": person_exists,
                    "person_id": person_id,
                },
                "deal": {
                    "title": deal_title,
                    "stage": f"stage_{stage_id}" if stage_id else "default",
                    "value": 0.0,
                },
                "note_preview": note_content,
            })

        # Salva preview no run
        run.pipedrive_dry_run = {"leads": results}
        await db.flush()

        return results

    async def push_to_pipedrive(
        self,
        run_id: uuid.UUID,
        tenant_id: uuid.UUID,
        db: AsyncSession,
    ) -> list[dict]:
        """Envia leads relevantes do sandbox para o Pipedrive (person + deal + nota)."""
        run = await self._get_run(run_id, tenant_id, db)

        # Busca credenciais Pipedrive do tenant
        result = await db.execute(
            select(TenantIntegration).where(TenantIntegration.tenant_id == tenant_id)
        )
        integration = result.scalar_one_or_none()
        if not integration or not integration.pipedrive_api_token:
            raise ValueError("Pipedrive não configurado para este tenant.")

        client = PipedriveClient(
            token=integration.pipedrive_api_token,
            domain=integration.pipedrive_domain,
        )
        stage_interest = integration.pipedrive_stage_interest
        stage_objection = integration.pipedrive_stage_objection
        owner_id = integration.pipedrive_owner_id

        # Coleta leads com intent INTEREST ou OBJECTION
        relevant_steps: dict[uuid.UUID | str, SandboxStep] = {}
        for step in run.steps:
            if step.simulated_intent in (Intent.INTEREST, Intent.OBJECTION):
                key = step.lead_id or str(step.id)
                if key not in relevant_steps:
                    relevant_steps[key] = step

        if not relevant_steps:
            raise ValueError(
                "Nenhum lead com intent INTEREST ou OBJECTION encontrado. "
                "Simule replies antes de enviar ao Pipedrive."
            )

        results: list[dict] = []

        for step in relevant_steps.values():
            lead_info = await self._get_lead_info(step, db)
            lead_name = lead_info["name"]
            email = lead_info.get("email")
            company = lead_info.get("company")

            try:
                # 1) Find or create organization
                org_id: int | None = None
                if company:
                    org_id = await client.find_or_create_organization(name=company)

                # 2) Find or create person (vinculado à org)
                person_id = await client.find_or_create_person(
                    name=lead_name,
                    email=email,
                    linkedin_url=lead_info.get("linkedin_url"),
                    org_id=org_id,
                )

                # 3) Create deal (somente se person foi criado)
                intent_label = step.simulated_intent.value if step.simulated_intent else "unknown"
                deal_id: int | None = None
                if person_id:
                    stage_id = (
                        stage_interest
                        if step.simulated_intent == Intent.INTEREST
                        else stage_objection
                    )
                    deal_title = f"[SANDBOX] Prospector - {company or 'N/A'}"

                    deal_id = await client.create_deal(
                        title=deal_title,
                        person_id=person_id,
                        stage_id=stage_id,
                        owner_id=owner_id,
                        org_id=org_id,
                    )

                # 3) Add note
                note_added = False
                if deal_id:
                    note_content = (
                        f"<b>Sandbox Test — Prospector</b><br>"
                        f"Lead: {lead_name}<br>"
                        f"Empresa: {lead_info.get('company', 'N/A')}<br>"
                        f"Intent: {intent_label}<br>"
                        f"Confiança: {step.simulated_confidence or 0:.0%}<br>"
                        f"Resumo: {step.simulated_reply_summary or 'N/A'}<br><br>"
                        f"<b>Mensagem enviada:</b><br>"
                        f"{(step.message_content or 'N/A')[:500]}<br><br>"
                        f"<b>Resposta simulada:</b><br>"
                        f"{(step.simulated_reply or 'N/A')[:500]}"
                    )
                    note_added = await client.add_note(deal_id, note_content)

                results.append({
                    "lead_name": lead_name,
                    "person_id": person_id,
                    "deal_id": deal_id,
                    "note_added": note_added,
                    "error": None,
                })

                logger.info(
                    "sandbox.pipedrive_pushed",
                    lead_name=lead_name,
                    person_id=person_id,
                    deal_id=deal_id,
                )

            except Exception as exc:
                logger.error(
                    "sandbox.pipedrive_push_error",
                    lead_name=lead_name,
                    error=str(exc),
                )
                results.append({
                    "lead_name": lead_name,
                    "person_id": None,
                    "deal_id": None,
                    "note_added": False,
                    "error": str(exc),
                })

        return results

    # ── Helpers privados ──────────────────────────────────────────────

    async def _get_run(
        self,
        run_id: uuid.UUID,
        tenant_id: uuid.UUID,
        db: AsyncSession,
    ) -> SandboxRun:
        """Carrega run com steps, valida tenant."""
        result = await db.execute(
            select(SandboxRun)
            .options(selectinload(SandboxRun.steps))
            .where(SandboxRun.id == run_id, SandboxRun.tenant_id == tenant_id)
        )
        run = result.scalar_one_or_none()
        if not run:
            raise ValueError("Sandbox run não encontrado.")
        return run

    async def _get_step(
        self,
        step_id: uuid.UUID,
        tenant_id: uuid.UUID,
        db: AsyncSession,
    ) -> SandboxStep:
        """Carrega step, valida tenant."""
        result = await db.execute(
            select(SandboxStep)
            .where(SandboxStep.id == step_id, SandboxStep.tenant_id == tenant_id)
        )
        step = result.scalar_one_or_none()
        if not step:
            raise ValueError("Sandbox step não encontrado.")
        return step

    async def _get_real_leads(
        self,
        lead_ids: list[uuid.UUID],
        tenant_id: uuid.UUID,
        db: AsyncSession,
    ) -> list[dict]:
        """Busca leads reais e retorna lista de dicts com lead_id."""
        result = await db.execute(
            select(Lead).where(Lead.id.in_(lead_ids), Lead.tenant_id == tenant_id)
        )
        leads = result.scalars().all()
        return [{"lead_id": lead.id, "fictitious_data": None} for lead in leads]

    async def _get_sample_leads(
        self,
        cadence: Cadence,
        tenant_id: uuid.UUID,
        db: AsyncSession,
        count: int,
    ) -> list[dict]:
        """Busca amostra aleatória de leads da lead_list da cadência."""
        query = select(Lead).where(Lead.tenant_id == tenant_id)

        if cadence.lead_list_id:
            query = query.join(
                lead_list_members,
                (lead_list_members.c.lead_id == Lead.id)
                & (lead_list_members.c.lead_list_id == cadence.lead_list_id),
            )

        query = query.order_by(func.random()).limit(count)
        result = await db.execute(query)
        leads = result.scalars().all()
        return [{"lead_id": lead.id, "fictitious_data": None} for lead in leads]

    async def _generate_fictitious_leads(
        self,
        count: int,
        registry: LLMRegistry,
        cadence: Cadence,
    ) -> list[dict]:
        """Gera leads fictícios: templates base + variações via LLM."""
        # Se count <= templates disponíveis, usa direto
        if count <= len(_FICTITIOUS_LEAD_TEMPLATES):
            templates = _FICTITIOUS_LEAD_TEMPLATES[:count]
            return [
                {"lead_id": None, "fictitious_data": t}
                for t in templates
            ]

        # Gera via LLM para ter mais variedade
        import json

        prompt = _FICTITIOUS_VARIATION_PROMPT.format(count=count)
        response = await registry.complete(
            messages=[LLMMessage(role="user", content=prompt)],
            provider=cadence.llm_provider,
            model=cadence.llm_model,
            temperature=0.9,
            max_tokens=2048,
        )

        try:
            leads_data = json.loads(response.text)
            if not isinstance(leads_data, list):
                raise ValueError("Resposta LLM não é uma lista")
        except (json.JSONDecodeError, ValueError):
            logger.warning("sandbox.fictitious_llm_fallback", raw=response.text[:200])
            # Fallback: usa templates
            leads_data = _FICTITIOUS_LEAD_TEMPLATES[:count]

        return [
            {"lead_id": None, "fictitious_data": lead}
            for lead in leads_data[:count]
        ]

    async def _compose_step(
        self,
        step: SandboxStep,
        cadence: Cadence,
        composer: AIComposer,
        context_fetcher: ContextFetcher,
        registry: LLMRegistry,
        db: AsyncSession,
        total_steps: int = 1,
        previous_channel: str | None = None,
    ) -> tuple[str, str | None, dict]:
        """Compõe mensagem para um step usando o mesmo pipeline do dispatch.

        Returns:
            Tuple[content, email_subject, llm_info]
            email_subject é preenchido apenas para Canal EMAIL (extraído do JSON LLM).
        """
        template_step = get_template_step_config(cadence, step.step_number)
        llm_bypassed_info = {
            "provider": None,
            "model": None,
            "tokens_in": None,
            "tokens_out": None,
        }

        # Rastreia company/name para fallback do parser de email
        _company: str | None = None
        _name: str | None = None
        lead_proxy: object

        if step.lead_id:
            # Lead real — busca via query async (não usar step.lead por lazy loading)
            from sqlalchemy import select as sa_select

            result = await db.execute(
                sa_select(Lead).where(Lead.id == step.lead_id)
            )
            lead = result.scalar_one_or_none()
            if not lead:
                raise ValueError(f"Lead {step.lead_id} não encontrado.")

            lead_proxy = lead

            _company = lead.company
            _name = lead.name

            context: dict = {}
            if lead.website:
                site_content = await context_fetcher.fetch_from_website(lead.website)
                context["site_summary"] = site_content
            elif lead.company:
                search_content = await context_fetcher.search_company(lead.company)
                context["site_summary"] = search_content

            # Usa AIComposer diretamente
            from integrations.llm import LLMResponse

            user_prompt = _build_sandbox_user_prompt(
                name=lead.name,
                company=lead.company,
                segment=lead.segment,
                linkedin_url=lead.linkedin_url,
                channel=step.channel.value,
                step_number=step.step_number,
                context=context,
                total_steps=total_steps,
                use_voice=step.use_voice,
                previous_channel=previous_channel,
                job_title=lead.job_title,
                industry=lead.industry,
                company_size=lead.company_size,
                location=lead.location or lead.city,
                cadence=cadence,
                step_type=step.step_type,
            )
        else:
            # Lead fictício
            from types import SimpleNamespace

            fdata = step.fictitious_lead_data or {}
            lead_proxy = SimpleNamespace(
                name=fdata.get("name", "Lead Teste"),
                company=fdata.get("company"),
                first_name=fdata.get("name", "Lead Teste").split(" ")[0],
                last_name=" ".join(fdata.get("name", "Lead Teste").split(" ")[1:]),
                job_title=fdata.get("job_title"),
                industry=fdata.get("industry"),
                city=fdata.get("city"),
                location=fdata.get("city"),
                company_size=fdata.get("company_size"),
                website=fdata.get("website"),
                linkedin_url=fdata.get("linkedin_url"),
                email=fdata.get("email"),
            )
            _company = fdata.get("company")
            _name = fdata.get("name", "Lead Teste")
            context = {"site_summary": f"Empresa fictícia: {fdata.get('company', 'N/A')} - Setor: {fdata.get('industry', 'N/A')}"}

            user_prompt = _build_sandbox_user_prompt(
                name=fdata.get("name", "Lead Teste"),
                company=fdata.get("company"),
                segment=fdata.get("industry"),
                linkedin_url=fdata.get("linkedin_url"),
                channel=step.channel.value,
                step_number=step.step_number,
                context=context,
                total_steps=total_steps,
                use_voice=step.use_voice,
                previous_channel=previous_channel,
                job_title=fdata.get("job_title"),
                industry=fdata.get("industry"),
                company_size=fdata.get("company_size"),
                location=fdata.get("city"),
                cadence=cadence,
                step_type=step.step_type,
            )

        configured_message = render_message_template(
            template_step.get("message_template") if template_step else None,
            lead_proxy,
        )
        subject_variants = template_step.get("subject_variants") if template_step else None
        configured_email_template_id = template_step.get("email_template_id") if template_step else None

        if step.channel == Channel.EMAIL and configured_email_template_id:
            from models.email_template import EmailTemplate

            try:
                template_result = await db.execute(
                    select(EmailTemplate).where(
                        EmailTemplate.id == uuid.UUID(str(configured_email_template_id)),
                        EmailTemplate.tenant_id == cadence.tenant_id,
                        EmailTemplate.is_active.is_(True),
                    )
                )
                email_template = template_result.scalar_one_or_none()
            except ValueError:
                email_template = None

            if email_template is not None:
                subject, body = render_saved_email_template(email_template, lead_proxy)
                cleaned_variants = [str(item).strip() for item in (subject_variants or []) if str(item).strip()]
                if cleaned_variants:
                    subject = cleaned_variants[0]
                return body, subject, llm_bypassed_info

        if configured_message:
            email_subject: str | None = None
            if step.channel == Channel.EMAIL:
                cleaned_variants = [str(item).strip() for item in (subject_variants or []) if str(item).strip()]
                if cleaned_variants:
                    email_subject = cleaned_variants[0]
            return configured_message, email_subject, llm_bypassed_info

        from services.ai_composer import COMPOSER_SYSTEM_PROMPT

        messages = [
            LLMMessage(role="system", content=COMPOSER_SYSTEM_PROMPT),
            LLMMessage(role="user", content=user_prompt),
        ]

        from integrations.llm import LLMResponse

        response: LLMResponse = await registry.complete(
            messages=messages,
            provider=cadence.llm_provider,
            model=cadence.llm_model,
            temperature=cadence.llm_temperature,
            max_tokens=cadence.llm_max_tokens,
        )

        llm_info = {
            "provider": response.provider,
            "model": response.model,
            "tokens_in": response.input_tokens,
            "tokens_out": response.output_tokens,
        }

        # Para EMAIL: instrução já pede JSON {subject, body} — extrai aqui para evitar segunda chamada LLM
        if step.channel == Channel.EMAIL:
            from services.ai_composer import _parse_email_json
            from types import SimpleNamespace

            _lead_proxy = SimpleNamespace(company=_company, name=_name)
            email_subject, email_body = _parse_email_json(
                response.text.strip(), _lead_proxy, step.step_number
            )
            return email_body, email_subject, llm_info

        return response.text.strip(), None, llm_info

    async def _generate_tts_preview(
        self,
        cadence: Cadence,
        text: str,
    ) -> str:
        """Gera áudio TTS preview, armazena no Redis e retorna URL."""
        from integrations.tts import TTSRegistry

        tts_registry = TTSRegistry(settings=settings, redis=redis_client)
        tts_provider = cadence.tts_provider or settings.VOICE_PROVIDER
        tts_voice_id = cadence.tts_voice_id or settings.SPEECHIFY_VOICE_ID
        tts_speed = getattr(cadence, "tts_speed", 1.0) or 1.0
        tts_pitch = getattr(cadence, "tts_pitch", 0.0) or 0.0

        # Fallback: se o provider configurado não estiver disponível, usa edge
        available = list(tts_registry._providers.keys())
        if tts_provider not in available and "edge" in available:
            logger.info(
                "sandbox.tts_fallback",
                requested=tts_provider,
                fallback="edge",
            )
            tts_provider = "edge"
            tts_voice_id = settings.EDGE_TTS_DEFAULT_VOICE

        audio_bytes = await tts_registry.synthesize(
            provider=tts_provider,
            voice_id=tts_voice_id,
            text=text,
            speed=tts_speed,
            pitch=tts_pitch,
        )
        audio_key = str(uuid.uuid4())
        await redis_client.set_bytes(f"audio:{audio_key}", audio_bytes, ttl=3600)
        return f"{settings.API_PUBLIC_URL}/audio/{audio_key}"

    async def _generate_email_subject(
        self,
        step: SandboxStep,
        cadence: Cadence,
        registry: LLMRegistry,
        db: AsyncSession,
    ) -> str:
        """Gera assunto de email via LLM."""
        lead_info = await self._get_lead_info(step, db)

        prompt = (
            f"Gere um assunto de email curto e atraente para uma mensagem de prospecção B2B.\n"
            f"Lead: {lead_info['name']} da {lead_info.get('company', 'N/A')}\n"
            f"Step {step.step_number} da cadência.\n"
            f"Resumo da mensagem: {(step.message_content or '')[:300]}\n\n"
            f"Retorne APENAS o assunto, sem aspas."
        )

        response = await registry.complete(
            messages=[LLMMessage(role="user", content=prompt)],
            provider=cadence.llm_provider,
            model=cadence.llm_model,
            temperature=0.7,
            max_tokens=64,
        )
        return response.text.strip()

    async def _get_lead_info(self, step: SandboxStep, db: AsyncSession) -> dict:
        """Retorna info do lead (real ou fictício)."""
        if step.lead_id:
            lead = await db.get(Lead, step.lead_id)
            if lead:
                return {
                    "name": lead.name,
                    "company": lead.company,
                    "job_title": lead.job_title,
                    "email": lead.email_corporate or lead.email_personal,
                    "industry": lead.industry,
                    "linkedin_url": lead.linkedin_url,
                }
        # Fictício ou lead não encontrado
        fdata = step.fictitious_lead_data or {}
        return {
            "name": fdata.get("name", "Lead Teste"),
            "company": fdata.get("company"),
            "job_title": fdata.get("job_title"),
            "email": fdata.get("email"),
            "industry": fdata.get("industry"),
            "linkedin_url": fdata.get("linkedin_url"),
        }

    async def _classify_and_save_reply(
        self,
        step: SandboxStep,
        reply_text: str,
        lead_name: str,
        registry: LLMRegistry,
        db: AsyncSession,
    ) -> SandboxStep:
        """Classifica reply e salva resultado no step."""
        parser = ReplyParser(
            registry=registry,
            provider=settings.REPLY_PARSER_PROVIDER,
            model=settings.REPLY_PARSER_MODEL,
        )

        result = await parser.classify(reply_text, lead_name)

        step.simulated_reply = reply_text
        step.simulated_intent = Intent(result.get("intent", "neutral").lower())
        step.simulated_confidence = result.get("confidence", 0.0)
        step.simulated_reply_summary = result.get("summary")

        await db.flush()

        logger.info(
            "sandbox.reply_simulated",
            step_id=str(step.id),
            intent=step.simulated_intent.value if step.simulated_intent else None,
            confidence=step.simulated_confidence,
        )

        return step

    def _find_next_available_slot(
        self,
        original_dt: datetime,
        channel: str,
        limit: int,
        daily_counts: dict[str, dict[str, int]],
        real_usage: dict[str, dict[str, int]],
    ) -> datetime:
        """Encontra o próximo dia com slot livre para o canal."""
        check_dt = original_dt + timedelta(days=1)
        for _ in range(30):  # máximo 30 dias à frente
            date_str = check_dt.strftime("%Y-%m-%d")
            current = daily_counts.get(date_str, {}).get(channel, 0)
            real = real_usage.get(date_str, {}).get(channel, 0)
            total = max(current, real)
            if total < limit:
                return check_dt
            check_dt += timedelta(days=1)
        return check_dt  # fallback: 30 dias depois


# ── Helper para montar prompt ─────────────────────────────────────────

def _build_sandbox_user_prompt(
    name: str,
    company: str | None,
    segment: str | None,
    linkedin_url: str | None,
    channel: str,
    step_number: int,
    context: dict,
    total_steps: int = 1,
    use_voice: bool = False,
    previous_channel: str | None = None,
    job_title: str | None = None,
    industry: str | None = None,
    company_size: str | None = None,
    location: str | None = None,
    cadence: Cadence | None = None,
    step_type: str | None = None,
) -> str:
    site_summary = context.get("site_summary", "Não disponível")

    step_key = resolve_step_key(
        channel, step_number, total_steps, use_voice, previous_channel, step_type=step_type,
    )
    step_instruction = STEP_INSTRUCTIONS.get(step_key, "")

    # Dados ricos do lead
    lead_lines = [
        f"Nome: {name}",
        f"Cargo: {job_title or 'Não informado'}",
        f"Empresa: {company or 'Não informado'}",
        f"Setor/indústria: {industry or 'Não informado'}",
        f"Porte da empresa: {company_size or 'Não informado'}",
        f"Segmento: {segment or 'Não informado'}",
        f"Localização: {location or 'Não informado'}",
    ]
    if linkedin_url:
        lead_lines.append(f"LinkedIn: {linkedin_url}")

    # Contexto da cadência (segmento-alvo, persona, oferta)
    cadence_context_lines: list[str] = []
    if cadence:
        if cadence.target_segment:
            cadence_context_lines.append(f"Segmento-alvo desta campanha: {cadence.target_segment}")
        if cadence.persona_description:
            cadence_context_lines.append(f"Persona ideal: {cadence.persona_description}")
        if cadence.offer_description:
            cadence_context_lines.append(f"O que oferecemos (use com sutileza, SÓ em steps avançados): {cadence.offer_description}")
        if cadence.tone_instructions:
            cadence_context_lines.append(f"Instruções extras de tom: {cadence.tone_instructions}")

    cadence_block = "\n".join(cadence_context_lines) if cadence_context_lines else "Não configurado"

    return f"""
{step_instruction}

---

DADOS DO LEAD:
{chr(10).join(lead_lines)}

CONTEXTO DA CAMPANHA:
{cadence_block}

PESQUISA SOBRE A EMPRESA:
{site_summary}

POSIÇÃO NA CADÊNCIA: Step {step_number} de {total_steps}.

Escreva a mensagem agora:
""".strip()


# Singleton
sandbox_service = SandboxService()
