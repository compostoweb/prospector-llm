"""024 — Tabela email_accounts.

Revision ID: 024
Revises: 023
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PGUUID


revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "email_accounts",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Identificação
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("email_address", sa.String(255), nullable=False),
        sa.Column("from_name", sa.String(200), nullable=True),
        # Tipo de provider
        sa.Column("provider_type", sa.String(50), nullable=False),
        # Unipile
        sa.Column("unipile_account_id", sa.String(200), nullable=True),
        # Google OAuth (criptografado)
        sa.Column("google_refresh_token", sa.String(1000), nullable=True),
        # SMTP
        sa.Column("smtp_host", sa.String(255), nullable=True),
        sa.Column("smtp_port", sa.Integer, nullable=True, server_default="587"),
        sa.Column("smtp_username", sa.String(255), nullable=True),
        sa.Column("smtp_password", sa.String(1000), nullable=True),
        sa.Column("smtp_use_tls", sa.Boolean, nullable=False, server_default="true"),
        # Limites e controles
        sa.Column("daily_send_limit", sa.Integer, nullable=False, server_default="50"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("is_warmup_enabled", sa.Boolean, nullable=False, server_default="false"),
        # Timestamps
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

    # Índices
    op.create_index("ix_email_accounts_tenant_id", "email_accounts", ["tenant_id"])
    op.create_index("ix_email_accounts_email_address", "email_accounts", ["email_address"])

    # RLS
    op.execute("ALTER TABLE email_accounts ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON email_accounts
        USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid)
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON email_accounts")
    op.drop_table("email_accounts")
