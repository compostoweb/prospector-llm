"""
workers/content_engagement.py

Task Celery para o LinkedIn Engagement Scanner do Content Hub.

Task principal:
  run_engagement_scan(session_id, tenant_id, keywords, icp_titles, icp_sectors)
    — Etapa 1: garimpagem de posts de referencia via Apify
    — Etapa 2: garimpagem de posts de ICP via Apify
    — Etapa 3: analise LLM dos posts (hook/pilar para referencias, relevancia para ICP)
    — Etapa 4: geracao de 2 comentarios por post de ICP relevante
        — Fila: "content-engagement"

IMPORTANTE: nenhum comentario e postado automaticamente.
O usuario revisa e posta manualmente pela interface.
"""

from __future__ import annotations

import asyncio
import re
import uuid
from datetime import UTC, datetime

import structlog

from workers.celery_app import celery_app

logger = structlog.get_logger()

# ── Constantes de engajamento ──────────────────────────────────────────────────
# Usadas como fallback quando nenhum keyword/titulo e passado na request
# Cobertura: Automação · Integração · IA · Cloud/DevOps · Telefonia ·
#            Software sob Medida · CRM/Growth · Gestão Operacional

DEFAULT_ENGAGEMENT_KEYWORDS: list[str] = [
    # AUTOMAÇÃO DE PROCESSOS
    "automação de processos empresa",
    "processo manual retrabalho",
    "gargalo operacional crescimento",
    "RPA robô processo",
    "eliminar tarefa manual equipe",
    "operação que não escala",
    # INTEGRAÇÃO DE SISTEMAS
    "integração de sistemas ERP",
    "sistemas desconectados operação",
    "dado defasado decisão",
    "ERP CRM não integrado",
    "fechamento mensal manual planilha",
    "redigitação dado entre sistemas",
    # IA APLICADA AO NEGÓCIO
    "IA empresas resultado prático",
    "inteligência artificial operação",
    "agente IA atendimento empresa",
    "ChatGPT empresa dado seguro",
    "modelo IA negócio aplicado",
    "IA privada dado confidencial",
    # CLOUD E INFRAESTRUTURA
    "cloud migração empresa",
    "infraestrutura TI custo",
    "modernização tecnológica empresa",
    "LGPD conformidade sistema",
    "segurança dados empresa",
    "DevOps entrega contínua",
    # TELEFONIA E COMUNICAÇÃO
    "PABX IP nuvem empresa",
    "telefonia integrada CRM",
    "custo telefonia empresa redução",
    "atendimento telefônico rastreável",
    # SOFTWARE SOB MEDIDA
    "software personalizado empresa",
    "sistema próprio versus SaaS",
    "propriedade intelectual software",
    "lock-in fornecedor tecnologia",
    "SaaS custo escala empresa",
    "ativo digital empresa",
    # CRM E CRESCIMENTO COMERCIAL
    "CRM implementação resultado",
    "Pipedrive vendas processo",
    "pipeline comercial estruturado",
    "funil vendas dados",
    "aquisição clientes rastreável",
    "tracking marketing vendas",
    # GESTÃO E OPERAÇÃO GERAL
    "escalar empresa sem contratar",
    "crescimento operacional tecnologia",
    "dado tempo real decisão gestão",
    "tecnologia parceiro estratégico",
    "operação cresceu processo não acompanhou",
    "tecnologia resolve problema negócio",
]

