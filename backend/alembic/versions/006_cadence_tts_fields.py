"""Add tts_provider and tts_voice_id columns to cadences

Revision ID: 006
Revises: 005
Create Date: 2025-01-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cadences",
        sa.Column(
            "tts_provider",
            sa.String(50),
            nullable=True,
            comment="Provedor TTS: speechify | voicebox. NULL = usa VOICE_PROVIDER global.",
        ),
    )
    op.add_column(
        "cadences",
        sa.Column(
            "tts_voice_id",
            sa.String(200),
            nullable=True,
            comment="ID da voz/profile TTS. NULL = usa default do provider.",
        ),
    )


def downgrade() -> None:
    op.drop_column("cadences", "tts_voice_id")
    op.drop_column("cadences", "tts_provider")
