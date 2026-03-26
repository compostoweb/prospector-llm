"""019 — Adiciona coluna linkedin_recent_posts_json na tabela leads.

Revision ID: 019
Revises: 018
"""

from alembic import op
import sqlalchemy as sa


revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "leads",
        sa.Column(
            "linkedin_recent_posts_json",
            sa.Text(),
            nullable=True,
            comment="JSON com últimos posts do lead no LinkedIn (cache de enriquecimento)",
        ),
    )


def downgrade() -> None:
    op.drop_column("leads", "linkedin_recent_posts_json")
