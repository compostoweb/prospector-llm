from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TenantMixin, TimestampMixin


class ContentExtensionCapture(Base, TenantMixin, TimestampMixin):
    __tablename__ = "content_extension_captures"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_platform: Mapped[str] = mapped_column(String(30), nullable=False, default="linkedin")
    destination_type: Mapped[str] = mapped_column(String(30), nullable=False)
    result: Mapped[str] = mapped_column(String(20), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    canonical_post_url: Mapped[str | None] = mapped_column(String(500), nullable=True, index=True)
    dedup_key: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    linked_object_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    linked_object_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    client_context: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    captured_payload: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
