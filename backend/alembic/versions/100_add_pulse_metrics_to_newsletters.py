"""100 add pulse metrics to newsletters

Revision ID: 100
Revises: 099
Create Date: 2026-05-02 00:00:00.000000

Adiciona 4 colunas de métricas manuais do LinkedIn Pulse a content_newsletters:
  pulse_views_count, pulse_reactions_count, pulse_comments_count, pulse_reposts_count
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "100"
down_revision = "099"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "content_newsletters",
        sa.Column("pulse_views_count", sa.Integer(), nullable=True),
    )
    op.add_column(
        "content_newsletters",
        sa.Column("pulse_reactions_count", sa.Integer(), nullable=True),
    )
    op.add_column(
        "content_newsletters",
        sa.Column("pulse_comments_count", sa.Integer(), nullable=True),
    )
    op.add_column(
        "content_newsletters",
        sa.Column("pulse_reposts_count", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("content_newsletters", "pulse_reposts_count")
    op.drop_column("content_newsletters", "pulse_comments_count")
    op.drop_column("content_newsletters", "pulse_reactions_count")
    op.drop_column("content_newsletters", "pulse_views_count")