DEFAULT_ICP_TITLES: list[str] = [
    # C-LEVEL GERAL
    "CEO",
    "CFO",
    "COO",
    "CTO",
    "Diretor Executivo",
    "Sócio Diretor",
    "Fundador",
    "Co-fundador",
    # OPERAÇÕES E TI
    "Diretor de Operações",
    "Gerente de Operações",
    "Diretor de TI",
    "Gerente de TI",
    "Head de TI",
    "Gerente de Infraestrutura",
    "Diretor de Tecnologia",
    "VP de Tecnologia",
    "VP de Operações",
    # FINANCEIRO E CONTÁBIL
    "Diretor Financeiro",
    "Gerente Financeiro",
    "Controller",
    "Sócio Contador",
    "Diretor de Controladoria",
    # COMERCIAL E MARKETING
    "Diretor Comercial",
    "Gerente Comercial",
    "Diretor de Vendas",
    "Head de Vendas",
    "CMO",
    "Diretor de Marketing",
    "Head de Growth",
    # INDUSTRIAL E LOGÍSTICA
    "Diretor Industrial",
    "Gerente Industrial",
    "Diretor de Logística",
    "Gerente de Supply Chain",
    "Gerente de Planejamento",
    "Gerente de PCP",
    # JURÍDICO
    "Sócio Advogado",
    "Diretor Jurídico",
    "General Counsel",
    "Sócio de Escritório",
    # SAÚDE
    "Diretor de Clínica",
    "Administrador Hospitalar",
    "Gerente Administrativo",
    "Sócio Clínica",
]

DEFAULT_ICP_SECTORS: list[str] = [
    # Prioritários
    "Financeiro",
    "Contabilidade",
    "Jurídico",
    "Advocacia",
    "Saúde",
    "Clínica",
    # Secundários
    "Indústria",
    "Logística",
    "Varejo",
    "E-commerce",
    "Tecnologia",
    "Software",
    "Imobiliário",
    "Construtora",
    "Agência",
    "RH",
    "Agroindustrial",
]

# Limites de posts por etapa
MAX_REFERENCE_POSTS = 15
MAX_ICP_POSTS = 10
MIN_ENGAGEMENT_SCORE = 50


# ── Task principal ────────────────────────────────────────────────────────────


@celery_app.task(
    bind=True,
    name="workers.content_engagement.run_engagement_scan",
    max_retries=2,
    default_retry_delay=60,
    queue="content-engagement",
)
def run_engagement_scan(
    self,
    session_id: str,
    tenant_id: str,
    linked_post_id: str | None = None,
    keywords: list[str] | None = None,
    icp_titles: list[str] | None = None,
    icp_sectors: list[str] | None = None,
) -> dict:
    """Executa o scan de engajamento em 4 etapas."""
    try:
        return asyncio.run(
            _run_scan_async(
                task=self,
                session_id=session_id,
                tenant_id=tenant_id,
                linked_post_id=linked_post_id,
                keywords=keywords,
                icp_titles=icp_titles,
                icp_sectors=icp_sectors,
            )
        )
    except Exception as exc:
        # Safety net: garante que a sessao nunca fica presa em 'running'
        logger.error(
            "engagement_scan.fatal_error",
            session_id=session_id,
            error=str(exc),
        )
        asyncio.run(_mark_session_failed(session_id, str(exc)))
        return {"session_id": session_id, "status": "failed", "error": str(exc)}


# ── Safety net ───────────────────────────────────────────────────────────────


async def _mark_session_failed(session_id: str, error_msg: str) -> None:
    """Marca a sessao como failed em caso de erro fatal no worker."""
    import uuid
    from datetime import UTC, datetime

    from sqlalchemy import select

    from core.database import WorkerSessionLocal
    from models.content_engagement_event import ContentEngagementEvent
    from models.content_engagement_session import ContentEngagementSession

    try:
        session_uuid = uuid.UUID(session_id)
        async with WorkerSessionLocal() as db:
            stmt = select(ContentEngagementSession).where(
                ContentEngagementSession.id == session_uuid
            )
            row = await db.execute(stmt)
            session_db = row.scalar_one_or_none()
            if session_db:
                session_db.status = "failed"
                session_db.error_message = error_msg[:500]
                session_db.completed_at = datetime.now(UTC)
                db.add(session_db)
                db.add(
                    ContentEngagementEvent(
                        tenant_id=session_db.tenant_id,
                        session_id=session_db.id,
                        event_type="scan_failed",
                        payload={"reason": "worker_fatal_error", "error": error_msg[:500]},
                    )
                )
            await db.commit()
    except Exception as inner_exc:
        logger.error(
            "engagement_scan.mark_failed_error",
            session_id=session_id,
            error=str(inner_exc),
        )


