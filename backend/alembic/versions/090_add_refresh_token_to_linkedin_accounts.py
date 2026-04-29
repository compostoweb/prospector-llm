"""090 add refresh_token_expires_at to content_linkedin_accounts

Revision ID: 090
Revises: 089
Create Date: 2026-04-30 00:02:00.000000

Note: refresh_token e token_expires_at ja existem desde 031_content_hub.
Esta migration apenas adiciona refresh_token_expires_at separado.
token_expires_at continua sendo usado para o access_token.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "090"
down_revision = "089"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "content_linkedin_accounts",
        sa.Column("refresh_token_expires_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("content_linkedin_accounts", "refresh_token_expires_at")
