"""
services/content/revision_service.py

Phase 3D — versionamento de ContentPost.

Cria snapshots em JSONB antes de alteracoes importantes (publish, edit, restore).
Permite restaurar campos editaveis a partir de revisao anterior.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from models.content_post import ContentPost
from models.content_post_revision import ContentPostRevision

logger = structlog.get_logger()

# Campos snapshotados — adicionar aqui novos campos sem migration
_SNAPSHOT_FIELDS = (
    "title",
    "body",
    "hashtags",
    "pillar",
    "hook_type",
    "first_comment_text",
)

# Razoes validas (str30 no schema)
REASON_MANUAL_EDIT = "manual_edit"
REASON_PRE_PUBLISH = "pre_publish"
REASON_RESTORE = "restore"
REASON_SYSTEM = "system"


def _build_snapshot(post: ContentPost) -> dict[str, Any]:
    return {field: getattr(post, field, None) for field in _SNAPSHOT_FIELDS}


async def snapshot_post(
    db: AsyncSession,
    *,
    post: ContentPost,
    reason: str,
    user_id: uuid.UUID | None = None,
    flush: bool = True,
) -> ContentPostRevision:
    """Cria revisao do estado atual do post.

    Nao faz commit — caller controla a transacao.
    """
    revision = ContentPostRevision(
        post_id=post.id,
        tenant_id=post.tenant_id,
        snapshot=_build_snapshot(post),
        reason=reason,
        created_by=user_id,
    )
    db.add(revision)
    if flush:
        await db.flush()
    logger.info(
        "content.revision_created",
        post_id=str(post.id),
        revision_id=str(revision.id),
        reason=reason,
        tenant_id=str(post.tenant_id),
    )
    return revision


def apply_snapshot(post: ContentPost, snapshot: dict[str, Any]) -> list[str]:
    """Aplica snapshot ao post in-memory. Retorna lista de campos alterados."""
    changed: list[str] = []
    for field in _SNAPSHOT_FIELDS:
        if field in snapshot:
            old = getattr(post, field, None)
            new = snapshot[field]
            if old != new:
                setattr(post, field, new)
                changed.append(field)
    return changed
