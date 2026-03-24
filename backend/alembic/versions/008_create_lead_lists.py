"""008 — Criar tabelas lead_lists e lead_list_members.

Revision ID: 008
Revises: 007
Create Date: 2025-01-01
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lead_lists",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "lead_list_members",
        sa.Column(
            "lead_list_id",
            UUID(as_uuid=True),
            sa.ForeignKey("lead_lists.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "lead_id",
            UUID(as_uuid=True),
            sa.ForeignKey("leads.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )


def downgrade() -> None:
    op.drop_table("lead_list_members")
    op.drop_table("lead_lists")
