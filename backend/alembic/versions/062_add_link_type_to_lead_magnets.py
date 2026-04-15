"""062 — add 'link' to content_lead_magnets type check constraint

Revision ID: 062
Revises: 061
Create Date: 2026-04-15 00:00:00.000000
"""

from alembic import op

revision = "062"
down_revision = "061"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_content_lead_magnets_type", "content_lead_magnets")
    op.create_check_constraint(
        "ck_content_lead_magnets_type",
        "content_lead_magnets",
        "type IN ('pdf', 'calculator', 'email_sequence', 'link')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_content_lead_magnets_type", "content_lead_magnets")
    op.create_check_constraint(
        "ck_content_lead_magnets_type",
        "content_lead_magnets",
        "type IN ('pdf', 'calculator', 'email_sequence')",
    )
