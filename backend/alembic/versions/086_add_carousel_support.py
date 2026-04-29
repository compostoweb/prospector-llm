"""086 add carousel support

Revision ID: 086
Revises: 085
Create Date: 2026-04-29 12:00:00.000000

Adiciona suporte a carrossel multi-imagem (até 9) no Content Hub:
- content_posts.media_kind (none | image | video | carousel)
- content_gallery_images.position, linkedin_image_urn, carousel_group_id

Posts antigos com image_url ou video_url ganham media_kind derivado
no upgrade. Mantém colunas image_*/video_* legadas.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "086"
down_revision = "085"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── content_posts.media_kind ──────────────────────────────────────
    op.add_column(
        "content_posts",
        sa.Column(
            "media_kind",
            sa.String(length=16),
            nullable=False,
            server_default="none",
            comment="none | image | video | carousel",
        ),
    )

    # Backfill: derivar a partir das colunas legadas
    op.execute(
        sa.text(
            """
            update content_posts set media_kind = case
                when video_url is not null and video_url <> '' then 'video'
                when image_url is not null and image_url <> '' then 'image'
                else 'none'
            end
            """
        )
    )

    # ── content_gallery_images: position, linkedin_image_urn, carousel_group_id
    op.add_column(
        "content_gallery_images",
        sa.Column(
            "position",
            sa.Integer(),
            nullable=True,
            comment="Ordem dentro do carrossel (0-based). NULL = imagem standalone/post single.",
        ),
    )
    op.add_column(
        "content_gallery_images",
        sa.Column(
            "linkedin_image_urn",
            sa.Text(),
            nullable=True,
            comment="urn:li:digitalmediaAsset:XXX após upload no LinkedIn (cache pré-publish).",
        ),
    )
    op.add_column(
        "content_gallery_images",
        sa.Column(
            "carousel_group_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="Agrupador visual (pasta) na galeria para imagens do mesmo carrossel.",
        ),
    )

    op.create_index(
        "ix_content_gallery_images_post_position",
        "content_gallery_images",
        ["linked_post_id", "position"],
        unique=False,
    )
    op.create_index(
        "ix_content_gallery_images_carousel_group",
        "content_gallery_images",
        ["carousel_group_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_content_gallery_images_carousel_group",
        table_name="content_gallery_images",
    )
    op.drop_index(
        "ix_content_gallery_images_post_position",
        table_name="content_gallery_images",
    )
    op.drop_column("content_gallery_images", "carousel_group_id")
    op.drop_column("content_gallery_images", "linkedin_image_urn")
    op.drop_column("content_gallery_images", "position")
    op.drop_column("content_posts", "media_kind")
