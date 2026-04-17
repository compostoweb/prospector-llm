"""073_capture_execution_logs.py

Revision ID: 073
Revises: 072
Create Date: 2026-04-16

Cria tabela capture_execution_logs para histórico de execuções
de capturas automáticas.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "073"
down_revision: str = "072"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "capture_execution_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "capture_config_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("capture_schedule_configs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column(
            "list_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("lead_lists.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("list_name", sa.Text, nullable=True),
        sa.Column("combo_label", sa.Text, nullable=True),
        sa.Column("leads_received", sa.Integer, server_default="0", nullable=False),
        sa.Column("leads_inserted", sa.Integer, server_default="0", nullable=False),
        sa.Column("leads_skipped", sa.Integer, server_default="0", nullable=False),
        sa.Column("status", sa.String(20), server_default="success", nullable=False),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "executed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("capture_execution_logs")
