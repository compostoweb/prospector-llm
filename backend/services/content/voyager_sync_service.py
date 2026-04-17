"""
services/content/voyager_sync_service.py

Sincronizacao de analytics de posts do LinkedIn via Unipile API.

  GET /users/me?account_id=X           → provider_id do dono da conta
  GET /users/{identifier}/posts        → posts com impressions_counter,
                                         reaction_counter, comment_counter,
                                         repost_counter

Usa a conta Unipile ja conectada no modulo de prospeccao (LinkedInAccount).

Invocado por:
  - workers/content_voyager.py  (Celery Beat 3x/dia)
  - api/routes/content/linkedin_auth.py  (POST /content/linkedin/sync manual)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.redis_client import redis_client
from integrations.unipile_client import UnipileClient
from models.content_engagement_session import ContentEngagementSession
from models.content_linkedin_account import ContentLinkedInAccount
from models.content_lm_post import ContentLMPost
from models.content_post import ContentPost
from models.content_publish_log import ContentPublishLog
from models.content_theme import ContentTheme
from models.linkedin_account import LinkedInAccount

logger = structlog.get_logger()

_OWN_PROFILE_CACHE_TTL = 86400
_OWN_PROFILE_MAX_ATTEMPTS = 2
_OWN_POSTS_MAX_ATTEMPTS = 2
_POST_RECONCILIATION_WINDOW = timedelta(minutes=5)


@dataclass
class VoyagerSyncResult:
    """Resultado de uma sincronizacao via Unipile."""

    tenant_id: str
    posts_created: int = 0
    posts_updated: int = 0
    posts_skipped: int = 0
    error: str | None = None
    synced_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def success(self) -> bool:
        return self.error is None

    def to_dict(self) -> dict:
        return {
            "tenant_id": self.tenant_id,
            "posts_created": self.posts_created,
            "posts_updated": self.posts_updated,
            "posts_skipped": self.posts_skipped,
            "error": self.error,
            "success": self.success,
            "synced_at": self.synced_at.isoformat(),
        }


async def sync_voyager_for_tenant(
    tenant_id: str,
    db: AsyncSession,
    limit: int = 50,
) -> VoyagerSyncResult:
    """
    Sincroniza analytics LinkedIn para um tenant via Unipile API.

    Fluxo:
      1. Busca LinkedInAccount (prospeccao) com unipile_account_id
            2. Resolve identificadores do perfil (provider_id/public_identifier/username salvo)
            3. GET /users/{identifier}/posts → posts com metricas
      4. Upsert posts no banco (match por linkedin_post_urn)
      5. Atualiza last_voyager_sync_at na ContentLinkedInAccount

    Args:
        tenant_id: UUID do tenant como string
        db: Sessao SQLAlchemy async
        limit: Maximo de posts a sincronizar (default 50)

    Returns:
        VoyagerSyncResult com contadores e possivel erro
    """
    result = VoyagerSyncResult(tenant_id=tenant_id)

    # 1. Busca conta Unipile do tenant (modulo prospeccao)
    stmt = select(LinkedInAccount).where(
        LinkedInAccount.tenant_id == tenant_id,  # type: ignore[arg-type]
        LinkedInAccount.is_active.is_(True),
        LinkedInAccount.unipile_account_id.is_not(None),
    )
    row = await db.execute(stmt)
    li_account: LinkedInAccount | None = row.scalar_one_or_none()

    if not li_account or not li_account.unipile_account_id:
        result.error = (
            "Nenhuma conta LinkedIn conectada via Unipile. Conecte em Configurações do Sistema."
        )
        logger.info("unipile_sync.no_account", tenant_id=tenant_id)
        return result

    account_id: str = li_account.unipile_account_id

    # 2. Resolve identificadores possiveis do perfil
    profile: dict[str, Any] | None = None
    profile_error: Exception | None = None
    provider_candidates: list[tuple[str, str]] = []
    fallback_candidates: list[tuple[str, str]] = []

    # 3. Busca posts com metricas via Unipile
    posts_raw: list[dict] | None = None
    identifier: str | None = None
    identifier_source: str | None = None
    attempt_errors: list[str] = []
    attempted_candidates: set[str] = set()

    try:
        async with UnipileClient() as client:
            cached_identifiers = await _get_cached_own_profile_identifiers(account_id)
            _append_identifier_candidate(
                provider_candidates,
                "cached_provider_id",
                cached_identifiers.get("provider_id"),
            )

            for source, candidate in provider_candidates:
                try:
                    attempted_candidates.add(candidate)
                    posts_raw = await _fetch_own_posts_with_retry(
                        client=client,
                        account_id=account_id,
                        identifier=candidate,
                        limit=limit,
                    )
                    identifier = candidate
                    identifier_source = source
                    break
                except Exception as exc:
                    attempt_errors.append(f"{source}={candidate}: {exc}")
                    logger.warning(
                        "unipile_sync.identifier_attempt_failed",
                        tenant_id=tenant_id,
                        source=source,
                        identifier=candidate,
                        error=str(exc),
                    )

            if identifier is None:
                try:
                    profile = await _fetch_own_profile_with_retry(client, account_id)
                except Exception as exc:
                    profile_error = exc
                    logger.warning(
                        "unipile_sync.profile_error",
                        tenant_id=tenant_id,
                        error=str(exc),
                    )
                else:
                    await _cache_own_profile_identifiers(account_id, profile)
                    _append_identifier_candidate(
                        provider_candidates,
                        "provider_id",
                        profile.get("provider_id"),
                    )

                for source, candidate in provider_candidates:
                    if candidate in attempted_candidates:
                        continue
                    try:
                        attempted_candidates.add(candidate)
                        posts_raw = await _fetch_own_posts_with_retry(
                            client=client,
                            account_id=account_id,
                            identifier=candidate,
                            limit=limit,
                        )
                        identifier = candidate
                        identifier_source = source
                        break
                    except Exception as exc:
                        attempt_errors.append(f"{source}={candidate}: {exc}")
                        logger.warning(
                            "unipile_sync.identifier_attempt_failed",
                            tenant_id=tenant_id,
                            source=source,
                            identifier=candidate,
                            error=str(exc),
                        )

            if identifier is None and not provider_candidates:
                _append_identifier_candidate(
                    fallback_candidates,
                    "linkedin_username",
                    li_account.linkedin_username,
                )

            if identifier is None:
                for source, candidate in fallback_candidates:
                    try:
                        attempted_candidates.add(candidate)
                        posts_raw = await client.get_own_posts_with_metrics(
                            account_id=account_id,
                            identifier=candidate,
                            limit=limit,
                        )
                        identifier = candidate
                        identifier_source = source
                        break
                    except Exception as exc:
                        attempt_errors.append(f"{source}={candidate}: {exc}")
                        logger.warning(
                            "unipile_sync.identifier_attempt_failed",
                            tenant_id=tenant_id,
                            source=source,
                            identifier=candidate,
                            error=str(exc),
                        )
    except Exception as exc:
        result.error = f"Erro ao buscar posts: {exc}"
        logger.error("unipile_sync.posts_error", tenant_id=tenant_id, error=str(exc))
        return result

    if identifier is None or posts_raw is None:
        result.error = (
            "Nao foi possivel identificar o perfil LinkedIn na Unipile. "
            "Configure o linkedin_username da conta ou verifique a conexao com a Unipile."
            if not provider_candidates and not fallback_candidates
            else "Erro ao buscar posts na Unipile."
        )
        if not provider_candidates and not fallback_candidates and profile_error is not None:
            result.error = f"{result.error} Erro original: {profile_error}"
        if attempt_errors:
            result.error = f"{result.error} Tentativas: {' | '.join(attempt_errors)}"
        logger.error(
            "unipile_sync.posts_all_identifiers_failed",
            tenant_id=tenant_id,
            attempts=attempt_errors,
            profile_keys=list(profile.keys()) if profile else [],
            has_linkedin_username=bool(li_account.linkedin_username),
        )
        return result

    logger.info(
        "unipile_sync.profile_ok",
        tenant_id=tenant_id,
        identifier=identifier,
        identifier_source=identifier_source,
        name=(profile or {}).get("first_name"),
    )

    if not posts_raw:
        logger.info("unipile_sync.no_posts", tenant_id=tenant_id)
        await _update_sync_timestamp(tenant_id, db)
        await db.commit()
        return result

    logger.info(
        "unipile_sync.posts_fetched",
        tenant_id=tenant_id,
        count=len(posts_raw),
    )

    # 4. Upsert posts no banco
    now = datetime.now(UTC)
    parsed_posts: list[dict[str, Any]] = []
    post_urns: list[str] = []
    reconciliation_texts: set[str] = set()
    reconciliation_dates: list[datetime] = []

    for raw in posts_raw:
        post_urn = str(raw.get("social_id") or raw.get("id") or "").strip()
        post_text = str(raw.get("text", "") or "")
        normalized_text = _normalize_post_body(post_text)
        published_at = _parse_unipile_post_datetime(raw)

        parsed_posts.append(
            {
                "raw": raw,
                "post_urn": post_urn,
                "text": post_text,
                "normalized_text": normalized_text,
                "published_at": published_at,
            }
        )

        if post_urn:
            post_urns.append(post_urn)
        if normalized_text and published_at is not None:
            reconciliation_texts.add(normalized_text)
            reconciliation_dates.append(published_at)

    normalized_post_urns = [post_urn for post_urn in post_urns if post_urn]
    existing_posts_by_urn: dict[str, ContentPost] = {}
    reconciliation_candidates: list[ContentPost] = []

    if normalized_post_urns:
        existing_posts_stmt = select(ContentPost).where(
            ContentPost.tenant_id == tenant_id,  # type: ignore[arg-type]
            ContentPost.linkedin_post_urn.in_(normalized_post_urns),
        )
        existing_posts_result = await db.execute(existing_posts_stmt)
        existing_posts_by_urn = {
            str(post.linkedin_post_urn): post
            for post in existing_posts_result.scalars().all()
            if post.linkedin_post_urn
        }

    if reconciliation_texts and reconciliation_dates:
        reconciliation_start = min(reconciliation_dates) - _POST_RECONCILIATION_WINDOW
        reconciliation_end = max(reconciliation_dates) + _POST_RECONCILIATION_WINDOW
        reconciliation_stmt = select(ContentPost).where(
            ContentPost.tenant_id == tenant_id,  # type: ignore[arg-type]
            ContentPost.status == "published",
            ContentPost.published_at.is_not(None),
            ContentPost.published_at >= reconciliation_start,
            ContentPost.published_at <= reconciliation_end,
        )
        reconciliation_result = await db.execute(reconciliation_stmt)
        reconciliation_candidates = list(reconciliation_result.scalars())

    for parsed_post in parsed_posts:
        raw = parsed_post["raw"]
        # Identificador unico do post: social_id ou id do Unipile
        post_urn = parsed_post["post_urn"]
        if not post_urn:
            result.posts_skipped += 1
            continue

        # Metricas do Unipile
        impressions = int(raw.get("impressions_counter") or 0)
        likes = int(raw.get("reaction_counter") or 0)
        comments_count = int(raw.get("comment_counter") or 0)
        shares = int(raw.get("repost_counter") or 0)
        saves = int(raw.get("save_counter") or 0)

        # Calcula engagement_rate se houver impressoes
        engagement_rate: float | None = None
        if impressions > 0:
            engagement_rate = round(
                (likes + comments_count + shares + saves) / impressions * 100, 2
            )

        published_at = parsed_post["published_at"]

        matched_posts = _find_matching_posts(
            existing_posts_by_urn=existing_posts_by_urn,
            reconciliation_candidates=reconciliation_candidates,
            post_urn=post_urn,
            normalized_body=parsed_post["normalized_text"],
            published_at=published_at,
        )
        existing = _select_canonical_post(matched_posts)

        if existing:
            # Atualiza apenas metricas (nao sobrescreve titulo/body manualmente editados)
            existing.impressions = impressions  # type: ignore[assignment]
            existing.likes = likes  # type: ignore[assignment]
            existing.comments = comments_count  # type: ignore[assignment]
            existing.shares = shares  # type: ignore[assignment]
            existing.saves = saves  # type: ignore[assignment]
            if engagement_rate is not None:
                existing.engagement_rate = engagement_rate  # type: ignore[assignment]
            existing.metrics_updated_at = now  # type: ignore[assignment]
            if published_at and not existing.published_at:
                existing.published_at = published_at  # type: ignore[assignment]
            duplicate_posts = _find_consolidation_duplicates(matched_posts, canonical_post=existing)
            if duplicate_posts:
                await _consolidate_duplicate_posts(
                    db,
                    canonical_post=existing,
                    duplicate_posts=duplicate_posts,
                )
            result.posts_updated += 1
        else:
            # Cria novo post importado do LinkedIn — status "published"
            text = cast(str, parsed_post["text"])
            if not text.strip():
                # Post sem texto (somente imagem, video, etc.)
                result.posts_skipped += 1
                continue

            new_post = ContentPost(
                tenant_id=tenant_id,  # type: ignore[arg-type]
                title=f"[LinkedIn] {text[:80].strip()}{'...' if len(text) > 80 else ''}",
                body=text,
                pillar="authority",  # default — pode ser ajustado manualmente depois
                status="published",
                hook_type=None,
                linkedin_post_urn=post_urn,
                impressions=impressions,
                likes=likes,
                comments=comments_count,
                shares=shares,
                saves=saves,
                engagement_rate=engagement_rate,
                metrics_updated_at=now,
                published_at=published_at,
                character_count=len(text),
            )
            db.add(new_post)
            result.posts_created += 1

    # 5. Commit e atualiza timestamp
    await db.flush()
    await _update_sync_timestamp(tenant_id, db)
    await db.commit()

    logger.info(
        "unipile_sync.complete",
        tenant_id=tenant_id,
        posts_created=result.posts_created,
        posts_updated=result.posts_updated,
        posts_skipped=result.posts_skipped,
    )
    return result


async def _update_sync_timestamp(
    tenant_id: str,
    db: AsyncSession,
) -> None:
    """Atualiza o timestamp de ultima sincronizacao na ContentLinkedInAccount."""
    stmt = select(ContentLinkedInAccount).where(
        ContentLinkedInAccount.tenant_id == tenant_id,  # type: ignore[arg-type]
        ContentLinkedInAccount.is_active.is_(True),
    )
    row = await db.execute(stmt)
    account = row.scalar_one_or_none()
    if account:
        account.last_voyager_sync_at = datetime.now(UTC)  # type: ignore[assignment]
        await db.flush()


async def _fetch_own_profile_with_retry(client: UnipileClient, account_id: str) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(1, _OWN_PROFILE_MAX_ATTEMPTS + 1):
        try:
            return await client.get_own_profile(account_id)
        except Exception as exc:
            last_error = exc
            if attempt >= _OWN_PROFILE_MAX_ATTEMPTS:
                break
            logger.warning(
                "unipile_sync.profile_retry",
                account_id=account_id,
                attempt=attempt,
                error=str(exc),
            )

    assert last_error is not None
    raise last_error


async def _fetch_own_posts_with_retry(
    *,
    client: UnipileClient,
    account_id: str,
    identifier: str,
    limit: int,
) -> list[dict]:
    last_error: Exception | None = None
    for attempt in range(1, _OWN_POSTS_MAX_ATTEMPTS + 1):
        try:
            return await client.get_own_posts_with_metrics(
                account_id=account_id,
                identifier=identifier,
                limit=limit,
            )
        except Exception as exc:
            last_error = exc
            if attempt >= _OWN_POSTS_MAX_ATTEMPTS or not _is_connection_error(exc):
                break
            logger.warning(
                "unipile_sync.posts_retry",
                account_id=account_id,
                identifier=identifier,
                attempt=attempt,
                error=str(exc),
            )

    assert last_error is not None
    raise last_error


def _is_connection_error(exc: Exception) -> bool:
    message = str(exc)
    return "Falha de conexao com Unipile" in message or "ReadTimeout" in message


def _append_identifier_candidate(
    candidates: list[tuple[str, str]],
    source: str,
    value: Any,
) -> None:
    normalized = str(value or "").strip()
    if not normalized:
        return
    if any(existing == normalized for _, existing in candidates):
        return
    candidates.append((source, normalized))


async def _get_cached_own_profile_identifiers(account_id: str) -> dict[str, str]:
    cache_key = f"unipile:own_profile:{account_id}"
    try:
        cached = await redis_client.get(cache_key)
    except Exception as exc:
        logger.debug(
            "unipile_sync.profile_cache_read_failed",
            account_id=account_id,
            error=str(exc),
        )
        return {}

    if not cached:
        return {}

    try:
        payload = json.loads(cached)
    except (TypeError, ValueError) as exc:
        logger.debug(
            "unipile_sync.profile_cache_invalid",
            account_id=account_id,
            error=str(exc),
        )
        return {}

    if not isinstance(payload, dict):
        return {}

    return {
        "provider_id": str(payload.get("provider_id") or "").strip(),
        "public_identifier": str(payload.get("public_identifier") or "").strip(),
    }


async def _cache_own_profile_identifiers(account_id: str, profile: dict[str, Any]) -> None:
    provider_id = str(profile.get("provider_id") or "").strip()
    public_identifier = str(profile.get("public_identifier") or "").strip()
    if not provider_id and not public_identifier:
        return

    cache_key = f"unipile:own_profile:{account_id}"
    payload = json.dumps(
        {
            "provider_id": provider_id,
            "public_identifier": public_identifier,
        }
    )

    try:
        await redis_client.set(cache_key, payload, ex=_OWN_PROFILE_CACHE_TTL)
    except Exception as exc:
        logger.debug(
            "unipile_sync.profile_cache_write_failed",
            account_id=account_id,
            error=str(exc),
        )


def _normalize_post_body(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").strip().split("\n"))


def _parse_unipile_post_datetime(raw: dict[str, Any]) -> datetime | None:
    date_str = raw.get("parsed_datetime") or raw.get("date")
    if not date_str:
        return None

    try:
        parsed = datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None

    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


def _find_matching_posts(
    *,
    existing_posts_by_urn: dict[str, ContentPost],
    reconciliation_candidates: list[ContentPost],
    post_urn: str,
    normalized_body: str,
    published_at: datetime | None,
) -> list[ContentPost]:
    matches: list[ContentPost] = []
    seen_post_ids: set[str] = set()

    exact_match = existing_posts_by_urn.get(post_urn)
    if exact_match is not None:
        seen_post_ids.add(str(exact_match.id))
        matches.append(exact_match)

    if not normalized_body or published_at is None:
        return matches

    for candidate in reconciliation_candidates:
        if str(candidate.id) in seen_post_ids:
            continue
        if not _post_matches_body_and_time(
            candidate,
            normalized_body=normalized_body,
            published_at=published_at,
        ):
            continue
        seen_post_ids.add(str(candidate.id))
        matches.append(candidate)

    return matches


def _post_matches_body_and_time(
    candidate: ContentPost,
    *,
    normalized_body: str,
    published_at: datetime,
) -> bool:
    candidate_published_at = _coerce_datetime(candidate.published_at)
    if candidate_published_at is None:
        return False
    if _normalize_post_body(candidate.body) != normalized_body:
        return False
    return abs(candidate_published_at - published_at) <= _POST_RECONCILIATION_WINDOW


def _select_canonical_post(candidates: list[ContentPost]) -> ContentPost | None:
    if not candidates:
        return None

    return min(candidates, key=_canonical_post_priority)


def _canonical_post_priority(post: ContentPost) -> tuple[int, int, datetime, str]:
    publish_date_rank = 0 if post.publish_date is not None else 1
    imported_rank = 1 if _looks_like_imported_post(post) else 0
    created_at = _coerce_datetime(post.created_at) or datetime.max.replace(tzinfo=UTC)
    return (publish_date_rank, imported_rank, created_at, str(post.id))


def _looks_like_imported_post(post: ContentPost) -> bool:
    return post.publish_date is None and post.title.startswith("[LinkedIn]")


def _find_consolidation_duplicates(
    candidates: list[ContentPost],
    *,
    canonical_post: ContentPost,
) -> list[ContentPost]:
    duplicates: list[ContentPost] = []
    for candidate in candidates:
        if candidate.id == canonical_post.id:
            continue
        if _looks_like_imported_post(candidate):
            duplicates.append(candidate)
    return duplicates


async def _consolidate_duplicate_posts(
    db: AsyncSession,
    *,
    canonical_post: ContentPost,
    duplicate_posts: list[ContentPost],
) -> None:
    for duplicate_post in duplicate_posts:
        await _reassign_post_references(
            db,
            source_post_id=duplicate_post.id,
            target_post_id=canonical_post.id,
        )
        await db.delete(duplicate_post)
        logger.info(
            "unipile_sync.duplicate_post_consolidated",
            canonical_post_id=str(canonical_post.id),
            duplicate_post_id=str(duplicate_post.id),
        )


async def _reassign_post_references(
    db: AsyncSession,
    *,
    source_post_id: Any,
    target_post_id: Any,
) -> None:
    content_theme_result = await db.execute(
        select(ContentTheme).where(ContentTheme.used_in_post_id == source_post_id)
    )
    for theme_row in content_theme_result.scalars():
        theme_row.used_in_post_id = target_post_id  # type: ignore[assignment]

    content_lm_post_result = await db.execute(
        select(ContentLMPost).where(ContentLMPost.content_post_id == source_post_id)
    )
    for lm_post_row in content_lm_post_result.scalars():
        lm_post_row.content_post_id = target_post_id  # type: ignore[assignment]

    publish_log_result = await db.execute(
        select(ContentPublishLog).where(ContentPublishLog.post_id == source_post_id)
    )
    for publish_log_row in publish_log_result.scalars():
        publish_log_row.post_id = target_post_id  # type: ignore[assignment]

    engagement_session_result = await db.execute(
        select(ContentEngagementSession).where(
            ContentEngagementSession.linked_post_id == source_post_id
        )
    )
    for session_row in engagement_session_result.scalars():
        session_row.linked_post_id = target_post_id  # type: ignore[assignment]


def _coerce_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
    if isinstance(value, str) and value:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
    return None
