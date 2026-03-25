"""013 — Adiciona coluna tts_pitch à tabela cadences.

Permite configurar entonação/pitch da voz TTS por cadência (-50 a +50%).
Default: 0 (sem alteração de pitch).

Revision ID: 013
Revises: 012
Create Date: 2026-03-24
"""

from alembic import op
import sqlalchemy as sa

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cadences",
        sa.Column(
            "tts_pitch",
            sa.Float(),
            server_default="0",
            nullable=False,
            comment="Entonação/pitch TTS (-50 a +50%). 0 = normal.",
        ),
    )


def downgrade() -> None:
    op.drop_column("cadences", "tts_pitch")
