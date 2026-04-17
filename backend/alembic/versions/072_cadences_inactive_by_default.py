"""072_cadences_inactive_by_default.py

Revision ID: 072
Revises: 071
Create Date: 2026-04-16

Novas cadências passam a nascer pausadas por padrão.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "072"
down_revision: str = "071"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "cadences",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "cadences",
        "is_active",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )
