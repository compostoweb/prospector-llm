"""098 reconcile missing legacy RLS

Revision ID: 098
Revises: 097
Create Date: 2026-05-01 03:40:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "098"
down_revision = "097"
branch_labels = None
depends_on = None

_LEGACY_MULTI_TENANT_TABLES = (
    "audio_files",
    "cadence_steps",
    "cadences",
    "email_accounts",
    "email_templates",
    "email_unsubscribes",
    "interactions",
    "lead_tags",
    "leads",
    "linkedin_accounts",
    "sandbox_runs",
    "sandbox_steps",
    "tenant_integrations",
    "warmup_campaigns",
    "warmup_logs",
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
    for table_name in _LEGACY_MULTI_TENANT_TABLES:
        _enable_tenant_rls(table_name)


def downgrade() -> None:
    for table_name in reversed(_LEGACY_MULTI_TENANT_TABLES):
        _disable_tenant_rls(table_name)