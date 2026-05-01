"""093 create content_newsletters table

Revision ID: 093
Revises: 092
Create Date: 2026-05-01 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "093"
down_revision = "092"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "content_newsletters",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "edition_number",
            sa.Integer(),
            nullable=False,
            comment="Numero da edicao por tenant (auto-incremento via service)",
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("subtitle", sa.Text(), nullable=True),
        sa.Column(
            "body_markdown",
            sa.Text(),
            nullable=False,
            server_default="",
            comment="Markdown completo (renderizado a partir das secoes)",
        ),
        sa.Column(
            "body_html",
            sa.Text(),
            nullable=True,
            comment="Cache HTML pre-renderizado para clipboard",
        ),
        sa.Column(
            "sections_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Estrutura das 5 secoes (tema, visao, tutorial, radar, pergunta)",
        ),
        sa.Column("cover_image_url", sa.Text(), nullable=True),
        sa.Column("cover_image_s3_key", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="draft",
            comment="draft | approved | scheduled | published | deleted",
        ),
        sa.Column(
            "scheduled_for",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Lembrete (nao publish automatico - LinkedIn nao tem API)",
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "linkedin_pulse_url",
            sa.Text(),
            nullable=True,
            comment="URL final do Pulse, preenchida no mark-as-published",
        ),
        sa.Column(
            "derived_article_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="FK para content_articles criado no mark-as-published (FK adicionada em 094)",
        ),
        sa.Column(
            "last_reminder_sent_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Idempotencia para reminders diarios",
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("notion_page_id", sa.String(length=100), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
    )

    # Unique edition_number por tenant (apenas registros ativos)
    op.create_index(
        "uq_content_newsletters_tenant_edition",
        "content_newsletters",
        ["tenant_id", "edition_number"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_index(
        "ix_content_newsletters_tenant_status",
        "content_newsletters",
        ["tenant_id", "status", "scheduled_for"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_content_newsletters_tenant_status", table_name="content_newsletters"
    )
    op.drop_index(
        "uq_content_newsletters_tenant_edition", table_name="content_newsletters"
    )
    op.drop_table("content_newsletters")
