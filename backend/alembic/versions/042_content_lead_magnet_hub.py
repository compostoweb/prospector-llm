"""042 — Content Hub inbound: lead magnets, landing pages, calculator e eventos SendPulse.

Revision ID: 042
Revises: 041
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "042"
down_revision = "041"
branch_labels = None
depends_on = None


def _enable_tenant_rls(table_name: str, policy_name: str) -> None:
    op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY {policy_name} ON {table_name}
        USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid)
        """
    )


def upgrade() -> None:
    op.create_table(
        "content_lead_magnets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("file_url", sa.Text(), nullable=True),
        sa.Column("cta_text", sa.String(100), nullable=True),
        sa.Column("sendpulse_list_id", sa.String(100), nullable=True),
        sa.Column("linked_calculator_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("content_lead_magnets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("total_leads_captured", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_downloads", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("conversion_rate", sa.Numeric(5, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("type IN ('pdf', 'calculator', 'email_sequence')", name="ck_content_lead_magnets_type"),
        sa.CheckConstraint("status IN ('draft', 'active', 'paused', 'archived')", name="ck_content_lead_magnets_status"),
    )
    op.create_index("ix_content_lead_magnets_tenant_id", "content_lead_magnets", ["tenant_id"])
    op.create_index("ix_content_lead_magnets_tenant_status", "content_lead_magnets", ["tenant_id", "status"])

    op.create_table(
        "content_lm_posts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lead_magnet_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("content_lead_magnets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content_post_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("content_posts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("post_type", sa.String(20), nullable=False, server_default="launch"),
        sa.Column("distribution_type", sa.String(20), nullable=False, server_default="comment"),
        sa.Column("trigger_word", sa.String(50), nullable=True),
        sa.Column("linkedin_post_urn", sa.String(100), nullable=True),
        sa.Column("comments_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("dms_sent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("clicks_lp", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("leads_from_post", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("post_type IN ('launch', 'relaunch', 'reminder')", name="ck_content_lm_posts_post_type"),
        sa.CheckConstraint("distribution_type IN ('comment', 'dm', 'link_bio')", name="ck_content_lm_posts_distribution_type"),
    )
    op.create_index("ix_content_lm_posts_tenant_id", "content_lm_posts", ["tenant_id"])
    op.create_index("ix_content_lm_posts_lm", "content_lm_posts", ["lead_magnet_id"])
    op.create_index("ix_content_lm_posts_post", "content_lm_posts", ["content_post_id"])

    op.create_table(
        "content_lm_leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lead_magnet_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("content_lead_magnets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lm_post_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("content_lm_posts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("linkedin_profile_url", sa.String(500), nullable=True),
        sa.Column("company", sa.String(150), nullable=True),
        sa.Column("role", sa.String(150), nullable=True),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("origin", sa.String(30), nullable=False, server_default="landing_page"),
        sa.Column("capture_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("sendpulse_list_id", sa.String(100), nullable=True),
        sa.Column("sendpulse_subscriber_id", sa.String(100), nullable=True),
        sa.Column("sendpulse_sync_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("sendpulse_last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sendpulse_last_error", sa.Text(), nullable=True),
        sa.Column("sequence_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("sequence_completed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("converted_via_email", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("converted_to_lead", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("leads.id", ondelete="SET NULL"), nullable=True),
        sa.Column("downloaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "origin IN ('linkedin_comment', 'linkedin_dm', 'landing_page', 'cold_outreach', 'direct', 'calculator')",
            name="ck_content_lm_leads_origin",
        ),
        sa.CheckConstraint(
            "sendpulse_sync_status IN ('pending', 'processing', 'synced', 'failed', 'skipped')",
            name="ck_content_lm_leads_sync_status",
        ),
        sa.CheckConstraint(
            "sequence_status IN ('pending', 'active', 'completed', 'unsubscribed')",
            name="ck_content_lm_leads_sequence_status",
        ),
        sa.UniqueConstraint("tenant_id", "lead_magnet_id", "email", name="uq_content_lm_leads_tenant_lm_email"),
    )
    op.create_index("ix_content_lm_leads_tenant_id", "content_lm_leads", ["tenant_id"])
    op.create_index("ix_content_lm_leads_lm", "content_lm_leads", ["lead_magnet_id"])
    op.create_index("ix_content_lm_leads_email", "content_lm_leads", ["email"])
    op.create_index("ix_content_lm_leads_lead", "content_lm_leads", ["lead_id"])

    op.create_table(
        "content_landing_pages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lead_magnet_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("content_lead_magnets.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("subtitle", sa.Text(), nullable=True),
        sa.Column("hero_image_url", sa.Text(), nullable=True),
        sa.Column("benefits", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("social_proof_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("author_bio", sa.Text(), nullable=True),
        sa.Column("author_photo_url", sa.Text(), nullable=True),
        sa.Column("meta_title", sa.String(255), nullable=True),
        sa.Column("meta_description", sa.Text(), nullable=True),
        sa.Column("published", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("total_views", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_submissions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("conversion_rate", sa.Numeric(5, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_content_landing_pages_tenant_id", "content_landing_pages", ["tenant_id"])

    op.create_table(
        "content_calculator_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lead_magnet_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("content_lead_magnets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("pessoas", sa.Integer(), nullable=False),
        sa.Column("horas_semana", sa.Numeric(5, 1), nullable=False),
        sa.Column("custo_hora", sa.Numeric(10, 2), nullable=False),
        sa.Column("cargo", sa.String(50), nullable=False),
        sa.Column("retrabalho_pct", sa.Numeric(5, 2), nullable=False),
        sa.Column("tipo_processo", sa.String(30), nullable=False),
        sa.Column("custo_mensal", sa.Numeric(12, 2), nullable=False),
        sa.Column("custo_retrabalho", sa.Numeric(12, 2), nullable=False),
        sa.Column("custo_total_mensal", sa.Numeric(12, 2), nullable=False),
        sa.Column("custo_anual", sa.Numeric(12, 2), nullable=False),
        sa.Column("investimento_estimado_min", sa.Numeric(12, 2), nullable=False),
        sa.Column("investimento_estimado_max", sa.Numeric(12, 2), nullable=False),
        sa.Column("roi_estimado", sa.Numeric(8, 2), nullable=False),
        sa.Column("payback_meses", sa.Numeric(5, 1), nullable=False),
        sa.Column("name", sa.String(150), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("company", sa.String(150), nullable=True),
        sa.Column("role", sa.String(150), nullable=True),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("converted_to_lead", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("leads.id", ondelete="SET NULL"), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("session_id", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_content_calculator_results_tenant_id", "content_calculator_results", ["tenant_id"])
    op.create_index("ix_content_calculator_results_lead_magnet", "content_calculator_results", ["lead_magnet_id"])
    op.create_index("ix_content_calculator_results_email", "content_calculator_results", ["email"])
    op.create_index("ix_content_calculator_results_lead", "content_calculator_results", ["lead_id"])

    op.create_table(
        "content_lm_email_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lead_magnet_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("content_lead_magnets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("lm_lead_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("content_lm_leads.id", ondelete="SET NULL"), nullable=True),
        sa.Column("calculator_result_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("content_calculator_results.id", ondelete="SET NULL"), nullable=True),
        sa.Column("provider", sa.String(30), nullable=False, server_default="sendpulse"),
        sa.Column("provider_event_id", sa.String(200), nullable=True),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("link_url", sa.Text(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("provider", "payload_hash", name="uq_content_lm_email_events_provider_payload_hash"),
    )
    op.create_index("ix_content_lm_email_events_tenant_id", "content_lm_email_events", ["tenant_id"])
    op.create_index("ix_content_lm_email_events_lm", "content_lm_email_events", ["lead_magnet_id"])
    op.create_index("ix_content_lm_email_events_lead", "content_lm_email_events", ["lm_lead_id"])
    op.create_index("ix_content_lm_email_events_event_type", "content_lm_email_events", ["event_type"])

    for table_name, policy_name in (
        ("content_lead_magnets", "content_lead_magnets_tenant_isolation"),
        ("content_lm_posts", "content_lm_posts_tenant_isolation"),
        ("content_lm_leads", "content_lm_leads_tenant_isolation"),
        ("content_landing_pages", "content_landing_pages_tenant_isolation"),
        ("content_calculator_results", "content_calculator_results_tenant_isolation"),
        ("content_lm_email_events", "content_lm_email_events_tenant_isolation"),
    ):
        _enable_tenant_rls(table_name, policy_name)


def downgrade() -> None:
    op.drop_table("content_lm_email_events")
    op.drop_table("content_calculator_results")
    op.drop_table("content_landing_pages")
    op.drop_table("content_lm_leads")
    op.drop_table("content_lm_posts")
    op.drop_table("content_lead_magnets")