# ── Implementacao async ───────────────────────────────────────────────────────


async def _run_scan_async(
    task,
    session_id: str,
    tenant_id: str,
    linked_post_id: str | None,
    keywords: list[str] | None,
    icp_titles: list[str] | None,
    icp_sectors: list[str] | None,
) -> dict:
    from sqlalchemy import func, select
    from sqlalchemy.orm import selectinload

    from core.config import settings
    from core.database import WorkerSessionLocal
    from core.redis_client import redis_client
    from integrations.llm.registry import LLMRegistry
    from models.content_engagement_comment import ContentEngagementComment
    from models.content_engagement_event import ContentEngagementEvent
    from models.content_engagement_post import ContentEngagementPost
    from models.content_engagement_session import ContentEngagementSession
    from models.content_post import ContentPost
    from models.content_settings import ContentSettings
    from services.content.apify_linkedin_scanner import ApifyLinkedInScanner
    from services.content.comment_generator import generate_comments_for_post
    from services.content.engagement_analyzer import (
        analyze_icp_post_relevance,
        analyze_reference_post,
    )
    from services.content.engagement_post_identity import (
        build_post_identity,
        choose_primary_post_source,
        merge_post_sources,
    )

    session_uuid = uuid.UUID(session_id)
    tenant_uuid = uuid.UUID(tenant_id)

    async with WorkerSessionLocal() as preflight_db:
        session_stmt = select(ContentEngagementSession).where(
            ContentEngagementSession.id == session_uuid,
            ContentEngagementSession.tenant_id == tenant_uuid,
        )
        session_row = await preflight_db.execute(session_stmt)
        session_db = session_row.scalar_one_or_none()

        if session_db is None:
            logger.warning(
                "engagement_scan.session_missing",
                session_id=session_id,
                tenant_id=tenant_id,
            )
            return {
                "session_id": session_id,
                "status": "failed",
                "error": "Sessao nao encontrada antes do processamento",
            }

        if session_db.status != "running":
            logger.warning(
                "engagement_scan.skipped_stale_session",
                session_id=session_id,
                tenant_id=tenant_id,
                status=session_db.status,
            )
            return {
                "session_id": session_id,
                "status": session_db.status,
                "error": session_db.error_message,
            }

    linked_post_keywords: list[str] = []

    if linked_post_id:
        try:
            linked_post_uuid = uuid.UUID(linked_post_id)
            async with WorkerSessionLocal() as linked_post_db:
                linked_post_stmt = select(ContentPost).where(
                    ContentPost.id == linked_post_uuid,
                    ContentPost.tenant_id == tenant_uuid,
                )
                linked_post_row = await linked_post_db.execute(linked_post_stmt)
                linked_post = linked_post_row.scalar_one_or_none()
                if linked_post:
                    linked_post_keywords = _extract_linked_post_keywords(linked_post)
                    logger.info(
                        "engagement_scan.linked_post_context_loaded",
                        session_id=session_id,
                        linked_post_id=linked_post_id,
                        boosted_keywords=linked_post_keywords,
                    )
        except ValueError:
            logger.warning(
                "engagement_scan.invalid_linked_post_id",
                session_id=session_id,
                linked_post_id=linked_post_id,
            )

    effective_keywords = _merge_keywords(
        linked_post_keywords,
        keywords or DEFAULT_ENGAGEMENT_KEYWORDS,
    )
    effective_icp_titles = icp_titles or DEFAULT_ICP_TITLES
    effective_icp_sectors = icp_sectors or DEFAULT_ICP_SECTORS

    registry = LLMRegistry(settings=settings, redis=redis_client)
    scanner = ApifyLinkedInScanner()

    async def _update_session_fields(**updates: object) -> None:
        async with WorkerSessionLocal() as audit_db:
            stmt = select(ContentEngagementSession).where(
                ContentEngagementSession.id == session_uuid
            )
            row = await audit_db.execute(stmt)
            session_record = row.scalar_one_or_none()
            if session_record:
                for field, value in updates.items():
                    setattr(session_record, field, value)
                audit_db.add(session_record)
            await audit_db.commit()

    async def _record_event(event_type: str, payload: dict[str, object] | None = None) -> None:
        async with WorkerSessionLocal() as event_db:
            event_db.add(
                ContentEngagementEvent(
                    tenant_id=tenant_uuid,
                    session_id=session_uuid,
                    event_type=event_type,
                    payload=payload,
                )
            )
            await event_db.commit()

    await _update_session_fields(
        linked_post_context_keywords=linked_post_keywords or None,
        effective_keywords=effective_keywords or None,
        icp_titles_used=effective_icp_titles or None,
        icp_sectors_used=effective_icp_sectors or None,
    )
    await _record_event(
        "queue_pickup_started",
        {
            "linked_post_id": linked_post_id,
            "effective_keywords": effective_keywords,
            "icp_titles_used": effective_icp_titles,
            "icp_sectors_used": effective_icp_sectors,
        },
    )

    # Helper: atualiza current_step no banco para o frontend exibir progresso
    async def _set_step(step: int) -> None:
        async with WorkerSessionLocal() as step_db:
            stmt = select(ContentEngagementSession).where(
                ContentEngagementSession.id == session_uuid
            )
            row = await step_db.execute(stmt)
            s = row.scalar_one_or_none()
            if s:
                s.current_step = step
                step_db.add(s)
            await step_db.commit()

    # Helper: trunca string para caber no varchar do banco
    def _trunc(value: str | None, max_len: int) -> str | None:
        if value is None:
            return None
        return value[:max_len] if len(value) > max_len else value

    reference_posts_data: list[dict] = []
    icp_posts_data: list[dict] = []
    ref_count = 0
    icp_count = 0
    comments_generated = 0
    final_status = "completed"
    error_msg: str | None = None

    # ── Etapa 1: Posts de referencia via Apify ────────────────────────────────
    await _set_step(1)
    try:
        logger.info(
            "engagement_scan.etapa1_start",
            session_id=session_id,
            tenant_id=tenant_id,
            keywords_count=len(effective_keywords),
        )
        reference_posts_data = await scanner.search_posts_by_keywords(
            keywords=effective_keywords,
            max_results=MAX_REFERENCE_POSTS,
            min_engagement_score=MIN_ENGAGEMENT_SCORE,
        )
        logger.info(
            "engagement_scan.etapa1_done",
            session_id=session_id,
            references_found=len(reference_posts_data),
        )
        await _record_event(
            "reference_search_completed",
            {"references_found": len(reference_posts_data)},
        )
    except Exception as exc:
        logger.error(
            "engagement_scan.etapa1_failed",
            session_id=session_id,
            error=str(exc),
        )
        final_status = "partial"
        error_msg = f"Etapa 1 falhou: {exc}"

    # ── Etapa 2: Posts de ICP via Apify ───────────────────────────────────────
    await _set_step(2)
    try:
        logger.info(
            "engagement_scan.etapa2_start",
            session_id=session_id,
            icp_titles_count=len(effective_icp_titles),
        )
        icp_posts_data = await scanner.get_icp_recent_posts(
            icp_titles=effective_icp_titles,
            icp_sectors=effective_icp_sectors,
            topic_keywords=effective_keywords,
            max_results=MAX_ICP_POSTS,
        )
        logger.info(
            "engagement_scan.etapa2_done",
            session_id=session_id,
            icp_found=len(icp_posts_data),
        )
    except Exception as exc:
        logger.error(
            "engagement_scan.etapa2_failed",
            session_id=session_id,
            error=str(exc),
        )
        final_status = "partial"
        error_msg = (error_msg or "") + f" | Etapa 2 falhou: {exc}"
    else:
        await _record_event(
            "icp_search_completed",
            {"icp_found": len(icp_posts_data)},
        )

    # ── Etapa 3 + 4: Salvar posts, analisar com LLM, gerar comentarios ────────
    async with WorkerSessionLocal() as db:
        existing_posts_stmt = (
            select(ContentEngagementPost)
            .options(selectinload(ContentEngagementPost.suggested_comments))
            .where(
                ContentEngagementPost.session_id == session_uuid,
                ContentEngagementPost.tenant_id == tenant_uuid,
            )
        )
        existing_posts = (await db.execute(existing_posts_stmt)).scalars().all()
        posts_by_dedup_key: dict[str, ContentEngagementPost] = {}

        for existing_post in existing_posts:
            canonical_post_url, dedup_key = build_post_identity(
                post_url=existing_post.post_url,
                post_text=existing_post.post_text,
                author_name=existing_post.author_name,
            )
            if canonical_post_url and existing_post.canonical_post_url != canonical_post_url:
                existing_post.canonical_post_url = canonical_post_url
            if dedup_key and existing_post.dedup_key != dedup_key:
                existing_post.dedup_key = dedup_key
            if not existing_post.merged_sources:
                existing_post.merged_sources = merge_post_sources([], existing_post.source)
            if not existing_post.merge_count:
                existing_post.merge_count = 1
            if dedup_key:
                posts_by_dedup_key.setdefault(dedup_key, existing_post)

        def _merge_existing_post(
            existing_post: ContentEngagementPost,
            *,
            post_type: str,
            post_data: dict,
            canonical_post_url: str | None,
            dedup_key: str | None,
        ) -> bool:
            promoted_to_icp = existing_post.post_type != "icp" and post_type == "icp"

            if promoted_to_icp:
                existing_post.post_type = "icp"

            existing_post.source = choose_primary_post_source(existing_post.source, "apify")
            existing_post.merged_sources = merge_post_sources(existing_post.merged_sources, "apify")
            existing_post.merge_count = max(existing_post.merge_count, 1) + 1

            if canonical_post_url and not existing_post.canonical_post_url:
                existing_post.canonical_post_url = canonical_post_url
            if dedup_key and not existing_post.dedup_key:
                existing_post.dedup_key = dedup_key
            if post_data.get("post_url") and not existing_post.post_url:
                existing_post.post_url = _trunc(post_data.get("post_url"), 500)
            if post_data.get("post_text") and len(post_data["post_text"]) > len(
                existing_post.post_text
            ):
                existing_post.post_text = post_data["post_text"]
            if post_data.get("author_name") and not existing_post.author_name:
                existing_post.author_name = _trunc(post_data.get("author_name"), 300)
            if post_data.get("author_title") and not existing_post.author_title:
                existing_post.author_title = _trunc(post_data.get("author_title"), 500)
            if post_data.get("author_company") and not existing_post.author_company:
                existing_post.author_company = _trunc(post_data.get("author_company"), 300)
            if post_data.get("author_linkedin_urn") and not existing_post.author_linkedin_urn:
                existing_post.author_linkedin_urn = _trunc(
                    post_data.get("author_linkedin_urn"), 100
                )
            if post_data.get("author_profile_url") and not existing_post.author_profile_url:
                existing_post.author_profile_url = _trunc(post_data.get("author_profile_url"), 500)
            if post_data.get("post_published_at") and not existing_post.post_published_at:
                existing_post.post_published_at = post_data.get("post_published_at")

            existing_post.likes = max(existing_post.likes, post_data.get("likes", 0))
            existing_post.comments = max(existing_post.comments, post_data.get("comments", 0))
            existing_post.shares = max(existing_post.shares, post_data.get("shares", 0))

            incoming_score = post_data.get("engagement_score")
            if incoming_score is not None:
                existing_post.engagement_score = max(
                    existing_post.engagement_score or 0, incoming_score
                )

            return promoted_to_icp

        # Carregar ContentSettings para author_name e author_voice
        settings_stmt = select(ContentSettings).where(ContentSettings.tenant_id == tenant_uuid)
        settings_row = await db.execute(settings_stmt)
        content_settings = settings_row.scalar_one_or_none()
        author_name = (content_settings.author_name if content_settings else None) or "Especialista"
        author_voice = (
            content_settings.author_voice if content_settings else None
        ) or "direto, tecnico, coloquial profissional"
        from services.llm_config import resolve_tenant_llm_config  # noqa: PLC0415

        llm_config = await resolve_tenant_llm_config(db, tenant_uuid)

        # Salvar e analisar posts de referencia (Etapa 3a)
        await _set_step(3)
        for post_data in reference_posts_data:
            try:
                analysis = await analyze_reference_post(
                    post_text=post_data["post_text"],
                    registry=registry,
                    llm_config=llm_config,
                )
                canonical_post_url, dedup_key = build_post_identity(
                    post_url=post_data.get("post_url"),
                    post_text=post_data.get("post_text"),
                    author_name=post_data.get("author_name"),
                )
                existing_post = posts_by_dedup_key.get(dedup_key) if dedup_key else None

                if existing_post:
                    _merge_existing_post(
                        existing_post,
                        post_type="reference",
                        post_data=post_data,
                        canonical_post_url=canonical_post_url,
                        dedup_key=dedup_key,
                    )
                    if existing_post.post_type == "reference":
                        existing_post.hook_type = _trunc(analysis.get("hook_type"), 30)
                        existing_post.pillar = _trunc(analysis.get("pillar"), 20)
                        existing_post.why_it_performed = analysis.get("why_it_performed")
                        existing_post.what_to_replicate = analysis.get("what_to_replicate")
                    elif not existing_post.hook_type:
                        existing_post.hook_type = _trunc(analysis.get("hook_type"), 30)
                        existing_post.pillar = _trunc(analysis.get("pillar"), 20)
                    db.add(existing_post)
                    logger.info(
                        "engagement_scan.post_deduplicated",
                        session_id=session_id,
                        dedup_key=dedup_key,
                        post_type="reference",
                    )
                    continue

                post_db = ContentEngagementPost(
                    id=uuid.uuid4(),
                    tenant_id=tenant_uuid,
                    session_id=session_uuid,
                    post_type="reference",
                    source="apify",
                    merged_sources=["apify"],
                    merge_count=1,
                    author_name=_trunc(post_data.get("author_name"), 300),
                    author_title=_trunc(post_data.get("author_title"), 500),
                    author_company=_trunc(post_data.get("author_company"), 300),
                    author_linkedin_urn=_trunc(post_data.get("author_linkedin_urn"), 100),
                    author_profile_url=_trunc(post_data.get("author_profile_url"), 500),
                    post_url=_trunc(post_data.get("post_url"), 500),
                    canonical_post_url=_trunc(canonical_post_url, 500),
                    dedup_key=_trunc(dedup_key, 120),
                    post_text=post_data["post_text"],
                    post_published_at=post_data.get("post_published_at"),
                    likes=post_data.get("likes", 0),
                    comments=post_data.get("comments", 0),
                    shares=post_data.get("shares", 0),
                    engagement_score=post_data.get("engagement_score"),
                    hook_type=_trunc(analysis.get("hook_type"), 30),
                    pillar=_trunc(analysis.get("pillar"), 20),
                    why_it_performed=analysis.get("why_it_performed"),
                    what_to_replicate=analysis.get("what_to_replicate"),
                )
                db.add(post_db)
                if dedup_key:
                    posts_by_dedup_key[dedup_key] = post_db
            except Exception as exc:
                logger.warning(
                    "engagement_scan.reference_post_failed",
                    session_id=session_id,
                    error=str(exc),
                )

        # Salvar, analisar e gerar comentarios para posts de ICP (Etapas 3b + 4)
        await _set_step(4)
        for post_data in icp_posts_data:
            try:
                relevance = await analyze_icp_post_relevance(
                    post_text=post_data["post_text"],
                    author_name=post_data.get("author_name", ""),
                    author_title=post_data.get("author_title", ""),
                    author_company=post_data.get("author_company", ""),
                    registry=registry,
                    llm_config=llm_config,
                )
                canonical_post_url, dedup_key = build_post_identity(
                    post_url=post_data.get("post_url"),
                    post_text=post_data.get("post_text"),
                    author_name=post_data.get("author_name"),
                )
                existing_post = posts_by_dedup_key.get(dedup_key) if dedup_key else None

                if existing_post:
                    _merge_existing_post(
                        existing_post,
                        post_type="icp",
                        post_data=post_data,
                        canonical_post_url=canonical_post_url,
                        dedup_key=dedup_key,
                    )
                    existing_post.why_it_performed = relevance.get("relevance_reason")
                    existing_post.what_to_replicate = relevance.get("comment_angle")
                    db.add(existing_post)
                    post_db = existing_post
                    post_id = existing_post.id
                    logger.info(
                        "engagement_scan.post_deduplicated",
                        session_id=session_id,
                        dedup_key=dedup_key,
                        post_type="icp",
                    )
                else:
                    # Criar o post (mesmo se irrelevante — usuario pode ver)
                    post_id = uuid.uuid4()
                    post_db = ContentEngagementPost(
                        id=post_id,
                        tenant_id=tenant_uuid,
                        session_id=session_uuid,
                        post_type="icp",
                        source="apify",
                        merged_sources=["apify"],
                        merge_count=1,
                        author_name=_trunc(post_data.get("author_name"), 300),
                        author_title=_trunc(post_data.get("author_title"), 500),
                        author_company=_trunc(post_data.get("author_company"), 300),
                        author_linkedin_urn=_trunc(post_data.get("author_linkedin_urn"), 100),
                        author_profile_url=_trunc(post_data.get("author_profile_url"), 500),
                        post_url=_trunc(post_data.get("post_url"), 500),
                        canonical_post_url=_trunc(canonical_post_url, 500),
                        dedup_key=_trunc(dedup_key, 120),
                        post_text=post_data["post_text"],
                        post_published_at=post_data.get("post_published_at"),
                        likes=post_data.get("likes", 0),
                        comments=post_data.get("comments", 0),
                        shares=post_data.get("shares", 0),
                        engagement_score=post_data.get("engagement_score"),
                        # why_it_performed reutilizado como relevance_reason para ICP
                        why_it_performed=relevance.get("relevance_reason"),
                        what_to_replicate=relevance.get("comment_angle"),
                    )
                    db.add(post_db)
                    if dedup_key:
                        posts_by_dedup_key[dedup_key] = post_db

                # Gerar comentarios apenas para posts relevantes
                has_existing_comments = bool(post_db.suggested_comments)
                if relevance.get("is_relevant") and not has_existing_comments:
                    comment_1, comment_2 = await generate_comments_for_post(
                        post_text=post_data["post_text"],
                        author_name=post_data.get("author_name", ""),
                        author_title=post_data.get("author_title", ""),
                        author_company=post_data.get("author_company", ""),
                        comment_angle=relevance.get("comment_angle", ""),
                        author_voice=author_voice,
                        registry=registry,
                        llm_config=llm_config,
                    )

                    for variation, text in enumerate([comment_1, comment_2], start=1):
                        comment_db = ContentEngagementComment(
                            id=uuid.uuid4(),
                            tenant_id=tenant_uuid,
                            engagement_post_id=post_id,
                            session_id=session_uuid,
                            comment_text=text,
                            variation=variation,
                            status="pending",
                        )
                        db.add(comment_db)

            except Exception as exc:
                logger.warning(
                    "engagement_scan.icp_post_failed",
                    session_id=session_id,
                    error=str(exc),
                )

        # Atualizar sessao com totais e status final
        try:
            await db.flush()

            ref_count = (
                await db.execute(
                    select(func.count(ContentEngagementPost.id)).where(
                        ContentEngagementPost.session_id == session_uuid,
                        ContentEngagementPost.post_type == "reference",
                    )
                )
            ).scalar_one()
            icp_count = (
                await db.execute(
                    select(func.count(ContentEngagementPost.id)).where(
                        ContentEngagementPost.session_id == session_uuid,
                        ContentEngagementPost.post_type == "icp",
                    )
                )
            ).scalar_one()
            comments_generated = (
                await db.execute(
                    select(func.count(ContentEngagementComment.id)).where(
                        ContentEngagementComment.session_id == session_uuid,
                    )
                )
            ).scalar_one()

            session_stmt = select(ContentEngagementSession).where(
                ContentEngagementSession.id == session_uuid
            )
            session_row = await db.execute(session_stmt)
            session_db = session_row.scalar_one_or_none()

            if session_db:
                # Status: failed se zero resultados, partial se houve erro, completed caso contrario
                if ref_count == 0 and icp_count == 0:
                    final_status = "failed"
                elif error_msg:
                    final_status = "partial"
                else:
                    final_status = "completed"

                session_db.status = final_status
                session_db.references_found = ref_count
                session_db.icp_posts_found = icp_count
                session_db.comments_generated = comments_generated
                session_db.error_message = error_msg
                session_db.completed_at = datetime.now(UTC)
                db.add(session_db)

        except Exception as exc:
            logger.error(
                "engagement_scan.session_update_failed",
                session_id=session_id,
                error=str(exc),
            )

        await db.commit()

    await _record_event(
        "comments_generated",
        {"comments_generated": comments_generated},
    )
    await _record_event(
        "scan_completed" if final_status != "failed" else "scan_failed",
        {
            "status": final_status,
            "references_found": ref_count,
            "icp_posts_found": icp_count,
            "comments_generated": comments_generated,
            "error": error_msg,
        },
    )

    logger.info(
        "engagement_scan.completed",
        session_id=session_id,
        tenant_id=tenant_id,
        status=final_status,
        references_found=ref_count,
        icp_posts_found=icp_count,
        comments_generated=comments_generated,
    )

    return {
        "session_id": session_id,
        "status": final_status,
        "references_found": ref_count,
        "icp_posts_found": icp_count,
        "comments_generated": comments_generated,
    }


