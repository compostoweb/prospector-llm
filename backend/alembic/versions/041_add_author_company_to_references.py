"""
041 – Adiciona coluna author_company à tabela content_references.

Revisão: 041
Down revision: 040
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "041"
down_revision = "040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "content_references",
        sa.Column("author_company", sa.String(200), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("content_references", "author_company")
