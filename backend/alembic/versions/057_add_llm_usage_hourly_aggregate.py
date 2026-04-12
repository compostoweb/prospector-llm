"""057 — Cria tabela de agregação horária de uso de LLM.

Revision ID: 057
Revises: 056
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "057"
down_revision = "056"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "llm_usage_hourly",
        sa.Column("bucket_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("module", sa.String(length=80), nullable=False),
        sa.Column("task_type", sa.String(length=80), nullable=False),
        sa.Column("feature", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("requests", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint(
            "bucket_start",
            "provider",
            "model",
            "module",
            "task_type",
            "feature",
            "tenant_id",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "bucket_start",
            "provider",
            "model",
            "module",
            "task_type",
            "feature",
            name="uq_llm_usage_hourly_bucket_dimensions",
        ),
    )
    op.create_index(
        "ix_llm_usage_hourly_bucket_start", "llm_usage_hourly", ["bucket_start"], unique=False
    )
    op.create_index("ix_llm_usage_hourly_module", "llm_usage_hourly", ["module"], unique=False)
    op.create_index("ix_llm_usage_hourly_provider", "llm_usage_hourly", ["provider"], unique=False)
    op.create_index(
        "ix_llm_usage_hourly_task_type", "llm_usage_hourly", ["task_type"], unique=False
    )
    op.create_index(
        "ix_llm_usage_hourly_tenant_id", "llm_usage_hourly", ["tenant_id"], unique=False
    )
    op.execute(
        """
        INSERT INTO llm_usage_hourly (
            bucket_start,
            provider,
            model,
            module,
            task_type,
            feature,
            requests,
            input_tokens,
            output_tokens,
            total_tokens,
            estimated_cost_usd,
            tenant_id,
            created_at,
            updated_at
        )
        SELECT
            date_trunc('hour', created_at) AS bucket_start,
            provider,
            model,
            module,
            task_type,
            COALESCE(feature, '') AS feature,
            COUNT(*) AS requests,
            COALESCE(SUM(input_tokens), 0) AS input_tokens,
            COALESCE(SUM(output_tokens), 0) AS output_tokens,
            COALESCE(SUM(total_tokens), 0) AS total_tokens,
            COALESCE(SUM(estimated_cost_usd), 0) AS estimated_cost_usd,
            tenant_id,
            NOW() AS created_at,
            NOW() AS updated_at
        FROM llm_usage_events
        GROUP BY
            date_trunc('hour', created_at),
            provider,
            model,
            module,
            task_type,
            COALESCE(feature, ''),
            tenant_id
        """
    )


def downgrade() -> None:
    op.drop_index("ix_llm_usage_hourly_tenant_id", table_name="llm_usage_hourly")
    op.drop_index("ix_llm_usage_hourly_task_type", table_name="llm_usage_hourly")
    op.drop_index("ix_llm_usage_hourly_provider", table_name="llm_usage_hourly")
    op.drop_index("ix_llm_usage_hourly_module", table_name="llm_usage_hourly")
    op.drop_index("ix_llm_usage_hourly_bucket_start", table_name="llm_usage_hourly")
    op.drop_table("llm_usage_hourly")
