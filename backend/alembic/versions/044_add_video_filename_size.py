"""044_add_video_filename_size.

Revision ID: 044
Revises: 043
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "044"
down_revision = "043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "content_posts",
        sa.Column("video_filename", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "content_posts",
        sa.Column("video_size_bytes", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("content_posts", "video_size_bytes")
    op.drop_column("content_posts", "video_filename")
