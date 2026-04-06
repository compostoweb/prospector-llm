"""037 — Adiciona campos de análise LLM (Batch API) à tabela leads.

Campos adicionados:
  - llm_icp_score        FLOAT (0–100)
  - llm_icp_reasoning    TEXT
  - llm_personalization_notes TEXT
  - llm_analyzed_at      TIMESTAMPTZ

Revision ID: 037
Revises: 036
"""

import sqlalchemy as sa
from alembic import op


revision = "037"
down_revision = "036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("leads", sa.Column("llm_icp_score", sa.Float(), nullable=True))
    op.add_column("leads", sa.Column("llm_icp_reasoning", sa.Text(), nullable=True))
    op.add_column("leads", sa.Column("llm_personalization_notes", sa.Text(), nullable=True))
    op.add_column(
        "leads",
        sa.Column("llm_analyzed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("leads", "llm_analyzed_at")
    op.drop_column("leads", "llm_personalization_notes")
    op.drop_column("leads", "llm_icp_reasoning")
    op.drop_column("leads", "llm_icp_score")
