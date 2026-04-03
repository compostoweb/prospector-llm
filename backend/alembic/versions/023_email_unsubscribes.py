"""023 — Tabela email_unsubscribes.

Revision ID: 023
Revises: 022
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PGUUID


revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "email_unsubscribes",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", PGUUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column(
            "unsubscribed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_email_unsubscribes_tenant_email", "email_unsubscribes", ["tenant_id", "email"])

    # RLS
    op.execute("ALTER TABLE email_unsubscribes ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON email_unsubscribes
        USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid)
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON email_unsubscribes")
    op.drop_table("email_unsubscribes")
