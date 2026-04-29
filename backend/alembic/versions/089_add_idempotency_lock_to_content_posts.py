"""089 add idempotency lock fields to content_posts

Revision ID: 089
Revises: 088
Create Date: 2026-04-30 00:01:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "089"
down_revision = "088"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "content_posts",
        sa.Column("processing_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "content_posts",
        sa.Column("processing_lock_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    # Indice parcial para acelerar varredura por posts em processamento
    op.create_index(
        "ix_content_posts_processing",
        "content_posts",
        ["processing_at"],
        postgresql_where=sa.text("processing_at IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_content_posts_processing", table_name="content_posts")
    op.drop_column("content_posts", "processing_lock_id")
    op.drop_column("content_posts", "processing_at")
