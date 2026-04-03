"""032 — Altera email_signature de VARCHAR(10000) para TEXT em email_accounts.

Revision ID: 032
Revises: 031
"""

import sqlalchemy as sa
from alembic import op


revision = "032"
down_revision = "031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "email_accounts",
        "email_signature",
        type_=sa.Text(),
        existing_type=sa.String(10000),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "email_accounts",
        "email_signature",
        type_=sa.String(10000),
        existing_type=sa.Text(),
        existing_nullable=True,
    )
