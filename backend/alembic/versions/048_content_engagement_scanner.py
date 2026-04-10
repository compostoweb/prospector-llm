"""048_content_engagement_scanner.

Cria 3 tabelas do modulo LinkedIn Engagement Scanner (Content Hub):
  - content_engagement_sessions  : sessoes de garimpagem (agrupa uma rodada)
  - content_engagement_posts     : posts garimpados (reference + Icp)
  - content_engagement_comments  : sugestoes de comentario para posts ICP

Revision ID: 048
Revises: 047
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "048"
down_revision = "047"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── content_engagement_sessions ───────────────────────────────────
    op.create_table(
        "content_engagement_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "linked_post_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_posts.id", ondelete="SET NULL"),
            nullable=True,
            comment="post que sera publicado em seguida (opcional)",
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="running"),
        sa.Column("references_found", sa.Integer, nullable=False, server_default="0"),
        sa.Column("icp_posts_found", sa.Integer, nullable=False, server_default="0"),
        sa.Column("comments_generated", sa.Integer, nullable=False, server_default="0"),
        sa.Column("comments_posted", sa.Integer, nullable=False, server_default="0"),
        sa.Column("scan_source", sa.String(20), nullable=False, server_default="apify"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('running', 'completed', 'partial', 'failed')",
            name="ck_engagement_sessions_status",
        ),
        sa.CheckConstraint(
            "scan_source IN ('linkedin_api', 'apify', 'manual')",
            name="ck_engagement_sessions_scan_source",
        ),
    )
    op.create_index(
        "ix_engagement_sessions_tenant_id",
        "content_engagement_sessions",
        ["tenant_id"],
    )
    op.create_index(
        "ix_engagement_sessions_tenant_created",
        "content_engagement_sessions",
        ["tenant_id", "created_at"],
    )

    # ── content_engagement_posts ───────────────────────────────────────
    op.create_table(
        "content_engagement_posts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_engagement_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "post_type",
            sa.String(20),
            nullable=False,
            comment="reference | icp",
        ),
        sa.Column("author_name", sa.String(150), nullable=True),
        sa.Column("author_title", sa.String(200), nullable=True),
        sa.Column("author_company", sa.String(150), nullable=True),
        sa.Column("author_linkedin_urn", sa.String(100), nullable=True),
        sa.Column("author_profile_url", sa.String(500), nullable=True),
        sa.Column("post_url", sa.String(500), nullable=True),
        sa.Column("post_text", sa.Text, nullable=False),
        sa.Column("post_published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("likes", sa.Integer, nullable=False, server_default="0"),
        sa.Column("comments", sa.Integer, nullable=False, server_default="0"),
        sa.Column("shares", sa.Integer, nullable=False, server_default="0"),
        sa.Column("engagement_score", sa.Integer, nullable=True),
        sa.Column("hook_type", sa.String(30), nullable=True),
        sa.Column("pillar", sa.String(20), nullable=True),
        sa.Column("why_it_performed", sa.Text, nullable=True),
        sa.Column("what_to_replicate", sa.Text, nullable=True),
        sa.Column("is_saved", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "post_type IN ('reference', 'icp')",
            name="ck_engagement_posts_post_type",
        ),
    )
    op.create_index(
        "ix_engagement_posts_tenant_id",
        "content_engagement_posts",
        ["tenant_id"],
    )
    op.create_index(
        "ix_engagement_posts_session_id",
        "content_engagement_posts",
        ["session_id"],
    )
    op.create_index(
        "ix_engagement_posts_tenant_type",
        "content_engagement_posts",
        ["tenant_id", "post_type"],
    )

    # ── content_engagement_comments ────────────────────────────────────
    op.create_table(
        "content_engagement_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "engagement_post_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_engagement_posts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_engagement_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("comment_text", sa.Text, nullable=False),
        sa.Column("variation", sa.Integer, nullable=False, server_default="1"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'selected', 'posted', 'discarded')",
            name="ck_engagement_comments_status",
        ),
        sa.CheckConstraint(
            "variation IN (1, 2)",
            name="ck_engagement_comments_variation",
        ),
    )
    op.create_index(
        "ix_engagement_comments_tenant_id",
        "content_engagement_comments",
        ["tenant_id"],
    )
    op.create_index(
        "ix_engagement_comments_post_id",
        "content_engagement_comments",
        ["engagement_post_id"],
    )
    op.create_index(
        "ix_engagement_comments_session_id",
        "content_engagement_comments",
        ["session_id"],
    )


def downgrade() -> None:
    op.drop_table("content_engagement_comments")
    op.drop_table("content_engagement_posts")
    op.drop_table("content_engagement_sessions")
