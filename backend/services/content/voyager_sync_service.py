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

from dataclasses import dataclass, field
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from integrations.unipile_client import UnipileClient
from models.content_linkedin_account import ContentLinkedInAccount
from models.content_post import ContentPost
from models.linkedin_account import LinkedInAccount

logger = structlog.get_logger()


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
      2. GET /users/me → provider_id do dono da conta
      3. GET /users/{provider_id}/posts → posts com metricas
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
        result.error = "Nenhuma conta LinkedIn conectada via Unipile. Conecte em Configurações do Sistema."
        logger.info("unipile_sync.no_account", tenant_id=tenant_id)
        return result

    account_id: str = li_account.unipile_account_id

    # 2. Busca provider_id via GET /users/me
    try:
        async with UnipileClient() as client:
            profile = await client.get_own_profile(account_id)
    except Exception as exc:
        result.error = f"Erro ao buscar perfil Unipile: {exc}"
        logger.error("unipile_sync.profile_error", tenant_id=tenant_id, error=str(exc))
        return result

    provider_id = profile.get("provider_id") if profile else None
    if not provider_id:
        result.error = (
            "Perfil Unipile nao contem provider_id. "
            "Verifique se a conta LinkedIn esta conectada corretamente no Unipile."
        )
        logger.warning(
            "unipile_sync.no_provider_id",
            tenant_id=tenant_id,
            account_id=account_id,
            profile_keys=list(profile.keys()) if profile else [],
        )
        return result

    identifier: str = provider_id
    logger.info(
        "unipile_sync.profile_ok",
        tenant_id=tenant_id,
        identifier=identifier,
        name=profile.get("first_name"),
    )

    # 3. Busca posts com metricas via Unipile
    try:
        async with UnipileClient() as client:
            posts_raw = await client.get_own_posts_with_metrics(
                account_id=account_id,
                identifier=identifier,
                limit=limit,
            )
    except Exception as exc:
        result.error = f"Erro ao buscar posts: {exc}"
        logger.error("unipile_sync.posts_error", tenant_id=tenant_id, error=str(exc))
        return result

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

    for raw in posts_raw:
        # Identificador unico do post: social_id ou id do Unipile
        post_urn: str = raw.get("social_id") or raw.get("id", "")
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

        # Data de publicacao (parsed_datetime contem ISO8601, date e texto relativo)
        published_at: datetime | None = None
        date_str = raw.get("parsed_datetime") or raw.get("date")
        if date_str:
            try:
                parsed = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                published_at = parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed
            except (ValueError, TypeError):
                pass

        # Busca post existente pelo URN do LinkedIn
        existing_stmt = select(ContentPost).where(
            ContentPost.tenant_id == tenant_id,  # type: ignore[arg-type]
            ContentPost.linkedin_post_urn == post_urn,
        )
        existing_row = await db.execute(existing_stmt)
        existing: ContentPost | None = existing_row.scalar_one_or_none()

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
            result.posts_updated += 1
        else:
            # Cria novo post importado do LinkedIn — status "published"
            text: str = raw.get("text", "") or ""
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
