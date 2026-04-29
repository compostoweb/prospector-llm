"""091 add soft delete to content_posts

Revision ID: 091
Revises: 090
Create Date: 2026-04-30 00:03:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "091"
down_revision = "090"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "content_posts",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Indice parcial: queries normais filtram por deleted_at IS NULL
    op.create_index(
        "ix_content_posts_active",
        "content_posts",
        ["tenant_id", "status"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_content_posts_active", table_name="content_posts")
    op.drop_column("content_posts", "deleted_at")
