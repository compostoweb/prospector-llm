"""097 enable RLS on remaining multi-tenant tables

Revision ID: 097
Revises: 096
Create Date: 2026-05-01 03:20:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "097"
down_revision = "096"
branch_labels = None
depends_on = None

_MULTI_TENANT_TABLES = (
    "anthropic_batch_jobs",
    "capture_execution_logs",
    "capture_schedule_configs",
    "content_articles",
    "content_calculator_results",
    "content_engagement_comments",
    "content_engagement_discovery_queries",
    "content_engagement_events",
    "content_engagement_posts",
    "content_engagement_sessions",
    "content_extension_captures",
    "content_gallery_images",
    "content_landing_pages",
    "content_lead_magnets",
    "content_linkedin_accounts",
    "content_lm_email_events",
    "content_lm_leads",
    "content_lm_posts",
    "content_newsletters",
    "content_post_revisions",
    "content_posts",
    "content_publish_log",
    "content_references",
    "content_settings",
    "content_themes",
    "enrichment_jobs",
    "lead_contact_points",
    "lead_emails",
    "lead_lists",
    "llm_usage_events",
    "llm_usage_hourly",
    "manual_tasks",
    "tenant_users",
)


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return inspector.has_table(table_name)


def _policy_exists(table_name: str, policy_name: str) -> bool:
    bind = op.get_bind()
    return bool(
        bind.execute(
            sa.text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM pg_policy
                    WHERE polrelid = to_regclass(:table_name)
                      AND polname = :policy_name
                )
                """
            ),
            {"table_name": table_name, "policy_name": policy_name},
        ).scalar()
    )


def _enable_tenant_rls(table_name: str) -> None:
    policy_name = "tenant_isolation"
    if not _table_exists(table_name):
        return

    op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
    if not _policy_exists(table_name, policy_name):
        op.execute(
            f"""
            CREATE POLICY {policy_name} ON {table_name}
            USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid)
            """
        )


def _disable_tenant_rls(table_name: str) -> None:
    if not _table_exists(table_name):
        return

    op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table_name}")
    op.execute(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY")


def upgrade() -> None:
    for table_name in _MULTI_TENANT_TABLES:
        _enable_tenant_rls(table_name)


def downgrade() -> None:
    for table_name in reversed(_MULTI_TENANT_TABLES):
        _disable_tenant_rls(table_name)