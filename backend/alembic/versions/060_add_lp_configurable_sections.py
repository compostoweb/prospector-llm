"""060 — add LP configurable sections: publisher_name, features, expected_result

Revision ID: 060
Revises: 059
Create Date: 2025-01-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "060"
down_revision = "059"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "content_landing_pages",
        sa.Column("publisher_name", sa.String(255), nullable=True),
    )
    op.add_column(
        "content_landing_pages",
        sa.Column("features", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "content_landing_pages",
        sa.Column("expected_result", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("content_landing_pages", "expected_result")
    op.drop_column("content_landing_pages", "features")
    op.drop_column("content_landing_pages", "publisher_name")
