"""015 — Adiciona campos de contexto de prospecção na cadência.

Novos campos:
  - target_segment: segmento-alvo da campanha
  - persona_description: descrição da persona ideal
  - offer_description: proposta de valor resumida
  - tone_instructions: instruções customizadas de tom

Esses campos alimentam os prompts da IA para personalização enterprise.

Revision ID: 015
Revises: 014
Create Date: 2025-07-25
"""

from alembic import op
import sqlalchemy as sa

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cadences",
        sa.Column(
            "target_segment",
            sa.String(300),
            nullable=True,
            comment="Segmento-alvo ex: 'SaaS B2B', 'indústria farmacêutica'.",
        ),
    )
    op.add_column(
        "cadences",
        sa.Column(
            "persona_description",
            sa.Text(),
            nullable=True,
            comment="Descrição da persona ideal: cargo, dores, prioridades.",
        ),
    )
    op.add_column(
        "cadences",
        sa.Column(
            "offer_description",
            sa.Text(),
            nullable=True,
            comment="Proposta de valor resumida para a IA.",
        ),
    )
    op.add_column(
        "cadences",
        sa.Column(
            "tone_instructions",
            sa.Text(),
            nullable=True,
            comment="Instruções extras de tom/voz para a IA.",
        ),
    )


def downgrade() -> None:
    op.drop_column("cadences", "tone_instructions")
    op.drop_column("cadences", "offer_description")
    op.drop_column("cadences", "persona_description")
    op.drop_column("cadences", "target_segment")
