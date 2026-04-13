"""058 — Adiciona status 'dispatching' ao enum e campos de cache de composição.

Correção CRÍTICA: impede que cadence_tick re-enfileire steps já em processamento,
evitando consumo duplicado de tokens LLM (~8M tokens em 2h de loop).

Alterações:
  1. ALTER TYPE stepstatus ADD VALUE 'dispatching'
  2. Adiciona cadence_steps.composed_text   (cache do texto gerado pela LLM)
  3. Adiciona cadence_steps.composed_subject (cache do subject gerado pela LLM)

Revision ID: 058
Revises: 057
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "058"
down_revision = "057"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Adiciona 'DISPATCHING' ao enum PostgreSQL cadence_step_status
    # Os labels no PG são uppercase (PENDING, SENT, etc.) — SQLAlchemy usa .name do Enum.
    op.execute("ALTER TYPE cadence_step_status ADD VALUE IF NOT EXISTS 'DISPATCHING'")

    # 2. Campos de cache de composição LLM no cadence_steps
    op.add_column(
        "cadence_steps",
        sa.Column(
            "composed_text",
            sa.Text(),
            nullable=True,
            comment="Cache do texto/body gerado pela LLM — evita recomposição em retry",
        ),
    )
    op.add_column(
        "cadence_steps",
        sa.Column(
            "composed_subject",
            sa.String(500),
            nullable=True,
            comment="Cache do subject gerado pela LLM (email) — evita recomposição em retry",
        ),
    )


def downgrade() -> None:
    # Colunas podem ser removidas normalmente
    op.drop_column("cadence_steps", "composed_subject")
    op.drop_column("cadence_steps", "composed_text")
    # ALTER TYPE ... DROP VALUE não existe no PostgreSQL — 'dispatching' permanece no enum
    # mas não será usado após downgrade (steps voltarão a ser PENDING).
