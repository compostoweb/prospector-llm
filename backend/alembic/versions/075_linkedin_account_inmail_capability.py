"""075_add_linkedin_account_inmail_capability

Revision ID: 075
Revises: 074
Create Date: 2026-04-18 00:15:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "075"
down_revision = "074"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "linkedin_accounts",
        sa.Column(
            "supports_inmail",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )


def downgrade() -> None:
    op.drop_column("linkedin_accounts", "supports_inmail")