def _merge_keywords(prioritized: list[str], fallback: list[str], limit: int = 12) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()

    for keyword in prioritized + fallback:
        normalized = keyword.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        merged.append(keyword.strip())
        if len(merged) >= limit:
            break

    return merged


def _extract_linked_post_keywords(post) -> list[str]:
    pillar_keywords = {
        "authority": ["autoridade", "especialista", "expertise técnica"],
        "case": ["case de sucesso", "resultado real", "transformação operacional"],
        "vision": ["tendência de mercado", "visão estratégica", "futuro da operação"],
    }
    hook_keywords = {
        "loop_open": ["curiosidade", "mistério", "virada de contexto"],
        "contrarian": ["opinião contrária", "quebra de padrão", "senso comum"],
        "identification": ["dor operacional", "problema real", "retrabalho"],
        "shortcut": ["atalho estratégico", "ganho rápido", "rota mais curta"],
        "benefit": ["benefício direto", "ganho imediato", "valor claro"],
        "data": ["dados concretos", "métrica real", "indicador"],
    }

    extracted: list[str] = []
    title_terms = re.findall(r"[\wÀ-ÿ]{4,}", post.title or "")
    extracted.extend(title_terms[:5])

    hashtags = [tag.lstrip("#") for tag in (post.hashtags or "").split() if tag.startswith("#")]
    extracted.extend(hashtags[:4])

    if post.pillar:
        extracted.extend(pillar_keywords.get(post.pillar, []))
    if post.hook_type:
        extracted.extend(hook_keywords.get(post.hook_type, []))

    return _merge_keywords(extracted, [], limit=8)
