"""101 add notion newsletter database id to content settings

Revision ID: 101
Revises: 100
Create Date: 2026-05-02 00:00:00.000000

Adiciona notion_newsletter_database_id a content_settings para suportar
importação de newsletters a partir de um banco de dados Notion separado.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "101"
down_revision = "100"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "content_settings",
        sa.Column(
            "notion_newsletter_database_id",
            sa.String(100),
            nullable=True,
            comment="ID do banco de dados Notion com as newsletters (UUID da URL)",
        ),
    )


def downgrade() -> None:
    op.drop_column("content_settings", "notion_newsletter_database_id")
