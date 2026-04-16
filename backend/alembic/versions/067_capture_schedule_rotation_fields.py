"""067_capture_schedule_rotation_fields.py

Revision ID: 067
Revises: 066
Create Date: 2026-04-15

Adiciona campos de rotação à tabela capture_schedule_configs:
  - maps_locations: lista de cidades para rotação automática (Maps)
  - maps_combo_index: índice atual no produto cartesiano termos × locais
  - b2b_rotation_index: índice atual na lista de cidades B2B
  - last_run_at: timestamp da última execução
  - last_list_id: FK para a última lead_list criada pela captura
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "067"
down_revision = "066"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "capture_schedule_configs",
        sa.Column("maps_locations", postgresql.ARRAY(sa.Text()), nullable=True),
    )
    op.add_column(
        "capture_schedule_configs",
        sa.Column(
            "maps_combo_index",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "capture_schedule_configs",
        sa.Column(
            "b2b_rotation_index",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "capture_schedule_configs",
        sa.Column(
            "last_run_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "capture_schedule_configs",
        sa.Column(
            "last_list_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("lead_lists.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("capture_schedule_configs", "last_list_id")
    op.drop_column("capture_schedule_configs", "last_run_at")
    op.drop_column("capture_schedule_configs", "b2b_rotation_index")
    op.drop_column("capture_schedule_configs", "maps_combo_index")
    op.drop_column("capture_schedule_configs", "maps_locations")
