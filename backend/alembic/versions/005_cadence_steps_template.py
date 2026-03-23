"""Add steps_template JSONB column to cadences

Revision ID: 005
Revises: 004
Create Date: 2025-01-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cadences",
        sa.Column(
            "steps_template",
            JSONB,
            nullable=True,
            comment="Template de steps customizado (JSON). NULL = template padrão.",
        ),
    )


def downgrade() -> None:
    op.drop_column("cadences", "steps_template")
