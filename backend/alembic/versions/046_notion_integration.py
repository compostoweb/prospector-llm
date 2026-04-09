"""046_notion_integration.

Adiciona suporte à integração com Notion:

- content_settings: notion_api_key (TEXT) e notion_database_id (VARCHAR 100)
  para armazenar as credenciais Notion por tenant.

- content_posts: notion_page_id (VARCHAR 100) com índice para rastrear a
  origem do post e evitar reimportação duplicada.

Revision ID: 046
Revises: 045
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "046"
down_revision = "045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # content_settings — credenciais Notion por tenant
    op.add_column(
        "content_settings",
        sa.Column("notion_api_key", sa.Text(), nullable=True),
    )
    op.add_column(
        "content_settings",
        sa.Column("notion_database_id", sa.String(length=100), nullable=True),
    )

    # content_posts — ID da page original no Notion (controle de duplicatas)
    op.add_column(
        "content_posts",
        sa.Column("notion_page_id", sa.String(length=100), nullable=True),
    )
    op.create_index(
        "ix_content_posts_notion_page_id",
        "content_posts",
        ["notion_page_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_content_posts_notion_page_id", table_name="content_posts")
    op.drop_column("content_posts", "notion_page_id")
    op.drop_column("content_settings", "notion_database_id")
    op.drop_column("content_settings", "notion_api_key")
