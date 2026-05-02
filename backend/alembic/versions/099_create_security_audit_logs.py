"""099 create security audit logs

Revision ID: 099
Revises: 098
Create Date: 2026-05-01 06:20:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "099"
down_revision = "098"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return inspector.has_table(table_name)


def _existing_indexes(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    index_names: set[str] = set()
    for index in inspector.get_indexes(table_name):
        index_name = index.get("name")
        if isinstance(index_name, str):
            index_names.add(index_name)
    return index_names


def upgrade() -> None:
    if not _table_exists("security_audit_logs"):
        op.create_table(
            "security_audit_logs",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("scope_tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("event_type", sa.String(length=120), nullable=False),
            sa.Column("resource_type", sa.String(length=80), nullable=False),
            sa.Column("resource_id", sa.String(length=200), nullable=True),
            sa.Column("action", sa.String(length=60), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("message", sa.Text(), nullable=True),
            sa.Column("ip_address", sa.String(length=120), nullable=True),
            sa.Column("user_agent", sa.String(length=500), nullable=True),
            sa.Column("event_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["scope_tenant_id"], ["tenants.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )

    existing_indexes = _existing_indexes("security_audit_logs")
    if "ix_security_audit_logs_scope_tenant_created" not in existing_indexes:
        op.create_index(
            "ix_security_audit_logs_scope_tenant_created",
            "security_audit_logs",
            ["scope_tenant_id", "created_at"],
            unique=False,
        )
    if "ix_security_audit_logs_event_created" not in existing_indexes:
        op.create_index(
            "ix_security_audit_logs_event_created",
            "security_audit_logs",
            ["event_type", "created_at"],
            unique=False,
        )
    if op.f("ix_security_audit_logs_scope_tenant_id") not in existing_indexes:
        op.create_index(op.f("ix_security_audit_logs_scope_tenant_id"), "security_audit_logs", ["scope_tenant_id"], unique=False)
    if op.f("ix_security_audit_logs_actor_user_id") not in existing_indexes:
        op.create_index(op.f("ix_security_audit_logs_actor_user_id"), "security_audit_logs", ["actor_user_id"], unique=False)
    if op.f("ix_security_audit_logs_event_type") not in existing_indexes:
        op.create_index(op.f("ix_security_audit_logs_event_type"), "security_audit_logs", ["event_type"], unique=False)
    if op.f("ix_security_audit_logs_resource_type") not in existing_indexes:
        op.create_index(op.f("ix_security_audit_logs_resource_type"), "security_audit_logs", ["resource_type"], unique=False)
    if op.f("ix_security_audit_logs_resource_id") not in existing_indexes:
        op.create_index(op.f("ix_security_audit_logs_resource_id"), "security_audit_logs", ["resource_id"], unique=False)
    if op.f("ix_security_audit_logs_action") not in existing_indexes:
        op.create_index(op.f("ix_security_audit_logs_action"), "security_audit_logs", ["action"], unique=False)
    if op.f("ix_security_audit_logs_status") not in existing_indexes:
        op.create_index(op.f("ix_security_audit_logs_status"), "security_audit_logs", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_security_audit_logs_status"), table_name="security_audit_logs")
    op.drop_index(op.f("ix_security_audit_logs_action"), table_name="security_audit_logs")
    op.drop_index(op.f("ix_security_audit_logs_resource_id"), table_name="security_audit_logs")
    op.drop_index(op.f("ix_security_audit_logs_resource_type"), table_name="security_audit_logs")
    op.drop_index(op.f("ix_security_audit_logs_event_type"), table_name="security_audit_logs")
    op.drop_index(op.f("ix_security_audit_logs_actor_user_id"), table_name="security_audit_logs")
    op.drop_index(op.f("ix_security_audit_logs_scope_tenant_id"), table_name="security_audit_logs")
    op.drop_index("ix_security_audit_logs_event_created", table_name="security_audit_logs")
    op.drop_index("ix_security_audit_logs_scope_tenant_created", table_name="security_audit_logs")
    op.drop_table("security_audit_logs")