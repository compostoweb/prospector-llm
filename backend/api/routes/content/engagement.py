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

_QUEUE_PICKUP_TIMEOUT = timedelta(seconds=45)
_SESSION_TIMEOUT = timedelta(minutes=5)

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.dependencies import get_effective_tenant_id, get_llm_registry, get_session_flexible
from integrations.llm.registry import LLMRegistry
from models.content_engagement_comment import ContentEngagementComment
from models.content_engagement_discovery_query import ContentEngagementDiscoveryQuery
from models.content_engagement_event import ContentEngagementEvent
from models.content_engagement_post import ContentEngagementPost
from models.content_engagement_session import ContentEngagementSession
from models.content_reference import ContentReference
from models.content_theme import ContentTheme
from schemas.content_engagement import (
    AddManualPostRequest,
    EngagementCommentResponse,
    EngagementPostResponse,
    EngagementSessionDetailResponse,
    EngagementSessionResponse,
    GoogleDiscoveryComposeRequest,
    GoogleDiscoveryQueryResponse,
    ImportExternalPostsRequest,
    ImportExternalPostsResponse,
    RunScanRequest,
    RunScanResponse,
)
from services.content.engagement_post_identity import (
    build_post_identity,
    choose_primary_post_source,
    merge_post_sources,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/engagement", tags=["Content Hub — Engagement"])

_ENGAGEMENT_SCAN_QUEUE = "content-engagement"


def _normalize_string_list(values: list[str] | None) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()

    for value in values or []:
        item = value.strip()
        key = item.lower()
        if not item or key in seen:
            continue
        seen.add(key)
        normalized.append(item)

    return normalized


async def _record_session_event(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    session_id: uuid.UUID,
    event_type: str,
    payload: dict[str, object] | None = None,
) -> None:
    db.add(
        ContentEngagementEvent(
            tenant_id=tenant_id,
            session_id=session_id,
            event_type=event_type,
            payload=payload,
        )
    )


async def _load_session_or_404(
    db: AsyncSession,
    *,
    session_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> ContentEngagementSession:
    stmt = select(ContentEngagementSession).where(
        ContentEngagementSession.id == session_id,
        ContentEngagementSession.tenant_id == tenant_id,
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")
    return session


async def _load_discovery_query_or_404(
    db: AsyncSession,
    *,
    query_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> ContentEngagementDiscoveryQuery:
    stmt = select(ContentEngagementDiscoveryQuery).where(
        ContentEngagementDiscoveryQuery.id == query_id,
        ContentEngagementDiscoveryQuery.tenant_id == tenant_id,
    )
    result = await db.execute(stmt)
    query = result.scalar_one_or_none()
    if not query:
        raise HTTPException(status_code=404, detail="Composicao do Google nao encontrada")
    return query


def _apply_post_payload(
    post: ContentEngagementPost,
    body: AddManualPostRequest,
    *,
    canonical_post_url: str | None,
    dedup_key: str | None,
    merge_increment: bool,
) -> None:
    if body.post_type == "icp" and post.post_type != "icp":
        post.post_type = "icp"

    post.source = choose_primary_post_source(post.source, body.source)
    post.merged_sources = merge_post_sources(post.merged_sources, body.source)
    if merge_increment:
        post.merge_count = max(post.merge_count, 1) + 1
    else:
        post.merge_count = max(post.merge_count, 1)

    if canonical_post_url and not post.canonical_post_url:
        post.canonical_post_url = canonical_post_url
    if dedup_key and not post.dedup_key:
        post.dedup_key = dedup_key
    if body.post_url and not post.post_url:
        post.post_url = body.post_url
    if body.author_name and not post.author_name:
        post.author_name = body.author_name
    if body.author_title and not post.author_title:
        post.author_title = body.author_title
    if body.author_company and not post.author_company:
        post.author_company = body.author_company
    if body.author_profile_url and not post.author_profile_url:
        post.author_profile_url = body.author_profile_url
    if body.post_text and len(body.post_text) > len(post.post_text):
        post.post_text = body.post_text

    post.likes = max(post.likes, body.likes)
    post.comments = max(post.comments, body.comments)
    post.shares = max(post.shares, body.shares)

    computed_score = body.comments * 3 + body.likes + body.shares * 2
    post.engagement_score = (
        max(post.engagement_score or 0, computed_score) if computed_score else post.engagement_score
    )


async def _upsert_external_post(
    db: AsyncSession,
    *,
    session_id: uuid.UUID,
    tenant_id: uuid.UUID,
    body: AddManualPostRequest,
) -> tuple[ContentEngagementPost, bool]:
    await db.flush()

    canonical_post_url, dedup_key = build_post_identity(
        post_url=body.post_url,
        post_text=body.post_text,
        author_name=body.author_name,
    )

    existing_post: ContentEngagementPost | None = None
    if dedup_key:
        existing_stmt = select(ContentEngagementPost).where(
            ContentEngagementPost.session_id == session_id,
            ContentEngagementPost.tenant_id == tenant_id,
        )
        existing_result = await db.execute(existing_stmt)

        for candidate in existing_result.scalars().all():
            candidate_canonical_url, candidate_dedup_key = build_post_identity(
                post_url=candidate.post_url,
                post_text=candidate.post_text,
                author_name=candidate.author_name,
            )
            if candidate_canonical_url and not candidate.canonical_post_url:
                candidate.canonical_post_url = candidate_canonical_url
            if candidate_dedup_key and not candidate.dedup_key:
                candidate.dedup_key = candidate_dedup_key
            if not candidate.merged_sources:
                candidate.merged_sources = merge_post_sources([], candidate.source)
            if not candidate.merge_count:
                candidate.merge_count = 1
            if candidate_dedup_key == dedup_key:
                existing_post = candidate
                break

    if existing_post:
        _apply_post_payload(
            existing_post,
            body,
            canonical_post_url=canonical_post_url,
            dedup_key=dedup_key,
            merge_increment=True,
        )
        db.add(existing_post)
        return existing_post, False

    post = ContentEngagementPost(
        tenant_id=tenant_id,
        session_id=session_id,
        post_type=body.post_type,
        source=body.source,
        merged_sources=merge_post_sources([], body.source),
        merge_count=1,
        post_text=body.post_text,
        post_url=body.post_url,
        canonical_post_url=canonical_post_url,
        dedup_key=dedup_key,
        author_name=body.author_name,
        author_title=body.author_title,
        author_company=body.author_company,
        author_profile_url=body.author_profile_url,
        likes=body.likes,
        comments=body.comments,
        shares=body.shares,
        engagement_score=(body.comments * 3 + body.likes + body.shares * 2) or None,
    )
    db.add(post)
    return post, True


def _build_google_operator_queries(body: GoogleDiscoveryComposeRequest) -> list[str]:
    keywords = _normalize_string_list(body.keywords)
    exact_phrases = [
        phrase
        for phrase in _normalize_string_list(body.exact_phrases)
        if phrase.strip().lower() != "comentários"
    ]
    titles = _normalize_string_list(body.titles)
    sectors = _normalize_string_list(body.sectors)
    company = body.company.strip() if body.company else ""
    site_scope = "site:linkedin.com/posts"

    queries: list[str] = []
    seen: set[str] = set()

    def add_query(parts: list[str]) -> None:
        text = " ".join(part for part in parts if part).strip()
        key = text.lower()
        if not text or key in seen or len(queries) >= body.max_queries:
            return
        seen.add(key)
        queries.append(text)

    for keyword in keywords:
        add_query([site_scope, f'"{keyword}"', '"comentários"'])
        for phrase in exact_phrases[:2] or [""]:
            add_query([site_scope, f'"{keyword}"', f'"{phrase}"' if phrase else ""])
        for title in titles[:2]:
            add_query([site_scope, f'"{keyword}"', f'"{title}"', '"comentários"'])
        for sector in sectors[:2]:
            add_query([site_scope, f'"{keyword}"', f'"{sector}"', '"comentários"'])
        if company:
            add_query([site_scope, f'"{keyword}"', f'"{company}"', '"comentários"'])

    if not queries:
        add_query([site_scope, '"comentários"'])

    return queries[: body.max_queries]


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
    selected_theme_ids = [str(theme_id) for theme_id in body.selected_theme_ids or []]
    selected_theme_titles: list[str] = []

    if body.selected_theme_ids:
        theme_stmt = select(ContentTheme).where(
            ContentTheme.tenant_id == tenant_id,
            ContentTheme.id.in_(body.selected_theme_ids),
        )
        theme_rows = await db.execute(theme_stmt)
        themes = theme_rows.scalars().all()
        theme_title_map = {str(theme.id): theme.title for theme in themes}
        selected_theme_titles = [
            theme_title_map[theme_id]
            for theme_id in selected_theme_ids
            if theme_id in theme_title_map
        ]

    manual_keywords = _normalize_string_list(body.manual_keywords)
    requested_keywords = _normalize_string_list(body.keywords)
    if not requested_keywords:
        requested_keywords = _normalize_string_list([*selected_theme_titles, *manual_keywords])

    requested_icp_titles = _normalize_string_list(
        body.icp_filters.titles if body.icp_filters else None
    )
    requested_icp_sectors = _normalize_string_list(
        body.icp_filters.sectors if body.icp_filters else None
    )

    session = ContentEngagementSession(
        tenant_id=tenant_id,
        linked_post_id=body.linked_post_id,
        status="running",
        scan_source="apify",
        selected_theme_ids=selected_theme_ids or None,
        selected_theme_titles=selected_theme_titles or None,
        manual_keywords=manual_keywords or None,
        effective_keywords=requested_keywords or None,
        icp_titles_used=requested_icp_titles or None,
        icp_sectors_used=requested_icp_sectors or None,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    await _record_session_event(
        db,
        tenant_id=tenant_id,
        session_id=session.id,
        event_type="scan_requested",
        payload={
            "linked_post_id": str(body.linked_post_id) if body.linked_post_id else None,
            "selected_theme_ids": selected_theme_ids,
            "selected_theme_titles": selected_theme_titles,
            "manual_keywords": manual_keywords,
            "effective_keywords": requested_keywords,
            "icp_titles_used": requested_icp_titles,
            "icp_sectors_used": requested_icp_sectors,
        },
    )
    await db.commit()

    # Disparar task Celery (import local para evitar circular)
    from workers.content_engagement import run_engagement_scan

    run_engagement_scan.apply_async(
        kwargs={
            "session_id": str(session.id),
            "tenant_id": str(tenant_id),
            "linked_post_id": str(body.linked_post_id) if body.linked_post_id else None,
            "keywords": requested_keywords or None,
            "icp_titles": requested_icp_titles or None,
            "icp_sectors": requested_icp_sectors or None,
        },
        queue=_ENGAGEMENT_SCAN_QUEUE,
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
    return [EngagementSessionResponse.model_validate(s) for s in result.scalars().all()]


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
            selectinload(ContentEngagementSession.events),
            selectinload(ContentEngagementSession.posts).selectinload(
                ContentEngagementPost.suggested_comments
            ),
        )
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")

    # Auto-fail: evita sessao eternamente "running" quando a fila nao e consumida
    # ou quando o scan passa do tempo maximo esperado.
    if session.status == "running" and session.created_at is not None:
        now = datetime.now(UTC)
        elapsed = now - session.created_at
        if session.current_step is None and elapsed > _QUEUE_PICKUP_TIMEOUT:
            session.status = "failed"
            session.error_message = "Fila de engajamento nao iniciou o scan. Verifique se o worker-content-engagement esta ativo."
            session.completed_at = now
            db.add(session)
            await db.commit()
            await db.refresh(session)
            logger.warning(
                "engagement_session.queue_pickup_timeout",
                session_id=str(session.id),
                elapsed_s=int(elapsed.total_seconds()),
            )
            await _record_session_event(
                db,
                tenant_id=tenant_id,
                session_id=session.id,
                event_type="scan_failed",
                payload={
                    "reason": "queue_pickup_timeout",
                    "elapsed_s": int(elapsed.total_seconds()),
                },
            )
            await db.commit()
        elif elapsed > _SESSION_TIMEOUT:
            session.status = "failed"
            session.error_message = "Timeout: scan nao completou em 5 minutos"
            session.completed_at = now
            db.add(session)
            await db.commit()
            await db.refresh(session)
            logger.warning(
                "engagement_session.auto_failed",
                session_id=str(session.id),
                elapsed_s=int(elapsed.total_seconds()),
            )
            await _record_session_event(
                db,
                tenant_id=tenant_id,
                session_id=session.id,
                event_type="scan_failed",
                payload={"reason": "session_timeout", "elapsed_s": int(elapsed.total_seconds())},
            )
            await db.commit()

    return EngagementSessionDetailResponse.model_validate(session)


@router.post(
    "/discovery/google/compose",
    response_model=list[GoogleDiscoveryQueryResponse],
    status_code=status.HTTP_201_CREATED,
)
async def compose_google_discovery_queries(
    body: GoogleDiscoveryComposeRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> list[GoogleDiscoveryQueryResponse]:
    queries = _build_google_operator_queries(body)
    criteria = {
        "keywords": _normalize_string_list(body.keywords),
        "exact_phrases": _normalize_string_list(body.exact_phrases),
        "titles": _normalize_string_list(body.titles),
        "sectors": _normalize_string_list(body.sectors),
        "company": body.company.strip() if body.company else None,
        "linked_post_id": str(body.linked_post_id) if body.linked_post_id else None,
    }

    records: list[ContentEngagementDiscoveryQuery] = []
    for query_text in queries:
        record = ContentEngagementDiscoveryQuery(
            tenant_id=tenant_id,
            provider="google_operators",
            query_text=query_text,
            criteria=criteria,
        )
        db.add(record)
        records.append(record)

    await db.commit()
    for record in records:
        await db.refresh(record)

    return [GoogleDiscoveryQueryResponse.model_validate(record) for record in records]


@router.get(
    "/discovery/google/history",
    response_model=list[GoogleDiscoveryQueryResponse],
)
async def list_google_discovery_history(
    limit: int = Query(20, ge=1, le=100),
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> list[GoogleDiscoveryQueryResponse]:
    stmt = (
        select(ContentEngagementDiscoveryQuery)
        .where(
            ContentEngagementDiscoveryQuery.tenant_id == tenant_id,
            ContentEngagementDiscoveryQuery.provider == "google_operators",
        )
        .order_by(ContentEngagementDiscoveryQuery.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return [
        GoogleDiscoveryQueryResponse.model_validate(record) for record in result.scalars().all()
    ]


# ── Posts ──────────────────────────────────────────────────────────────────────


@router.get("/posts", response_model=list[EngagementPostResponse])
async def list_posts(
    session_id: uuid.UUID | None = Query(None),
    post_type: str | None = Query(None),
    is_saved: bool | None = Query(None),
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> list[EngagementPostResponse]:
    stmt = select(ContentEngagementPost).where(ContentEngagementPost.tenant_id == tenant_id)
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
    return [EngagementPostResponse.model_validate(p) for p in result.scalars().all()]


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
    await _load_session_or_404(db, session_id=session_id, tenant_id=tenant_id)

    post, created = await _upsert_external_post(
        db,
        session_id=session_id,
        tenant_id=tenant_id,
        body=body,
    )
    await db.commit()
    loaded_post_result = await db.execute(
        select(ContentEngagementPost)
        .options(selectinload(ContentEngagementPost.suggested_comments))
        .where(
            ContentEngagementPost.id == post.id,
            ContentEngagementPost.tenant_id == tenant_id,
        )
    )
    loaded_post = loaded_post_result.scalar_one()
    logger.info(
        "engagement.post_added_manual",
        post_id=str(loaded_post.id),
        session_id=str(session_id),
        tenant_id=str(tenant_id),
        source=body.source,
        created=created,
    )
    return EngagementPostResponse.model_validate(loaded_post)


@router.post(
    "/posts/import",
    response_model=ImportExternalPostsResponse,
    status_code=status.HTTP_201_CREATED,
)
async def import_external_posts(
    body: ImportExternalPostsRequest,
    session_id: uuid.UUID = Query(..., description="ID da sessao onde inserir os posts"),
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> ImportExternalPostsResponse:
    await _load_session_or_404(db, session_id=session_id, tenant_id=tenant_id)
    discovery_query: ContentEngagementDiscoveryQuery | None = None
    if body.discovery_query_id:
        discovery_query = await _load_discovery_query_or_404(
            db,
            query_id=body.discovery_query_id,
            tenant_id=tenant_id,
        )

    created_count = 0
    merged_count = 0
    imported_posts: list[ContentEngagementPost] = []

    for post_payload in body.posts:
        post, created = await _upsert_external_post(
            db,
            session_id=session_id,
            tenant_id=tenant_id,
            body=post_payload,
        )
        imported_posts.append(post)
        if created:
            created_count += 1
        else:
            merged_count += 1

    if discovery_query:
        discovery_query.imported_session_id = session_id
        db.add(discovery_query)

    await _record_session_event(
        db,
        tenant_id=tenant_id,
        session_id=session_id,
        event_type="external_posts_imported",
        payload={
            "created_count": created_count,
            "merged_count": merged_count,
            "sources": sorted({post.source for post in imported_posts}),
            "discovery_query_id": str(body.discovery_query_id) if body.discovery_query_id else None,
            "discovery_query_text": discovery_query.query_text if discovery_query else None,
        },
    )
    await db.commit()

    post_ids = list(dict.fromkeys(post.id for post in imported_posts))
    loaded_posts_result = await db.execute(
        select(ContentEngagementPost)
        .options(selectinload(ContentEngagementPost.suggested_comments))
        .where(
            ContentEngagementPost.tenant_id == tenant_id,
            ContentEngagementPost.id.in_(post_ids),
        )
    )
    loaded_posts_by_id = {post.id: post for post in loaded_posts_result.scalars().all()}
    response_posts = [loaded_posts_by_id[post.id] for post in imported_posts]

    return ImportExternalPostsResponse(
        session_id=session_id,
        created_count=created_count,
        merged_count=merged_count,
        posts=[EngagementPostResponse.model_validate(post) for post in response_posts],
    )


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
    stmt = select(ContentEngagementComment).where(ContentEngagementComment.tenant_id == tenant_id)
    if session_id:
        stmt = stmt.where(ContentEngagementComment.session_id == session_id)
    if comment_status:
        stmt = stmt.where(ContentEngagementComment.status == comment_status)
    stmt = stmt.order_by(
        ContentEngagementComment.engagement_post_id,
        ContentEngagementComment.variation,
    )
    result = await db.execute(stmt)
    return [EngagementCommentResponse.model_validate(c) for c in result.scalars().all()]


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
    await _record_session_event(
        db,
        tenant_id=tenant_id,
        session_id=comment.session_id,
        event_type="comment_posted",
        payload={
            "comment_id": str(comment_id),
            "posted_at": comment.posted_at.isoformat() if comment.posted_at else None,
        },
    )
    await db.commit()
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
    await _record_session_event(
        db,
        tenant_id=tenant_id,
        session_id=comment.session_id,
        event_type="comment_unposted",
        payload={"comment_id": str(comment_id)},
    )
    await db.commit()
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
    comment_stmt = select(ContentEngagementComment).where(ContentEngagementComment.id == comment_id)
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

    comment_stmt = select(ContentEngagementComment).where(ContentEngagementComment.id == comment_id)
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
