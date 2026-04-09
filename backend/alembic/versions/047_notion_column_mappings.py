"""047_notion_column_mappings.

Adiciona coluna notion_column_mappings em content_settings para armazenar
o mapeamento personalizado entre colunas do banco de dados Notion e campos
internos do ContentPost (JSON serializado).

Revision ID: 047
Revises: 046
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "047"
down_revision = "046"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "content_settings",
        sa.Column("notion_column_mappings", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("content_settings", "notion_column_mappings")
