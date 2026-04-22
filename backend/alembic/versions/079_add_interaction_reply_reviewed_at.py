"""079 add interaction reply reviewed timestamp

Revision ID: 079
Revises: 078
Create Date: 2026-04-22 11:00:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "079"
down_revision = "078"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "interactions",
        sa.Column("reply_reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_interactions_reply_reviewed_at",
        "interactions",
        ["reply_reviewed_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_interactions_reply_reviewed_at", table_name="interactions")
    op.drop_column("interactions", "reply_reviewed_at")
