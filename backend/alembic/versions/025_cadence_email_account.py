"""025 — Adiciona email_account_id na tabela cadences.

Revision ID: 025
Revises: 024
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PGUUID


revision = "025"
down_revision = "024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cadences",
        sa.Column(
            "email_account_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("email_accounts.id", ondelete="SET NULL"),
            nullable=True,
            comment="Conta de e-mail preferencial para steps EMAIL. NULL = usa Unipile global.",
        ),
    )
    op.create_index(
        "ix_cadences_email_account_id",
        "cadences",
        ["email_account_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_cadences_email_account_id", table_name="cadences")
    op.drop_column("cadences", "email_account_id")
