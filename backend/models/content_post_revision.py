"""
models/content_post_revision.py

Snapshot historico de campos editaveis de ContentPost para
auditoria e rollback (Phase 3D).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TenantMixin


class ContentPostRevision(Base, TenantMixin):
    """
    Versao snapshot de um ContentPost. Criado antes de alteracoes
    importantes (publish, edit pos-published, restauracao).

    Campos JSON em `snapshot`: title, body, hashtags, pillar, hook_type,
    first_comment_text. Outros campos podem ser adicionados sem migration.
    """

    __tablename__ = "content_post_revisions"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    post_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("content_posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    reason: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="manual_edit | pre_publish | restore | system",
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
