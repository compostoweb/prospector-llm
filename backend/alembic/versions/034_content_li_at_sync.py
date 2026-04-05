"""034 — Adiciona li_at_cookie e last_voyager_sync_at em content_linkedin_accounts.

Revision ID: 034
Revises: 033
"""

import sqlalchemy as sa

from alembic import op

revision = "034"
down_revision = "033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "content_linkedin_accounts",
        sa.Column(
            "li_at_cookie",
            sa.String(2000),
            nullable=True,
            comment="Cookie li_at criptografado com Fernet para Voyager API (analytics pessoal)",
        ),
    )
    op.add_column(
        "content_linkedin_accounts",
        sa.Column(
            "last_voyager_sync_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Última sincronização de métricas via Voyager API",
        ),
    )


def downgrade() -> None:
    op.drop_column("content_linkedin_accounts", "last_voyager_sync_at")
    op.drop_column("content_linkedin_accounts", "li_at_cookie")
