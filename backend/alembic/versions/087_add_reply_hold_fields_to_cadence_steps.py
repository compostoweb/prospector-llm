"""087 add reply hold fields to cadence steps

Revision ID: 087
Revises: 086
Create Date: 2026-04-29 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "087"
down_revision = "086"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cadence_steps",
        sa.Column("reply_hold_interaction_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column("cadence_steps", sa.Column("reply_hold_reason", sa.String(length=80), nullable=True))
    op.add_column(
        "cadence_steps", sa.Column("reply_hold_previous_status", sa.String(length=30), nullable=True)
    )
    op.add_column(
        "cadence_steps", sa.Column("reply_hold_created_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index(
        op.f("ix_cadence_steps_reply_hold_interaction_id"),
        "cadence_steps",
        ["reply_hold_interaction_id"],
        unique=False,
    )
    op.create_foreign_key(
        op.f("fk_cadence_steps_reply_hold_interaction_id_interactions"),
        "cadence_steps",
        "interactions",
        ["reply_hold_interaction_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_cadence_steps_reply_hold_interaction_id_interactions"),
        "cadence_steps",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_cadence_steps_reply_hold_interaction_id"), table_name="cadence_steps")
    op.drop_column("cadence_steps", "reply_hold_created_at")
    op.drop_column("cadence_steps", "reply_hold_previous_status")
    op.drop_column("cadence_steps", "reply_hold_reason")
    op.drop_column("cadence_steps", "reply_hold_interaction_id")