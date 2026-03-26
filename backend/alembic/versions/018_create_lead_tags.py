"""018 — Criar tabela lead_tags para tags de leads.

Revision ID: 018
Revises: 017
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID


revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lead_tags",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "lead_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("leads.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("color", sa.String(7), nullable=False, server_default="#6366f1"),
        sa.UniqueConstraint("lead_id", "name", name="uq_lead_tags_lead_name"),
    )

    # RLS policy
    op.execute("""
        ALTER TABLE lead_tags ENABLE ROW LEVEL SECURITY;
    """)
    op.execute("""
        CREATE POLICY lead_tags_tenant_isolation ON lead_tags
        USING (tenant_id::text = current_setting('app.current_tenant_id', true));
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS lead_tags_tenant_isolation ON lead_tags;")
    op.drop_table("lead_tags")
