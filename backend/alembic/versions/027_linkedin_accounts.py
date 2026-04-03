"""027 — Tabela linkedin_accounts.

Revision ID: 027
Revises: 026
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PGUUID


revision = "027"
down_revision = "026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "linkedin_accounts",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Identificação
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("linkedin_username", sa.String(200), nullable=True),
        # Tipo de provider: "unipile" | "native"
        sa.Column("provider_type", sa.String(50), nullable=False),
        # Unipile
        sa.Column("unipile_account_id", sa.String(200), nullable=True),
        # Native — cookie li_at criptografado com Fernet
        sa.Column("li_at_cookie", sa.String(2000), nullable=True),
        # Controles
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("last_polled_at", sa.DateTime(timezone=True), nullable=True),
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

    op.create_index(
        "ix_linkedin_accounts_tenant_id",
        "linkedin_accounts",
        ["tenant_id"],
    )

    # Row-Level Security — isolamento por tenant
    op.execute("ALTER TABLE linkedin_accounts ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY tenant_isolation ON linkedin_accounts
        USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON linkedin_accounts;")
    op.drop_index("ix_linkedin_accounts_tenant_id", table_name="linkedin_accounts")
    op.drop_table("linkedin_accounts")
