"""Add standalone gallery images table.

Revision ID: 081
Revises: 080
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "081"
down_revision = "080"
branch_labels = None
depends_on = None


LEGACY_GENERATED_BODIES = (
    "Imagem gerada por IA — aguardando vínculo com post.",
    "Imagem gerada por IA - aguardando vínculo com post.",
    "Imagem gerada por IA — aguardando vinculo com post.",
    "Imagem gerada por IA - aguardando vinculo com post.",
)

LEGACY_UPLOADED_BODIES = (
    "Imagem enviada via upload — aguardando vínculo com post.",
    "Imagem enviada via upload - aguardando vínculo com post.",
    "Imagem enviada via upload — aguardando vinculo com post.",
    "Imagem enviada via upload - aguardando vinculo com post.",
)


def _legacy_gallery_posts_predicate() -> str:
    generated_bodies = ", ".join(f"'{body}'" for body in LEGACY_GENERATED_BODIES)
    uploaded_bodies = ", ".join(f"'{body}'" for body in LEGACY_UPLOADED_BODIES)
    return f"""
        status = 'draft'
        and image_url is not null
        and image_url <> ''
        and publish_date is null
        and linkedin_post_urn is null
        and linkedin_scheduled_id is null
        and (
            (
                title like '[Imagem Gerada] %'
                and body in ({generated_bodies})
            )
            or (
                title like '[Upload] %'
                and body in ({uploaded_bodies})
            )
        )
    """


def _migrate_legacy_gallery_posts() -> None:
    legacy_posts_predicate = _legacy_gallery_posts_predicate()

    op.execute(
        sa.text(
            f"""
            insert into content_gallery_images (
                id,
                title,
                source,
                linked_post_id,
                image_url,
                image_s3_key,
                image_style,
                image_prompt,
                image_aspect_ratio,
                image_filename,
                image_size_bytes,
                tenant_id,
                created_at,
                updated_at
            )
            select
                id,
                case
                    when title like '[Upload] %' then coalesce(nullif(image_filename, ''), regexp_replace(title, '^\\[Upload\\]\\s*', ''))
                    else coalesce(
                        nullif(regexp_replace(title, '^\\[Imagem Gerada\\]\\s*', ''), ''),
                        nullif(image_prompt, ''),
                        'Imagem gerada'
                    )
                end as title,
                case
                    when title like '[Upload] %' or image_filename is not null then 'uploaded'
                    else 'generated'
                end as source,
                null::uuid as linked_post_id,
                image_url,
                image_s3_key,
                image_style,
                image_prompt,
                image_aspect_ratio,
                image_filename,
                image_size_bytes,
                tenant_id,
                created_at,
                updated_at
            from content_posts
            where {legacy_posts_predicate}
            """
        )
    )

    op.execute(
        sa.text(
            f"""
            delete from content_posts
            where {legacy_posts_predicate}
            """
        )
    )


def _ensure_gallery_images_table() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())
    if "content_gallery_images" in table_names:
        return

    op.create_table(
        "content_gallery_images",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column(
            "source",
            sa.String(length=20),
            nullable=False,
            server_default="generated",
            comment="generated | uploaded",
        ),
        sa.Column("linked_post_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=False),
        sa.Column("image_s3_key", sa.Text(), nullable=True),
        sa.Column(
            "image_style",
            sa.String(length=20),
            nullable=True,
            comment="clean | with_text | infographic",
        ),
        sa.Column("image_prompt", sa.Text(), nullable=True),
        sa.Column(
            "image_aspect_ratio",
            sa.String(length=10),
            nullable=True,
            comment="4:5 | 1:1 | 16:9",
        ),
        sa.Column("image_filename", sa.String(length=500), nullable=True),
        sa.Column("image_size_bytes", sa.Integer(), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["linked_post_id"], ["content_posts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def _ensure_gallery_images_indexes() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    index_names = {index["name"] for index in inspector.get_indexes("content_gallery_images")}

    linked_post_index = op.f("ix_content_gallery_images_linked_post_id")
    if linked_post_index not in index_names:
        op.create_index(
            linked_post_index,
            "content_gallery_images",
            ["linked_post_id"],
            unique=False,
        )

    tenant_index = op.f("ix_content_gallery_images_tenant_id")
    if tenant_index not in index_names:
        op.create_index(
            tenant_index,
            "content_gallery_images",
            ["tenant_id"],
            unique=False,
        )


def upgrade() -> None:
    _ensure_gallery_images_table()
    _ensure_gallery_images_indexes()
    _migrate_legacy_gallery_posts()


def downgrade() -> None:
    op.drop_index(op.f("ix_content_gallery_images_tenant_id"), table_name="content_gallery_images")
    op.drop_index(
        op.f("ix_content_gallery_images_linked_post_id"),
        table_name="content_gallery_images",
    )
    op.drop_table("content_gallery_images")
