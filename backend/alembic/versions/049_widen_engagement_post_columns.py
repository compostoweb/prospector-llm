"""Widen engagement post varchar columns for LinkedIn data.

Revision ID: 049
Revises: 048
"""

import sqlalchemy as sa

from alembic import op

revision = "049"
down_revision = "048"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "content_engagement_posts",
        "author_name",
        type_=sa.String(300),
        existing_type=sa.String(150),
        existing_nullable=True,
    )
    op.alter_column(
        "content_engagement_posts",
        "author_title",
        type_=sa.String(500),
        existing_type=sa.String(200),
        existing_nullable=True,
    )
    op.alter_column(
        "content_engagement_posts",
        "author_company",
        type_=sa.String(300),
        existing_type=sa.String(150),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "content_engagement_posts",
        "author_name",
        type_=sa.String(150),
        existing_type=sa.String(300),
        existing_nullable=True,
    )
    op.alter_column(
        "content_engagement_posts",
        "author_title",
        type_=sa.String(200),
        existing_type=sa.String(500),
        existing_nullable=True,
    )
    op.alter_column(
        "content_engagement_posts",
        "author_company",
        type_=sa.String(150),
        existing_type=sa.String(300),
        existing_nullable=True,
    )
