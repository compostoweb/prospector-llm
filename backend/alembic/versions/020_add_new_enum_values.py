"""020 — Adiciona novos valores aos ENUMs de canal (Channel) e lead_source.

Revision ID: 020
Revises: 019

Novos valores de Channel:
  linkedin_post_reaction, linkedin_post_comment, linkedin_inmail

O enum Channel existe sob 3 nomes no banco:
  - cadence_step_channel  (cadence_steps.channel)
  - interaction_channel   (interactions.channel)
  - channel               (manual_tasks.channel)

E lead_source recebe: linkedin_search

Nota: StepType NÃO é um PostgreSQL enum — é só um Python Enum usado em
validações Pydantic. Portanto NÃO gera ALTER TYPE step_type.
"""

from alembic import op


revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None

_NEW_CHANNEL_VALUES = [
    "linkedin_post_reaction",
    "linkedin_post_comment",
    "linkedin_inmail",
]

_CHANNEL_ENUM_NAMES = [
    "cadence_step_channel",
    "interaction_channel",
    "channel",
]


def upgrade() -> None:
    for enum_name in _CHANNEL_ENUM_NAMES:
        for value in _NEW_CHANNEL_VALUES:
            op.execute(
                f"ALTER TYPE {enum_name} ADD VALUE IF NOT EXISTS '{value}'"
            )

    op.execute("ALTER TYPE lead_source ADD VALUE IF NOT EXISTS 'linkedin_search'")


def downgrade() -> None:
    # PostgreSQL não suporta remover valores de enum com DROP VALUE.
    pass

