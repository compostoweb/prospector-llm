"""012 — Adiciona coluna tts_speed à tabela cadences.

Permite configurar velocidade da fala TTS por cadência (0.5–2.0).
Default: 1.0 (velocidade normal).

Revision ID: 012
Revises: 011
Create Date: 2026-03-24
"""

from alembic import op
import sqlalchemy as sa

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cadences",
        sa.Column(
            "tts_speed",
            sa.Float(),
            server_default="1.0",
            nullable=False,
            comment="Velocidade da fala TTS (0.5–2.0). 1.0 = normal.",
        ),
    )


def downgrade() -> None:
    op.drop_column("cadences", "tts_speed")
