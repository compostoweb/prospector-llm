"""056 — Cria tabela de eventos de uso de LLM.

Revision ID: 056
Revises: 055_add_content_extension_capture_audit
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "056"
down_revision = "055"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "llm_usage_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("module", sa.String(length=80), nullable=False),
        sa.Column("task_type", sa.String(length=80), nullable=False),
        sa.Column("feature", sa.String(length=80), nullable=True),
        sa.Column("entity_type", sa.String(length=50), nullable=True),
        sa.Column("entity_id", sa.String(length=120), nullable=True),
        sa.Column("secondary_entity_type", sa.String(length=50), nullable=True),
        sa.Column("secondary_entity_id", sa.String(length=120), nullable=True),
        sa.Column("prompt_chars", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_chars", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("is_estimated", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("request_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_llm_usage_events_created_at", "llm_usage_events", ["created_at"], unique=False)
    op.create_index("ix_llm_usage_events_feature", "llm_usage_events", ["feature"], unique=False)
    op.create_index("ix_llm_usage_events_model", "llm_usage_events", ["model"], unique=False)
    op.create_index("ix_llm_usage_events_module", "llm_usage_events", ["module"], unique=False)
    op.create_index("ix_llm_usage_events_provider", "llm_usage_events", ["provider"], unique=False)
    op.create_index("ix_llm_usage_events_task_type", "llm_usage_events", ["task_type"], unique=False)
    op.create_index("ix_llm_usage_events_tenant_id", "llm_usage_events", ["tenant_id"], unique=False)
    op.create_index("ix_llm_usage_events_total_tokens", "llm_usage_events", ["total_tokens"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_llm_usage_events_total_tokens", table_name="llm_usage_events")
    op.drop_index("ix_llm_usage_events_tenant_id", table_name="llm_usage_events")
    op.drop_index("ix_llm_usage_events_task_type", table_name="llm_usage_events")
    op.drop_index("ix_llm_usage_events_provider", table_name="llm_usage_events")
    op.drop_index("ix_llm_usage_events_module", table_name="llm_usage_events")
    op.drop_index("ix_llm_usage_events_model", table_name="llm_usage_events")
    op.drop_index("ix_llm_usage_events_feature", table_name="llm_usage_events")
    op.drop_index("ix_llm_usage_events_created_at", table_name="llm_usage_events")
    op.drop_table("llm_usage_events")