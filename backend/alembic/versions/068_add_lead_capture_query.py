"""068_add_lead_capture_query.py

Revision ID: 068
Revises: 067
Create Date: 2026-04-15

Adiciona o campo capture_query à tabela leads.
Armazena o termo de busca que originou o lead na captura automática
(ex: "academia" para Maps, "CEO em São Paulo" para B2B).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "068"
down_revision = "067"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "leads",
        sa.Column("capture_query", sa.String(500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("leads", "capture_query")
