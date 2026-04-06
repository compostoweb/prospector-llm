"""
039 – Adiciona campo email_bounce_type à tabela leads.

Revisão: 039
Down revision: 038
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "039"
down_revision = "038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "leads",
        sa.Column(
            "email_bounce_type",
            sa.String(10),
            nullable=True,
            comment="'hard' (permanente) ou 'soft' (temporário)",
        ),
    )


def downgrade() -> None:
    op.drop_column("leads", "email_bounce_type")
