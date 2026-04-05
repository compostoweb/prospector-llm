"""035 — Adiciona composition_context em sandbox_steps.

Revision ID: 035
Revises: 034
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "035"
down_revision = "034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sandbox_steps",
        sa.Column(
            "composition_context",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Metadados de observabilidade usados na composição do step",
        ),
    )


def downgrade() -> None:
    op.drop_column("sandbox_steps", "composition_context")