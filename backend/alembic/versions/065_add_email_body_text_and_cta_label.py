"""065 — add email_body_text and email_cta_label to content_lead_magnets

Revision ID: 065
Revises: 064
Create Date: 2026-04-15 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "065"
down_revision = "064"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "content_lead_magnets",
        sa.Column(
            "email_body_text",
            sa.Text(),
            nullable=True,
            comment="Texto do corpo do email de entrega (após '{nome},')",
        ),
    )
    op.add_column(
        "content_lead_magnets",
        sa.Column(
            "email_cta_label",
            sa.String(100),
            nullable=True,
            comment="Texto do botão CTA customizado no email de entrega",
        ),
    )


def downgrade() -> None:
    op.drop_column("content_lead_magnets", "email_cta_label")
    op.drop_column("content_lead_magnets", "email_body_text")
