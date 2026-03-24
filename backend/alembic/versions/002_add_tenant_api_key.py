"""
alembic/versions/002_add_tenant_api_key.py

Adiciona campo api_key_hash à tabela tenants.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column("api_key_hash", sa.String(200), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tenants", "api_key_hash")
