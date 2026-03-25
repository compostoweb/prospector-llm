"""011 — Cria tabela audio_files e adiciona audio_file_id a cadence_steps.

Permite upload de áudios pré-gravados no S3/MinIO
e uso em steps de cadência como voice notes personalizados.

Revision ID: 011
Revises: 010
Create Date: 2026-03-24
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Tabela audio_files ────────────────────────────────────────────
    op.create_table(
        "audio_files",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("s3_key", sa.String(500), nullable=False, unique=True),
        sa.Column("url", sa.String(1000), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False, server_default="audio/mpeg"),
        sa.Column("size_bytes", sa.BigInteger, nullable=False),
        sa.Column("duration_seconds", sa.Float, nullable=True),
        sa.Column("language", sa.String(10), nullable=False, server_default="pt-BR"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ── RLS policy ────────────────────────────────────────────────────
    op.execute("""
        ALTER TABLE audio_files ENABLE ROW LEVEL SECURITY;
    """)
    op.execute("""
        CREATE POLICY tenant_isolation ON audio_files
        USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
    """)

    # ── FK audio_file_id em cadence_steps ─────────────────────────────
    op.add_column(
        "cadence_steps",
        sa.Column(
            "audio_file_id",
            UUID(as_uuid=True),
            sa.ForeignKey("audio_files.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_cadence_steps_audio_file_id", "cadence_steps", ["audio_file_id"])


def downgrade() -> None:
    op.drop_index("ix_cadence_steps_audio_file_id", table_name="cadence_steps")
    op.drop_column("cadence_steps", "audio_file_id")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON audio_files;")
    op.drop_table("audio_files")
