"""add merge metadata to engagement posts

Revision ID: 054
Revises: 053
Create Date: 2026-04-10 00:30:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "054"
down_revision = "053"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "content_engagement_posts",
        sa.Column(
            "merged_sources",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "content_engagement_posts",
        sa.Column("merge_count", sa.Integer(), nullable=False, server_default="1"),
    )
    op.execute(
        """
        UPDATE content_engagement_posts
        SET merged_sources = to_jsonb(ARRAY[source]),
            merge_count = 1
        """
    )
    op.alter_column("content_engagement_posts", "merge_count", server_default=None)


def downgrade() -> None:
    op.drop_column("content_engagement_posts", "merge_count")
    op.drop_column("content_engagement_posts", "merged_sources")
