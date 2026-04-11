"""add content extension capture audit

Revision ID: 055
Revises: 054
Create Date: 2026-04-11 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "055"
down_revision = "054"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "content_extension_captures",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_platform", sa.String(length=30), nullable=False),
        sa.Column("destination_type", sa.String(length=30), nullable=False),
        sa.Column("result", sa.String(length=20), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("canonical_post_url", sa.String(length=500), nullable=True),
        sa.Column("dedup_key", sa.String(length=120), nullable=True),
        sa.Column("linked_object_type", sa.String(length=30), nullable=True),
        sa.Column("linked_object_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("client_context", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("captured_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_content_extension_captures_user_id"),
        "content_extension_captures",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_content_extension_captures_tenant_id"),
        "content_extension_captures",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_content_extension_captures_canonical_post_url"),
        "content_extension_captures",
        ["canonical_post_url"],
        unique=False,
    )
    op.create_index(
        op.f("ix_content_extension_captures_dedup_key"),
        "content_extension_captures",
        ["dedup_key"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_content_extension_captures_dedup_key"), table_name="content_extension_captures"
    )
    op.drop_index(
        op.f("ix_content_extension_captures_canonical_post_url"),
        table_name="content_extension_captures",
    )
    op.drop_index(
        op.f("ix_content_extension_captures_tenant_id"), table_name="content_extension_captures"
    )
    op.drop_index(
        op.f("ix_content_extension_captures_user_id"), table_name="content_extension_captures"
    )
    op.drop_table("content_extension_captures")
