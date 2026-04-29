"""085 add pipedrive sync fields to interactions

Revision ID: 085
Revises: 084
Create Date: 2026-04-29 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "085"
down_revision = "084"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "interactions", sa.Column("pipedrive_sync_status", sa.String(length=30), nullable=True)
    )
    op.add_column("interactions", sa.Column("pipedrive_person_id", sa.Integer(), nullable=True))
    op.add_column("interactions", sa.Column("pipedrive_deal_id", sa.Integer(), nullable=True))
    op.add_column(
        "interactions", sa.Column("pipedrive_synced_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("interactions", sa.Column("pipedrive_sync_error", sa.Text(), nullable=True))
    op.create_index(
        op.f("ix_interactions_pipedrive_sync_status"),
        "interactions",
        ["pipedrive_sync_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_interactions_pipedrive_deal_id"),
        "interactions",
        ["pipedrive_deal_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_interactions_pipedrive_deal_id"), table_name="interactions")
    op.drop_index(op.f("ix_interactions_pipedrive_sync_status"), table_name="interactions")
    op.drop_column("interactions", "pipedrive_sync_error")
    op.drop_column("interactions", "pipedrive_synced_at")
    op.drop_column("interactions", "pipedrive_deal_id")
    op.drop_column("interactions", "pipedrive_person_id")
    op.drop_column("interactions", "pipedrive_sync_status")
