"""071_linkedin_search_params_cache.py

Revision ID: 071
Revises: 070
Create Date: 2026-04-16

Cache global de parâmetros de busca LinkedIn (LOCATION, INDUSTRY).
Evita chamadas repetidas à Unipile API para dados de referência.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "071"
down_revision: str = "070"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "linkedin_search_params",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("param_type", sa.String(20), nullable=False, index=True),
        sa.Column("external_id", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("param_type", "external_id", name="uq_li_search_param_type_eid"),
    )


def downgrade() -> None:
    op.drop_table("linkedin_search_params")
