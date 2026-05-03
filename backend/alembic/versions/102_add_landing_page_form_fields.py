"""102 add landing page form fields

Revision ID: 102
Revises: 101
Create Date: 2026-05-03 17:20:00.000000

Adiciona configuração JSONB de campos do formulário por landing page.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "102"
down_revision = "101"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "content_landing_pages",
        sa.Column(
            "form_fields",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Campos do formulário público da LP: key + required por campo.",
        ),
    )


def downgrade() -> None:
    op.drop_column("content_landing_pages", "form_fields")