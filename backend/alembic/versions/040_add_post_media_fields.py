"""
040 – Adiciona campos de mídia (imagem e vídeo) à tabela content_posts.

Revisão: 040
Down revision: 039
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "040"
down_revision = "039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("content_posts", sa.Column("image_url", sa.Text(), nullable=True))
    op.add_column("content_posts", sa.Column("image_s3_key", sa.Text(), nullable=True))
    op.add_column(
        "content_posts",
        sa.Column(
            "image_style", sa.String(20), nullable=True, comment="clean | with_text | infographic"
        ),
    )
    op.add_column("content_posts", sa.Column("image_prompt", sa.Text(), nullable=True))
    op.add_column(
        "content_posts",
        sa.Column("image_aspect_ratio", sa.String(10), nullable=True, comment="4:5 | 1:1 | 16:9"),
    )
    op.add_column("content_posts", sa.Column("linkedin_image_urn", sa.Text(), nullable=True))
    op.add_column("content_posts", sa.Column("video_url", sa.Text(), nullable=True))
    op.add_column("content_posts", sa.Column("video_s3_key", sa.Text(), nullable=True))
    op.add_column("content_posts", sa.Column("linkedin_video_urn", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("content_posts", "linkedin_video_urn")
    op.drop_column("content_posts", "video_s3_key")
    op.drop_column("content_posts", "video_url")
    op.drop_column("content_posts", "linkedin_image_urn")
    op.drop_column("content_posts", "image_aspect_ratio")
    op.drop_column("content_posts", "image_prompt")
    op.drop_column("content_posts", "image_style")
    op.drop_column("content_posts", "image_s3_key")
    op.drop_column("content_posts", "image_url")
