"""
api/routes/content/engagement.py

LinkedIn Engagement Scanner — todos os endpoints do scanner de engajamento.

POST   /content/engagement/run                      — iniciar scan
GET    /content/engagement/sessions                 — listar sessoes
GET    /content/engagement/sessions/{id}            — sessao com posts e comentarios

GET    /content/engagement/posts                    — listar posts
POST   /content/engagement/posts                    — adicao manual de post
PATCH  /content/engagement/posts/{id}/save          — salvar como referencia
DELETE /content/engagement/posts/{id}               — remover post

GET    /content/engagement/comments                 — listar comentarios
PATCH  /content/engagement/comments/{id}/select     — marcar como selecionado
PATCH  /content/engagement/comments/{id}/posted     — confirmar postagem manual
PATCH  /content/engagement/comments/{id}/discard    — descartar sugestao
POST   /content/engagement/comments/{id}/regenerate — nova sugestao LLM
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

_SESSION_TIMEOUT = timedelta(minutes=5)

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.dependencies import get_effective_tenant_id, get_llm_registry, get_session_flexible
from integrations.llm.registry import LLMRegistry
from models.content_engagement_comment import ContentEngagementComment
from models.content_engagement_post import ContentEngagementPost
from models.content_engagement_session import ContentEngagementSession
from models.content_reference import ContentReference
from schemas.content_engagement import (
    AddManualPostRequest,
    EngagementCommentResponse,
    EngagementPostResponse,
    EngagementSessionDetailResponse,
    EngagementSessionResponse,
    RunScanRequest,
    RunScanResponse,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/engagement", tags=["Content Hub — Engagement"])


# ── Sessoes ────────────────────────────────────────────────────────────────────


@router.post(
    "/run",
    response_model=RunScanResponse,
    status_code=status.HTTP_201_CREATED,
)
async def run_scan(
    body: RunScanRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> RunScanResponse:
    """Inicia uma nova sessao de scan de engajamento."""
    session = ContentEngagementSession(
        tenant_id=tenant_id,
        linked_post_id=body.linked_post_id,
        status="running",
        scan_source="apify",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    # Disparar task Celery (import local para evitar circular)
    from workers.content_engagement import run_engagement_scan

    run_engagement_scan.apply_async(
        kwargs={
            "session_id": str(session.id),
            "tenant_id": str(tenant_id),
            "linked_post_id": str(body.linked_post_id) if body.linked_post_id else None,
            "keywords": body.keywords,
            "icp_titles": body.icp_filters.titles if body.icp_filters else None,
            "icp_sectors": body.icp_filters.sectors if body.icp_filters else None,
        },
        queue="content",
    )

    logger.info(
        "engagement.scan_started",
        session_id=str(session.id),
        tenant_id=str(tenant_id),
    )
    return RunScanResponse(session_id=session.id, status="running")


@router.get("/sessions", response_model=list[EngagementSessionResponse])
async def list_sessions(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> list[EngagementSessionResponse]:
    offset = (page - 1) * limit
    stmt = (
        select(ContentEngagementSession)
        .where(ContentEngagementSession.tenant_id == tenant_id)
        .order_by(ContentEngagementSession.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return [
        EngagementSessionResponse.model_validate(s)
        for s in result.scalars().all()
    ]


@router.get(
    "/sessions/{session_id}",
    response_model=EngagementSessionDetailResponse,
)
async def get_session(
    session_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> EngagementSessionDetailResponse:
    stmt = (
        select(ContentEngagementSession)
        .where(
            ContentEngagementSession.id == session_id,
            ContentEngagementSession.tenant_id == tenant_id,
        )
        .options(
            selectinload(ContentEngagementSession.posts).selectinload(
                ContentEngagementPost.suggested_comments
            )
        )
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")

    # Auto-fail: se está "running" há mais de _SESSION_TIMEOUT, marcar como failed
    if session.status == "running" and session.created_at is not None:
        elapsed = datetime.now(UTC) - session.created_at
        if elapsed > _SESSION_TIMEOUT:
            session.status = "failed"
            session.error_message = "Timeout: scan nao completou em 5 minutos"
            session.completed_at = datetime.now(UTC)
            db.add(session)
            await db.commit()
            await db.refresh(session)
            logger.warning(
                "engagement_session.auto_failed",
                session_id=str(session.id),
                elapsed_s=int(elapsed.total_seconds()),
            )

    return EngagementSessionDetailResponse.model_validate(session)


# ── Posts ──────────────────────────────────────────────────────────────────────


@router.get("/posts", response_model=list[EngagementPostResponse])
async def list_posts(
    session_id: uuid.UUID | None = Query(None),
    post_type: str | None = Query(None),
    is_saved: bool | None = Query(None),
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> list[EngagementPostResponse]:
    stmt = select(ContentEngagementPost).where(
        ContentEngagementPost.tenant_id == tenant_id
    )
    if session_id:
        stmt = stmt.where(ContentEngagementPost.session_id == session_id)
    if post_type:
        stmt = stmt.where(ContentEngagementPost.post_type == post_type)
    if is_saved is not None:
        stmt = stmt.where(ContentEngagementPost.is_saved == is_saved)
    stmt = stmt.options(selectinload(ContentEngagementPost.suggested_comments))
    stmt = stmt.order_by(
        ContentEngagementPost.engagement_score.desc().nulls_last(),
        ContentEngagementPost.created_at.desc(),
    )
    result = await db.execute(stmt)
    return [
        EngagementPostResponse.model_validate(p) for p in result.scalars().all()
    ]


@router.post(
    "/posts",
    response_model=EngagementPostResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_manual_post(
    body: AddManualPostRequest,
    session_id: uuid.UUID = Query(..., description="ID da sessao onde inserir o post"),
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> EngagementPostResponse:
    """Adicao manual de post pelo usuario."""
    # Valida que a sessao pertence ao tenant
    sess_stmt = select(ContentEngagementSession).where(
        ContentEngagementSession.id == session_id,
        ContentEngagementSession.tenant_id == tenant_id,
    )
    sess_result = await db.execute(sess_stmt)
    session = sess_result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")

    post = ContentEngagementPost(
        tenant_id=tenant_id,
        session_id=session_id,
        post_type=body.post_type,
        post_text=body.post_text,
        post_url=body.post_url,
        author_name=body.author_name,
        author_title=body.author_title,
        author_company=body.author_company,
        author_profile_url=body.author_profile_url,
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)
    logger.info(
        "engagement.post_added_manual",
        post_id=str(post.id),
        session_id=str(session_id),
        tenant_id=str(tenant_id),
    )
    return EngagementPostResponse.model_validate(post)


@router.patch("/posts/{post_id}/save", response_model=EngagementPostResponse)
async def save_post(
    post_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> EngagementPostResponse:
    """Toggle is_saved de um post de engajamento.

    Ao salvar (is_saved → True): cria um ContentReference espelho.
    Ao remover (is_saved → False): deleta o ContentReference espelho.
    """
    post = await _get_post_or_404(post_id, tenant_id, db)
    new_saved = not post.is_saved
    post.is_saved = new_saved  # type: ignore[assignment]

    if new_saved:
        # Cria ContentReference espelho (idempotente: checa duplicata por source_url)
        existing_ref = None
        if post.post_url:
            stmt_ref = select(ContentReference).where(
                ContentReference.tenant_id == tenant_id,
                ContentReference.source_url == post.post_url,
            )
            existing_ref = (await db.execute(stmt_ref)).scalar_one_or_none()

        if not existing_ref:
            ref = ContentReference(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                author_name=post.author_name,
                author_title=post.author_title,
                author_company=post.author_company,
                body=post.post_text or "",
                hook_type=post.hook_type,
                pillar=post.pillar,
                engagement_score=post.engagement_score,
                source_url=post.post_url,
                notes=post.why_it_performed,
            )
            db.add(ref)
    else:
        # Remove ContentReference espelho ao desmarcar
        if post.post_url:
            stmt_ref = select(ContentReference).where(
                ContentReference.tenant_id == tenant_id,
                ContentReference.source_url == post.post_url,
            )
            existing_ref = (await db.execute(stmt_ref)).scalar_one_or_none()
            if existing_ref:
                await db.delete(existing_ref)

    await db.commit()
    await db.refresh(post, attribute_names=["suggested_comments"])
    return EngagementPostResponse.model_validate(post)


@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_post(
    post_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> None:
    post = await _get_post_or_404(post_id, tenant_id, db)
    await db.delete(post)
    await db.commit()
    logger.info(
        "engagement.post_deleted",
        post_id=str(post_id),
        tenant_id=str(tenant_id),
    )


# ── Comentarios ────────────────────────────────────────────────────────────────


@router.get("/comments", response_model=list[EngagementCommentResponse])
async def list_comments(
    session_id: uuid.UUID | None = Query(None),
    comment_status: str | None = Query(None, alias="status"),
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> list[EngagementCommentResponse]:
    stmt = select(ContentEngagementComment).where(
        ContentEngagementComment.tenant_id == tenant_id
    )
    if session_id:
        stmt = stmt.where(ContentEngagementComment.session_id == session_id)
    if comment_status:
        stmt = stmt.where(ContentEngagementComment.status == comment_status)
    stmt = stmt.order_by(
        ContentEngagementComment.engagement_post_id,
        ContentEngagementComment.variation,
    )
    result = await db.execute(stmt)
    return [
        EngagementCommentResponse.model_validate(c) for c in result.scalars().all()
    ]


@router.patch(
    "/comments/{comment_id}/select",
    response_model=EngagementCommentResponse,
)
async def select_comment(
    comment_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> EngagementCommentResponse:
    comment = await _get_comment_or_404(comment_id, tenant_id, db)
    comment.status = "selected"  # type: ignore[assignment]
    await db.commit()
    await db.refresh(comment)
    return EngagementCommentResponse.model_validate(comment)


@router.patch(
    "/comments/{comment_id}/posted",
    response_model=EngagementCommentResponse,
)
async def mark_comment_posted(
    comment_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> EngagementCommentResponse:
    """Confirma que o comentario foi postado manualmente."""
    comment = await _get_comment_or_404(comment_id, tenant_id, db)
    if comment.status == "posted":
        return EngagementCommentResponse.model_validate(comment)

    comment.status = "posted"  # type: ignore[assignment]
    comment.posted_at = datetime.now(UTC)  # type: ignore[assignment]

    # Atualiza contador de comentarios na sessao
    sess_stmt = select(ContentEngagementSession).where(
        ContentEngagementSession.id == comment.session_id,
        ContentEngagementSession.tenant_id == tenant_id,
    )
    sess_result = await db.execute(sess_stmt)
    session = sess_result.scalar_one_or_none()
    if session:
        session.comments_posted = (session.comments_posted or 0) + 1  # type: ignore[assignment]

    await db.commit()
    await db.refresh(comment)

    # Integrar com modulo de leads (fire-and-forget, nao bloqueia resposta)
    try:
        await _on_comment_marked_posted(comment_id=comment_id, tenant_id=tenant_id, db=db)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "engagement.lead_integration_failed",
            comment_id=str(comment_id),
            error=str(exc),
        )

    logger.info(
        "engagement.comment_posted",
        comment_id=str(comment_id),
        tenant_id=str(tenant_id),
    )
    return EngagementCommentResponse.model_validate(comment)


@router.patch(
    "/comments/{comment_id}/unpost",
    response_model=EngagementCommentResponse,
)
async def unmark_comment_posted(
    comment_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> EngagementCommentResponse:
    """Desfaz a confirmacao manual de comentario postado."""
    comment = await _get_comment_or_404(comment_id, tenant_id, db)
    if comment.status != "posted":
        return EngagementCommentResponse.model_validate(comment)

    previous_posted_at = comment.posted_at
    comment.status = "pending"  # type: ignore[assignment]
    comment.posted_at = None  # type: ignore[assignment]

    sess_stmt = select(ContentEngagementSession).where(
        ContentEngagementSession.id == comment.session_id,
        ContentEngagementSession.tenant_id == tenant_id,
    )
    sess_result = await db.execute(sess_stmt)
    session = sess_result.scalar_one_or_none()
    if session:
        session.comments_posted = max((session.comments_posted or 0) - 1, 0)  # type: ignore[assignment]

    await db.commit()
    await db.refresh(comment)

    try:
        await _undo_comment_marked_posted(
            comment_id=comment_id,
            tenant_id=tenant_id,
            posted_at=previous_posted_at,
            db=db,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "engagement.lead_integration_undo_failed",
            comment_id=str(comment_id),
            error=str(exc),
        )

    logger.info(
        "engagement.comment_unposted",
        comment_id=str(comment_id),
        tenant_id=str(tenant_id),
    )
    return EngagementCommentResponse.model_validate(comment)


@router.patch(
    "/comments/{comment_id}/discard",
    response_model=EngagementCommentResponse,
)
async def discard_comment(
    comment_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> EngagementCommentResponse:
    comment = await _get_comment_or_404(comment_id, tenant_id, db)
    comment.status = "discarded"  # type: ignore[assignment]
    await db.commit()
    await db.refresh(comment)
    return EngagementCommentResponse.model_validate(comment)


@router.post(
    "/comments/{comment_id}/regenerate",
    response_model=EngagementCommentResponse,
)
async def regenerate_comment(
    comment_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
    registry: LLMRegistry = Depends(get_llm_registry),
) -> EngagementCommentResponse:
    """Regenera comentario com nova sugestao LLM."""
    comment = await _get_comment_or_404(comment_id, tenant_id, db)

    # Buscar post pai
    post_stmt = select(ContentEngagementPost).where(
        ContentEngagementPost.id == comment.engagement_post_id,
        ContentEngagementPost.tenant_id == tenant_id,
    )
    post_result = await db.execute(post_stmt)
    post = post_result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post nao encontrado")

    # Buscar author_name e author_voice das configuracoes do tenant
    author_name, author_voice = await _get_author_settings(tenant_id, db)

    # Gerar novo comentario via LLM
    from services.content.comment_generator import generate_comments_for_post

    comment_angle = ""  # sem angle especifico no regenerate
    c1, c2 = await generate_comments_for_post(
        post={
            "post_text": post.post_text,
            "author_name": post.author_name or "",
            "author_title": post.author_title or "",
            "author_company": post.author_company or "",
        },
        author_name=author_name,
        author_voice=author_voice,
        comment_angle=comment_angle,
        registry=registry,
    )

    # Atualiza somente a variacao correspondente
    new_text = c1 if comment.variation == 1 else c2
    comment.comment_text = new_text  # type: ignore[assignment]
    comment.status = "pending"  # type: ignore[assignment]
    await db.commit()
    await db.refresh(comment)

    logger.info(
        "engagement.comment_regenerated",
        comment_id=str(comment_id),
        tenant_id=str(tenant_id),
    )
    return EngagementCommentResponse.model_validate(comment)


# ── Helpers privados ───────────────────────────────────────────────────────────


async def _get_post_or_404(
    post_id: uuid.UUID,
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> ContentEngagementPost:
    stmt = (
        select(ContentEngagementPost)
        .where(
            ContentEngagementPost.id == post_id,
            ContentEngagementPost.tenant_id == tenant_id,
        )
        .options(selectinload(ContentEngagementPost.suggested_comments))
    )
    result = await db.execute(stmt)
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post nao encontrado")
    return post


async def _get_comment_or_404(
    comment_id: uuid.UUID,
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> ContentEngagementComment:
    stmt = select(ContentEngagementComment).where(
        ContentEngagementComment.id == comment_id,
        ContentEngagementComment.tenant_id == tenant_id,
    )
    result = await db.execute(stmt)
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comentario nao encontrado")
    return comment


async def _get_author_settings(
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> tuple[str, str]:
    """Retorna (author_name, author_voice) das configuracoes do tenant."""
    from models.content_settings import ContentSettings

    stmt = select(ContentSettings).where(ContentSettings.tenant_id == tenant_id)
    result = await db.execute(stmt)
    settings = result.scalar_one_or_none()
    if settings:
        return (settings.author_name or "Autor", settings.author_voice or "")
    return ("Autor", "")


async def _on_comment_marked_posted(
    comment_id: uuid.UUID,
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> None:
    """
    Integracao com modulo de leads apos comentario postado manualmente.

    - Se o autor do post ja existe como lead: registra nota na timeline
    - Se nao existe: loga para futuro acompanhamento
    """
    from models.lead import Lead

    # Buscar comentario + post associado
    comment_stmt = select(ContentEngagementComment).where(
        ContentEngagementComment.id == comment_id
    )
    comment_result = await db.execute(comment_stmt)
    comment = comment_result.scalar_one_or_none()
    if not comment:
        return

    post_stmt = select(ContentEngagementPost).where(
        ContentEngagementPost.id == comment.engagement_post_id
    )
    post_result = await db.execute(post_stmt)
    post = post_result.scalar_one_or_none()
    if not post or not post.author_linkedin_urn:
        return

    # Buscar lead por linkedin_profile_id
    lead_stmt = select(Lead).where(
        Lead.tenant_id == tenant_id,
        Lead.linkedin_profile_id == post.author_linkedin_urn,
    )
    lead_result = await db.execute(lead_stmt)
    lead = lead_result.scalar_one_or_none()

    if lead:
        # Lead existe: registrar nota (notes append)
        note_entry = _build_lead_note_entry(
            author_name=post.author_name,
            post_url=post.post_url,
            posted_at=comment.posted_at,
        )
        existing_notes = lead.notes or ""
        lead.notes = f"{existing_notes}\n{note_entry}".strip()  # type: ignore[assignment]
        await db.commit()
        logger.info(
            "engagement.lead_note_created",
            lead_id=str(lead.id),
            post_author=post.author_name,
            tenant_id=str(tenant_id),
        )
    else:
        # Lead nao existe: apenas logar
        logger.info(
            "engagement.no_lead_found_for_post_author",
            author_urn=post.author_linkedin_urn,
            author_name=post.author_name,
            tenant_id=str(tenant_id),
        )


async def _undo_comment_marked_posted(
    comment_id: uuid.UUID,
    tenant_id: uuid.UUID,
    posted_at: datetime | None,
    db: AsyncSession,
) -> None:
    """Remove a nota de lead criada a partir de um clique acidental em comentario postado."""
    from models.lead import Lead

    if posted_at is None:
        return

    comment_stmt = select(ContentEngagementComment).where(
        ContentEngagementComment.id == comment_id
    )
    comment_result = await db.execute(comment_stmt)
    comment = comment_result.scalar_one_or_none()
    if not comment:
        return

    post_stmt = select(ContentEngagementPost).where(
        ContentEngagementPost.id == comment.engagement_post_id
    )
    post_result = await db.execute(post_stmt)
    post = post_result.scalar_one_or_none()
    if not post or not post.author_linkedin_urn:
        return

    lead_stmt = select(Lead).where(
        Lead.tenant_id == tenant_id,
        Lead.linkedin_profile_id == post.author_linkedin_urn,
    )
    lead_result = await db.execute(lead_stmt)
    lead = lead_result.scalar_one_or_none()
    if not lead or not lead.notes:
        return

    note_entry = _build_lead_note_entry(
        author_name=post.author_name,
        post_url=post.post_url,
        posted_at=posted_at,
    )
    notes_lines = lead.notes.splitlines()
    updated_notes = [line for line in notes_lines if line.strip() != note_entry]

    if len(updated_notes) == len(notes_lines):
        return

    lead.notes = "\n".join(updated_notes).strip() or None  # type: ignore[assignment]
    await db.commit()
    logger.info(
        "engagement.lead_note_removed",
        lead_id=str(lead.id),
        comment_id=str(comment_id),
        tenant_id=str(tenant_id),
    )


def _build_lead_note_entry(
    author_name: str | None,
    post_url: str | None,
    posted_at: datetime | None,
) -> str:
    note_date = (posted_at or datetime.now(UTC)).strftime("%Y-%m-%d")
    return (
        f"[{note_date}] "
        f"Comentou no post de {author_name or 'autor'} no LinkedIn. "
        f"URL: {post_url or 'N/A'}"
    )
