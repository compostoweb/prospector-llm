"""028 — Adiciona linkedin_account_id na tabela cadences.

Revision ID: 028
Revises: 027
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PGUUID


revision = "028"
down_revision = "027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cadences",
        sa.Column(
            "linkedin_account_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("linkedin_accounts.id", ondelete="SET NULL"),
            nullable=True,
            comment="Conta LinkedIn usada nos steps (LinkedInAccount). NULL = usa Unipile global.",
        ),
    )
    op.create_index(
        "ix_cadences_linkedin_account_id",
        "cadences",
        ["linkedin_account_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_cadences_linkedin_account_id", table_name="cadences")
    op.drop_column("cadences", "linkedin_account_id")
