"""009 — Adicionar 'manual_task' ao enum channel.

Revision ID: 009
Revises: 008
Create Date: 2025-01-01
"""

from alembic import op

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE channel ADD VALUE IF NOT EXISTS 'manual_task'")


def downgrade() -> None:
    # PostgreSQL não permite remover valores de enum diretamente.
    # Em downgrade, o valor ficará no tipo mas não será usado.
    pass
