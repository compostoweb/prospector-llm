"""077 add interaction reply correlation fields

Revision ID: 077
Revises: 076
Create Date: 2026-04-19 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "077"
down_revision = "076"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "interactions",
        sa.Column("cadence_step_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "interactions",
        sa.Column("email_message_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "interactions",
        sa.Column("provider_thread_id", sa.String(length=255), nullable=True),
    )
    op.create_index(
        "ix_interactions_cadence_step_id",
        "interactions",
        ["cadence_step_id"],
        unique=False,
    )
    op.create_index(
        "ix_interactions_email_message_id",
        "interactions",
        ["email_message_id"],
        unique=False,
    )
    op.create_index(
        "ix_interactions_provider_thread_id",
        "interactions",
        ["provider_thread_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_interactions_cadence_step_id",
        "interactions",
        "cadence_steps",
        ["cadence_step_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_interactions_cadence_step_id", "interactions", type_="foreignkey")
    op.drop_index("ix_interactions_provider_thread_id", table_name="interactions")
    op.drop_index("ix_interactions_email_message_id", table_name="interactions")
    op.drop_index("ix_interactions_cadence_step_id", table_name="interactions")
    op.drop_column("interactions", "provider_thread_id")
    op.drop_column("interactions", "email_message_id")
    op.drop_column("interactions", "cadence_step_id")