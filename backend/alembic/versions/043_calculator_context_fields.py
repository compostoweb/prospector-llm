"""043_add_calculator_context_fields.

Revision ID: 043
Revises: 042
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "043"
down_revision = "042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "content_calculator_results",
        sa.Column("company_segment", sa.String(length=30), nullable=True),
    )
    op.add_column(
        "content_calculator_results",
        sa.Column("company_size", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "content_calculator_results",
        sa.Column("process_area_span", sa.String(length=10), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("content_calculator_results", "process_area_span")
    op.drop_column("content_calculator_results", "company_size")
    op.drop_column("content_calculator_results", "company_segment")
