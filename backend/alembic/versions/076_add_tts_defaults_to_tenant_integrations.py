"""076_add_tts_defaults_to_tenant_integrations

Adiciona campos de TTS padrão ao TenantIntegration:
  - tts_default_provider: provider TTS padrão por tenant (nullable)
  - tts_default_voice_ids: JSON map provider → voice_id

Revision ID: 076
Revises: 075
Create Date: 2026-04-18 00:00:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "076"
down_revision = "075"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenant_integrations",
        sa.Column(
            "tts_default_provider",
            sa.String(50),
            nullable=True,
        ),
    )
    op.add_column(
        "tenant_integrations",
        sa.Column(
            "tts_default_voice_ids",
            sa.JSON(),
            nullable=False,
            server_default="{}",
        ),
    )


def downgrade() -> None:
    op.drop_column("tenant_integrations", "tts_default_voice_ids")
    op.drop_column("tenant_integrations", "tts_default_provider")
