"""038 — Cria tabela anthropic_batch_jobs para rastrear Batch API jobs.

Revision ID: 038
Revises: 037
"""

import sqlalchemy as sa
from alembic import op


revision = "038"
down_revision = "037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "anthropic_batch_jobs",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("anthropic_batch_id", sa.String(100), nullable=False),
        sa.Column("job_type", sa.String(50), nullable=False, server_default="lead_analysis"),
        sa.Column("status", sa.String(30), nullable=False, server_default="in_progress"),
        sa.Column("lead_ids_json", sa.Text(), nullable=False),
        sa.Column("results_url", sa.String(500), nullable=True),
        sa.Column("request_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("succeeded_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expired_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("model", sa.String(100), nullable=False, server_default="claude-haiku-4-5"),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("ix_anthropic_batch_jobs_tenant_id", "anthropic_batch_jobs", ["tenant_id"])
    op.create_index("ix_anthropic_batch_jobs_anthropic_batch_id", "anthropic_batch_jobs", ["anthropic_batch_id"])
    op.create_index("ix_anthropic_batch_jobs_status", "anthropic_batch_jobs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_anthropic_batch_jobs_status", "anthropic_batch_jobs")
    op.drop_index("ix_anthropic_batch_jobs_anthropic_batch_id", "anthropic_batch_jobs")
    op.drop_index("ix_anthropic_batch_jobs_tenant_id", "anthropic_batch_jobs")
    op.drop_table("anthropic_batch_jobs")
