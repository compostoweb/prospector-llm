"""094 create content_articles table

Revision ID: 094
Revises: 093
Create Date: 2026-05-01 00:01:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "094"
down_revision = "093"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "content_articles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        # ── Conteudo do card ──────────────────────────────────────────
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("thumbnail_url", sa.Text(), nullable=True),
        sa.Column("thumbnail_s3_key", sa.Text(), nullable=True),
        sa.Column("linkedin_image_urn", sa.Text(), nullable=True),
        sa.Column(
            "commentary",
            sa.Text(),
            nullable=True,
            comment="Texto acima do card (ate 3000 chars)",
        ),
        # ── Status ────────────────────────────────────────────────────
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="draft",
            comment="draft | approved | scheduled | published | failed | deleted",
        ),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("linkedin_post_urn", sa.String(length=200), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        # ── First comment (mesma estrutura de content_posts) ──────────
        sa.Column("first_comment_text", sa.Text(), nullable=True),
        sa.Column(
            "first_comment_status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "first_comment_pin_status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("first_comment_urn", sa.Text(), nullable=True),
        sa.Column(
            "first_comment_posted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("first_comment_error", sa.Text(), nullable=True),
        # ── Idempotency lock ──────────────────────────────────────────
        sa.Column("processing_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "processing_lock_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        # ── Metricas ──────────────────────────────────────────────────
        sa.Column("impressions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("likes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("comments", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("shares", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "engagement_rate",
            sa.Numeric(5, 2),
            nullable=True,
        ),
        sa.Column(
            "metrics_updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        # ── Origem (newsletter parent) ────────────────────────────────
        sa.Column(
            "source_newsletter_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="FK para content_newsletters quando gerado por mark-as-published",
        ),
        sa.Column(
            "auto_scraped",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "scraped_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        # ── Soft delete + timestamps ──────────────────────────────────
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["source_newsletter_id"],
            ["content_newsletters.id"],
            ondelete="SET NULL",
        ),
    )

    op.create_index(
        "ix_content_articles_tenant_status",
        "content_articles",
        ["tenant_id", "status"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_content_articles_tenant_scheduled",
        "content_articles",
        ["tenant_id", "scheduled_for"],
        postgresql_where=sa.text("status = 'scheduled' AND deleted_at IS NULL"),
    )
    op.create_index(
        "ix_content_articles_source_newsletter",
        "content_articles",
        ["source_newsletter_id"],
        postgresql_where=sa.text("source_newsletter_id IS NOT NULL"),
    )

    # FK content_newsletters.derived_article_id -> content_articles.id
    op.create_foreign_key(
        "fk_content_newsletters_derived_article",
        "content_newsletters",
        "content_articles",
        ["derived_article_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_content_newsletters_derived_article",
        "content_newsletters",
        type_="foreignkey",
    )
    op.drop_index("ix_content_articles_source_newsletter", table_name="content_articles")
    op.drop_index("ix_content_articles_tenant_scheduled", table_name="content_articles")
    op.drop_index("ix_content_articles_tenant_status", table_name="content_articles")
    op.drop_table("content_articles")
