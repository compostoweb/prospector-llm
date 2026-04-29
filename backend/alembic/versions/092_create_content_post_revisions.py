"""092 create content_post_revisions table

Revision ID: 092
Revises: 091
Create Date: 2026-04-30 00:04:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "092"
down_revision = "091"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "content_post_revisions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("post_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="Snapshot dos campos title, body, hashtags, pillar, hook_type, first_comment_text",
        ),
        sa.Column("reason", sa.String(length=30), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["post_id"], ["content_posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_content_post_revisions_post",
        "content_post_revisions",
        ["post_id", "created_at"],
    )
    op.create_index(
        "ix_content_post_revisions_tenant",
        "content_post_revisions",
        ["tenant_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_content_post_revisions_tenant", table_name="content_post_revisions")
    op.drop_index("ix_content_post_revisions_post", table_name="content_post_revisions")
    op.drop_table("content_post_revisions")
