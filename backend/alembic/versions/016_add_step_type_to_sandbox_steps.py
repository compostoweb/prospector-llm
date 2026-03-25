"""016 — Adiciona campo step_type na tabela sandbox_steps.

Permite que o usuário defina manualmente o tipo de instrução de cada step
(ex: email_first, email_followup, linkedin_dm_post_connect) ao invés de
depender apenas da inferência automática.

Revision ID: 016
Revises: 015
"""

from alembic import op
import sqlalchemy as sa

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sandbox_steps",
        sa.Column("step_type", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sandbox_steps", "step_type")
