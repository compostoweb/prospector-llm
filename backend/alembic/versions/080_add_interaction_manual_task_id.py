"""080 add interaction manual task correlation

Revision ID: 080
Revises: 079
Create Date: 2026-04-23 00:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "080"
down_revision = "079"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "interactions",
        sa.Column("manual_task_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "ix_interactions_manual_task_id",
        "interactions",
        ["manual_task_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_interactions_manual_task_id",
        "interactions",
        "manual_tasks",
        ["manual_task_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_interactions_manual_task_id", "interactions", type_="foreignkey")
    op.drop_index("ix_interactions_manual_task_id", table_name="interactions")
    op.drop_column("interactions", "manual_task_id")
