"""078 add interaction reply audit fields

Revision ID: 078
Revises: 077
Create Date: 2026-04-19 00:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "078"
down_revision = "077"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "interactions",
        sa.Column("reply_match_status", sa.String(length=30), nullable=True),
    )
    op.add_column(
        "interactions",
        sa.Column("reply_match_source", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "interactions",
        sa.Column("reply_match_sent_cadence_count", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_interactions_reply_match_status",
        "interactions",
        ["reply_match_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_interactions_reply_match_status", table_name="interactions")
    op.drop_column("interactions", "reply_match_sent_cadence_count")
    op.drop_column("interactions", "reply_match_source")
    op.drop_column("interactions", "reply_match_status")