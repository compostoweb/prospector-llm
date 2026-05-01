"""096 account audit logs

Revision ID: 096
Revises: 095
Create Date: 2026-05-01 01:20:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "096"
down_revision = "095"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return inspector.has_table(table_name)


def _index_exists(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def _create_index_if_missing(index_name: str, columns: list[str]) -> None:
    table_name = "account_audit_logs"
    if not _index_exists(table_name, index_name):
        op.create_index(index_name, table_name, columns)


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


def upgrade() -> None:
    if not _table_exists("account_audit_logs"):
        op.create_table(
            "account_audit_logs",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("account_type", sa.String(length=30), nullable=False),
            sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("external_account_id", sa.String(length=200), nullable=True),
            sa.Column("provider_type", sa.String(length=50), nullable=True),
            sa.Column("event_type", sa.String(length=80), nullable=False),
            sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("provider_status", sa.String(length=80), nullable=True),
            sa.Column("message", sa.Text(), nullable=True),
            sa.Column("event_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    _create_index_if_missing("ix_account_audit_logs_tenant_id", ["tenant_id"])
    _create_index_if_missing("ix_account_audit_logs_account_type", ["account_type"])
    _create_index_if_missing("ix_account_audit_logs_account_id", ["account_id"])
    _create_index_if_missing(
        "ix_account_audit_logs_external_account_id",
        ["external_account_id"],
    )
    _create_index_if_missing("ix_account_audit_logs_provider_type", ["provider_type"])
    _create_index_if_missing("ix_account_audit_logs_event_type", ["event_type"])
    _create_index_if_missing("ix_account_audit_logs_actor_user_id", ["actor_user_id"])
    _create_index_if_missing("ix_account_audit_logs_provider_status", ["provider_status"])
    _create_index_if_missing(
        "ix_account_audit_logs_tenant_created",
        ["tenant_id", "created_at"],
    )
    op.execute("ALTER TABLE account_audit_logs ENABLE ROW LEVEL SECURITY")
    if not _policy_exists("account_audit_logs", "tenant_isolation"):
        op.execute(
            """
            CREATE POLICY tenant_isolation ON account_audit_logs
            USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid)
            """
        )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON account_audit_logs")
    op.drop_index("ix_account_audit_logs_tenant_created", table_name="account_audit_logs")
    op.drop_index("ix_account_audit_logs_provider_status", table_name="account_audit_logs")
    op.drop_index("ix_account_audit_logs_actor_user_id", table_name="account_audit_logs")
    op.drop_index("ix_account_audit_logs_event_type", table_name="account_audit_logs")
    op.drop_index("ix_account_audit_logs_provider_type", table_name="account_audit_logs")
    op.drop_index("ix_account_audit_logs_external_account_id", table_name="account_audit_logs")
    op.drop_index("ix_account_audit_logs_account_id", table_name="account_audit_logs")
    op.drop_index("ix_account_audit_logs_account_type", table_name="account_audit_logs")
    op.drop_index("ix_account_audit_logs_tenant_id", table_name="account_audit_logs")
    op.drop_table("account_audit_logs")
