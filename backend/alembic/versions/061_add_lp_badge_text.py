"""061 — add badge_text to content_landing_pages

Revision ID: 061
Revises: 060
Create Date: 2025-01-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "061"
down_revision = "060"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "content_landing_pages",
        sa.Column("badge_text", sa.String(500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("content_landing_pages", "badge_text")
