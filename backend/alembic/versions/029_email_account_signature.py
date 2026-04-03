"""029 — Adiciona email_signature na tabela email_accounts.

Revision ID: 029
Revises: 028
"""

import sqlalchemy as sa
from alembic import op


revision = "029"
down_revision = "028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "email_accounts",
        sa.Column(
            "email_signature",
            sa.String(10000),
            nullable=True,
            comment="Assinatura HTML/texto inserida ao final dos e-mails enviados",
        ),
    )


def downgrade() -> None:
    op.drop_column("email_accounts", "email_signature")
