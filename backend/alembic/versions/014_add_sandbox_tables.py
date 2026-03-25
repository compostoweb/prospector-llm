"""014 — Cria tabelas sandbox_runs e sandbox_steps.

Sistema de sandbox para testar cadências antes de ativá-las.
Permite preview de mensagens IA, simulação de replies, rate limits e Pipedrive dry-run.

Revision ID: 014
Revises: 013
Create Date: 2025-07-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -- Enums ----------------------------------------------------------
    sandbox_run_status = postgresql.ENUM(
        "running", "completed", "approved", "rejected",
        name="sandbox_run_status",
        create_type=False,
    )
    sandbox_step_status = postgresql.ENUM(
        "pending", "generating", "generated", "approved", "rejected",
        name="sandbox_step_status",
        create_type=False,
    )
    sandbox_lead_source = postgresql.ENUM(
        "real", "sample", "fictitious",
        name="sandbox_lead_source",
        create_type=False,
    )

    # Criar os tipos enum no banco
    sandbox_run_status.create(op.get_bind(), checkfirst=True)
    sandbox_step_status.create(op.get_bind(), checkfirst=True)
    sandbox_lead_source.create(op.get_bind(), checkfirst=True)

    # -- sandbox_runs ---------------------------------------------------
    op.create_table(
        "sandbox_runs",
        sa.Column("id", sa.UUID(), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.UUID(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("cadence_id", sa.UUID(), sa.ForeignKey("cadences.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sandbox_run_status, nullable=False, server_default="running"),
        sa.Column("lead_source", sandbox_lead_source, nullable=False),
        sa.Column("pipedrive_dry_run", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sandbox_runs_tenant_id", "sandbox_runs", ["tenant_id"])
    op.create_index("ix_sandbox_runs_cadence_id", "sandbox_runs", ["cadence_id"])

    # -- sandbox_steps --------------------------------------------------
    op.create_table(
        "sandbox_steps",
        sa.Column("id", sa.UUID(), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.UUID(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("sandbox_run_id", sa.UUID(), sa.ForeignKey("sandbox_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lead_id", sa.UUID(), sa.ForeignKey("leads.id", ondelete="SET NULL"), nullable=True),
        sa.Column("fictitious_lead_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        # Canal e posição
        sa.Column("channel", sa.Enum("linkedin_connect", "linkedin_dm", "email", "manual_task", name="cadence_step_channel", create_type=False), nullable=False),
        sa.Column("step_number", sa.Integer(), nullable=False),
        sa.Column("day_offset", sa.Integer(), nullable=False),
        sa.Column("use_voice", sa.Boolean(), nullable=False, server_default="false"),
        # Timeline preview
        sa.Column("scheduled_at_preview", sa.DateTime(timezone=True), nullable=False),
        # Mensagem gerada pela IA
        sa.Column("message_content", sa.Text(), nullable=True),
        sa.Column("audio_preview_url", sa.String(500), nullable=True),
        sa.Column("email_subject", sa.String(300), nullable=True),
        # Status
        sa.Column("status", sandbox_step_status, nullable=False, server_default="pending"),
        # Info LLM
        sa.Column("llm_provider", sa.String(50), nullable=True),
        sa.Column("llm_model", sa.String(100), nullable=True),
        sa.Column("tokens_in", sa.Integer(), nullable=True),
        sa.Column("tokens_out", sa.Integer(), nullable=True),
        # Simulação de reply
        sa.Column("simulated_reply", sa.Text(), nullable=True),
        sa.Column("simulated_intent", sa.Enum("interest", "objection", "not_interested", "neutral", "out_of_office", name="interaction_intent", create_type=False), nullable=True),
        sa.Column("simulated_confidence", sa.Float(), nullable=True),
        sa.Column("simulated_reply_summary", sa.String(500), nullable=True),
        # Rate limit simulation
        sa.Column("is_rate_limited", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("rate_limit_reason", sa.String(300), nullable=True),
        sa.Column("adjusted_scheduled_at", sa.DateTime(timezone=True), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sandbox_steps_tenant_id", "sandbox_steps", ["tenant_id"])
    op.create_index("ix_sandbox_steps_sandbox_run_id", "sandbox_steps", ["sandbox_run_id"])
    op.create_index("ix_sandbox_steps_lead_id", "sandbox_steps", ["lead_id"])

    # -- RLS policies ---------------------------------------------------
    op.execute("""
        ALTER TABLE sandbox_runs ENABLE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation_sandbox_runs ON sandbox_runs
            USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
    """)
    op.execute("""
        ALTER TABLE sandbox_steps ENABLE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation_sandbox_steps ON sandbox_steps
            USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
    """)


def downgrade() -> None:
    # RLS
    op.execute("DROP POLICY IF EXISTS tenant_isolation_sandbox_steps ON sandbox_steps;")
    op.execute("ALTER TABLE sandbox_steps DISABLE ROW LEVEL SECURITY;")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_sandbox_runs ON sandbox_runs;")
    op.execute("ALTER TABLE sandbox_runs DISABLE ROW LEVEL SECURITY;")

    # Tables
    op.drop_table("sandbox_steps")
    op.drop_table("sandbox_runs")

    # Enums
    op.execute("DROP TYPE IF EXISTS sandbox_step_status;")
    op.execute("DROP TYPE IF EXISTS sandbox_run_status;")
    op.execute("DROP TYPE IF EXISTS sandbox_lead_source;")
