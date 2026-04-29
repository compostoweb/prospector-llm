"""add linkedin crosscheck fields to leads

Revision ID: 084
Revises: 083
Create Date: 2026-04-29 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "084"
down_revision = "083"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "leads", sa.Column("linkedin_current_company", sa.String(length=300), nullable=True)
    )
    op.add_column(
        "leads", sa.Column("linkedin_checked_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("leads", sa.Column("linkedin_mismatch", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("leads", "linkedin_mismatch")
    op.drop_column("leads", "linkedin_checked_at")
    op.drop_column("leads", "linkedin_current_company")
