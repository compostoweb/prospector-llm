"""063 — add email_subject to content_lead_magnets

Revision ID: 063
Revises: 062
Create Date: 2026-04-15 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "063"
down_revision = "062"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "content_lead_magnets",
        sa.Column(
            "email_subject",
            sa.String(255),
            nullable=True,
            comment="Assunto customizado do email de entrega",
        ),
    )


def downgrade() -> None:
    op.drop_column("content_lead_magnets", "email_subject")
