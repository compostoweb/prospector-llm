"""Add current_step column to content_engagement_sessions.

Revision ID: 050
Revises: 049
"""

import sqlalchemy as sa

from alembic import op

revision = "050"
down_revision = "049"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "content_engagement_sessions",
        sa.Column(
            "current_step",
            sa.Integer(),
            nullable=True,
            comment="etapa atual do scan: 1-4",
        ),
    )


def downgrade() -> None:
    op.drop_column("content_engagement_sessions", "current_step")
