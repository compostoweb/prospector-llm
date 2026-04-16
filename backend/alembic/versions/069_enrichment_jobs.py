"""069_enrichment_jobs.py

Revision ID: 069
Revises: 068
Create Date: 2026-04-15

Cria a tabela enrichment_jobs para filas de enriquecimento em lote de perfis LinkedIn.
Ao invés de enviar 200 URLs de uma vez para o Apify, o sistema divide em batches
e processa automaticamente a cada hora até zerar a fila.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "069"
down_revision = "068"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "enrichment_jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "target_list_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("lead_lists.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "linkedin_urls",
            postgresql.ARRAY(sa.Text),
            nullable=False,
        ),
        sa.Column("batch_size", sa.Integer, nullable=False, server_default="50"),
        sa.Column("processed_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="pending",
            index=True,
        ),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            onupdate=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("enrichment_jobs")
