"""088 add first comment + pin fields to content_posts

Revision ID: 088
Revises: 087
Create Date: 2026-04-30 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "088"
down_revision = "087"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "content_posts",
        sa.Column("first_comment_text", sa.Text(), nullable=True),
    )
    op.add_column(
        "content_posts",
        sa.Column(
            "first_comment_status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column(
        "content_posts",
        sa.Column(
            "first_comment_pin_status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column(
        "content_posts",
        sa.Column("first_comment_urn", sa.Text(), nullable=True),
    )
    op.add_column(
        "content_posts",
        sa.Column("first_comment_posted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "content_posts",
        sa.Column("first_comment_error", sa.Text(), nullable=True),
    )
    # Strip server_default after backfill so application controls value
    op.alter_column("content_posts", "first_comment_status", server_default=None)
    op.alter_column("content_posts", "first_comment_pin_status", server_default=None)


def downgrade() -> None:
    op.drop_column("content_posts", "first_comment_error")
    op.drop_column("content_posts", "first_comment_posted_at")
    op.drop_column("content_posts", "first_comment_urn")
    op.drop_column("content_posts", "first_comment_pin_status")
    op.drop_column("content_posts", "first_comment_status")
    op.drop_column("content_posts", "first_comment_text")
