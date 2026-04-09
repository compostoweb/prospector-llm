"""045_add_image_filename_size.

Adiciona image_filename e image_size_bytes à tabela content_posts
para suportar upload manual de imagem (complementando geração por IA).

Revision ID: 045
Revises: 044
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "045"
down_revision = "044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "content_posts",
        sa.Column("image_filename", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "content_posts",
        sa.Column("image_size_bytes", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("content_posts", "image_size_bytes")
    op.drop_column("content_posts", "image_filename")
