"""026 — Tabelas de warmup de e-mail.

Revises: 025
Cria: warmup_campaigns, warmup_logs, warmup_seed_pool.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PGUUID


revision = "026"
down_revision = "025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── warmup_campaigns ─────────────────────────────────────────────
    op.create_table(
        "warmup_campaigns",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "email_account_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("email_accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("current_day", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_sent", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_replied", sa.Integer, nullable=False, server_default="0"),
        sa.Column("spam_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("daily_volume_start", sa.Integer, nullable=False, server_default="5"),
        sa.Column("daily_volume_target", sa.Integer, nullable=False, server_default="80"),
        sa.Column("ramp_days", sa.Integer, nullable=False, server_default="30"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_index("ix_warmup_campaigns_tenant_id", "warmup_campaigns", ["tenant_id"])
    op.create_index("ix_warmup_campaigns_email_account_id", "warmup_campaigns", ["email_account_id"])
    op.execute("ALTER TABLE warmup_campaigns ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON warmup_campaigns
        USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid)
    """)

    # ── warmup_logs ───────────────────────────────────────────────────
    op.create_table(
        "warmup_logs",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "campaign_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("warmup_campaigns.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("direction", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="delivered"),
        sa.Column("partner_email", sa.String(255), nullable=False),
        sa.Column("message_id_sent", sa.String(500), nullable=True),
        sa.Column("message_id_reply", sa.String(500), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replied_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_warmup_logs_tenant_id", "warmup_logs", ["tenant_id"])
    op.create_index("ix_warmup_logs_campaign_id", "warmup_logs", ["campaign_id"])
    op.execute("ALTER TABLE warmup_logs ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON warmup_logs
        USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid)
    """)

    # ── warmup_seed_pool ──────────────────────────────────────────────
    op.create_table(
        "warmup_seed_pool",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("display_name", sa.String(200), nullable=True),
        sa.Column("provider", sa.String(50), nullable=False, server_default="smtp"),
        sa.Column("smtp_host", sa.String(255), nullable=True),
        sa.Column("smtp_port", sa.Integer, nullable=True),
        sa.Column("smtp_username", sa.String(255), nullable=True),
        sa.Column("smtp_password", sa.String(1000), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_warmup_seed_pool_email", "warmup_seed_pool", ["email"])


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON warmup_logs")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON warmup_campaigns")
    op.drop_table("warmup_seed_pool")
    op.drop_table("warmup_logs")
    op.drop_table("warmup_campaigns")
