"""064 — add email_headline to content_lead_magnets

Revision ID: 064
Revises: 063
Create Date: 2026-04-15 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "064"
down_revision = "063"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "content_lead_magnets",
        sa.Column(
            "email_headline",
            sa.String(255),
            nullable=True,
            comment="Título/headline customizado do email de entrega",
        ),
    )


def downgrade() -> None:
    op.drop_column("content_lead_magnets", "email_headline")
