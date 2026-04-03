"""031 -- Content Hub: tabelas do modulo de criacao e publicacao de conteudo LinkedIn.

Cria 6 tabelas novas para o modulo Content Hub:
  - content_posts        : posts do calendario editorial
  - content_themes       : banco de temas por pilar
  - content_settings     : configuracoes por tenant (1 registro/tenant)
  - content_references   : posts de referencia (few-shot LLM)
  - content_publish_log  : log imutavel de publicacoes
  - content_linkedin_accounts : contas OAuth LinkedIn por tenant (1/tenant)

Revision ID: 031
Revises: 030
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "031"
down_revision = "030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── content_posts ─────────────────────────────────────────────────
    op.create_table(
        "content_posts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("pillar", sa.String(20), nullable=False),
        sa.Column("hook_type", sa.String(30), nullable=True),
        sa.Column("hashtags", sa.Text, nullable=True),
        sa.Column("character_count", sa.Integer, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("publish_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("week_number", sa.Integer, nullable=True),
        sa.Column("linkedin_post_urn", sa.String(100), nullable=True),
        sa.Column("linkedin_scheduled_id", sa.String(100), nullable=True),
        sa.Column("impressions", sa.Integer, nullable=False, server_default="0"),
        sa.Column("likes", sa.Integer, nullable=False, server_default="0"),
        sa.Column("comments", sa.Integer, nullable=False, server_default="0"),
        sa.Column("shares", sa.Integer, nullable=False, server_default="0"),
        sa.Column("engagement_rate", sa.Numeric(5, 2), nullable=True),
        sa.Column("metrics_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("pillar IN ('authority', 'case', 'vision')", name="ck_content_posts_pillar"),
        sa.CheckConstraint("status IN ('draft', 'approved', 'scheduled', 'published', 'failed')", name="ck_content_posts_status"),
    )
    op.create_index("ix_content_posts_tenant_id", "content_posts", ["tenant_id"])
    op.create_index("ix_content_posts_tenant_status", "content_posts", ["tenant_id", "status"])

    # ── content_themes ────────────────────────────────────────────────
    op.create_table(
        "content_themes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("pillar", sa.String(20), nullable=False),
        sa.Column("used", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("used_in_post_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("content_posts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_custom", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("pillar IN ('authority', 'case', 'vision')", name="ck_content_themes_pillar"),
    )
    op.create_index("ix_content_themes_tenant_id", "content_themes", ["tenant_id"])
    op.create_index("ix_content_themes_tenant_pillar", "content_themes", ["tenant_id", "pillar"])

    # ── content_settings ──────────────────────────────────────────────
    op.create_table(
        "content_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("default_publish_time", sa.Time, nullable=True),
        sa.Column("posts_per_week", sa.Integer, nullable=False, server_default="3"),
        sa.Column("author_name", sa.String(100), nullable=True),
        sa.Column("author_voice", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ── content_references ────────────────────────────────────────────
    op.create_table(
        "content_references",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_name", sa.String(150), nullable=True),
        sa.Column("author_title", sa.String(200), nullable=True),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("hook_type", sa.String(30), nullable=True),
        sa.Column("pillar", sa.String(20), nullable=True),
        sa.Column("engagement_score", sa.Integer, nullable=True),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_content_references_tenant_id", "content_references", ["tenant_id"])

    # ── content_publish_log ───────────────────────────────────────────
    op.create_table(
        "content_publish_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("post_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("content_posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action", sa.String(30), nullable=False),
        sa.Column("linkedin_response", postgresql.JSONB, nullable=True),
        sa.Column("error_detail", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("action IN ('schedule', 'publish', 'cancel', 'fail')", name="ck_content_publish_log_action"),
    )
    op.create_index("ix_content_publish_log_tenant_id", "content_publish_log", ["tenant_id"])
    op.create_index("ix_content_publish_log_post_id", "content_publish_log", ["post_id"])

    # ── content_linkedin_accounts ─────────────────────────────────────
    op.create_table(
        "content_linkedin_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("person_id", sa.String(50), nullable=False),
        sa.Column("person_urn", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(150), nullable=True),
        sa.Column("access_token", sa.Text, nullable=False),
        sa.Column("refresh_token", sa.Text, nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scopes", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("content_linkedin_accounts")
    op.drop_table("content_publish_log")
    op.drop_table("content_references")
    op.drop_table("content_settings")
    op.drop_table("content_themes")
    op.drop_table("content_posts")
