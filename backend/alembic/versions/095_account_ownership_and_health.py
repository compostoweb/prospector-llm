"""095 account ownership and health fields

Revision ID: 095
Revises: 094
Create Date: 2026-05-01 00:30:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "095"
down_revision = "094"
branch_labels = None
depends_on = None

_ACCOUNT_TABLES = ("email_accounts", "linkedin_accounts")


def _add_common_account_columns(table_name: str) -> None:
    op.add_column(
        table_name,
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        table_name,
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(table_name, sa.Column("provider_status", sa.String(length=50), nullable=True))
    op.add_column(
        table_name, sa.Column("last_status_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        table_name,
        sa.Column("last_health_check_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(table_name, sa.Column("health_error", sa.Text(), nullable=True))
    op.add_column(table_name, sa.Column("connected_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        table_name, sa.Column("disconnected_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        table_name,
        sa.Column("reconnect_required_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_foreign_key(
        f"fk_{table_name}_owner_user_id",
        table_name,
        "users",
        ["owner_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        f"fk_{table_name}_created_by_user_id",
        table_name,
        "users",
        ["created_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        f"ix_{table_name}_owner_user_id",
        table_name,
        ["owner_user_id"],
    )
    op.create_index(
        f"ix_{table_name}_tenant_owner",
        table_name,
        ["tenant_id", "owner_user_id"],
    )
    op.create_index(
        f"ix_{table_name}_created_by_user_id",
        table_name,
        ["created_by_user_id"],
    )
    op.create_index(
        f"ix_{table_name}_provider_status",
        table_name,
        ["provider_status"],
    )


def _drop_common_account_columns(table_name: str) -> None:
    op.drop_index(f"ix_{table_name}_provider_status", table_name=table_name)
    op.drop_index(f"ix_{table_name}_created_by_user_id", table_name=table_name)
    op.drop_index(f"ix_{table_name}_tenant_owner", table_name=table_name)
    op.drop_index(f"ix_{table_name}_owner_user_id", table_name=table_name)
    op.drop_constraint(f"fk_{table_name}_created_by_user_id", table_name, type_="foreignkey")
    op.drop_constraint(f"fk_{table_name}_owner_user_id", table_name, type_="foreignkey")

    op.drop_column(table_name, "reconnect_required_at")
    op.drop_column(table_name, "disconnected_at")
    op.drop_column(table_name, "connected_at")
    op.drop_column(table_name, "health_error")
    op.drop_column(table_name, "last_health_check_at")
    op.drop_column(table_name, "last_status_at")
    op.drop_column(table_name, "provider_status")
    op.drop_column(table_name, "created_by_user_id")
    op.drop_column(table_name, "owner_user_id")


def upgrade() -> None:
    for table_name in _ACCOUNT_TABLES:
        _add_common_account_columns(table_name)

    op.create_index(
        "ix_linkedin_accounts_tenant_unipile_account",
        "linkedin_accounts",
        ["tenant_id", "unipile_account_id"],
        postgresql_where=sa.text("unipile_account_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_linkedin_accounts_tenant_unipile_account", table_name="linkedin_accounts")

    for table_name in reversed(_ACCOUNT_TABLES):
        _drop_common_account_columns(table_name)
