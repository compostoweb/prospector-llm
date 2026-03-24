"""010 — Adiciona lead_list_id à tabela cadences.

Permite vincular uma lista de leads a uma cadência.

Revision ID: 010
Revises: 009
Create Date: 2026-03-23
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cadences",
        sa.Column(
            "lead_list_id",
            UUID(as_uuid=True),
            sa.ForeignKey("lead_lists.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_cadences_lead_list_id", "cadences", ["lead_list_id"])


def downgrade() -> None:
    op.drop_index("ix_cadences_lead_list_id", table_name="cadences")
    op.drop_column("cadences", "lead_list_id")
