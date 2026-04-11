"""add source and dedup fields to engagement posts

Revision ID: 053
Revises: 052
Create Date: 2026-04-10 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "053"
down_revision = "052"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "content_engagement_posts",
        sa.Column(
            "source",
            sa.String(length=30),
            nullable=False,
            server_default="apify",
            comment="apify | linkedin_api | manual | google",
        ),
    )
    op.add_column(
        "content_engagement_posts",
        sa.Column("canonical_post_url", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "content_engagement_posts",
        sa.Column("dedup_key", sa.String(length=120), nullable=True),
    )
    op.create_index(
        "ix_content_engagement_posts_session_dedup_key",
        "content_engagement_posts",
        ["session_id", "dedup_key"],
        unique=False,
    )

    op.execute(
        """
        UPDATE content_engagement_posts AS post
        SET source = session.scan_source
        FROM content_engagement_sessions AS session
        WHERE session.id = post.session_id
        """
    )

    op.alter_column("content_engagement_posts", "source", server_default=None)


def downgrade() -> None:
    op.drop_index(
        "ix_content_engagement_posts_session_dedup_key", table_name="content_engagement_posts"
    )
    op.drop_column("content_engagement_posts", "dedup_key")
    op.drop_column("content_engagement_posts", "canonical_post_url")
    op.drop_column("content_engagement_posts", "source")
