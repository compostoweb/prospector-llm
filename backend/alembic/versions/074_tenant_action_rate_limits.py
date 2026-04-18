"""074_add_tenant_action_rate_limits

Revision ID: 074
Revises: 073
Create Date: 2026-04-17 23:20:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "074"
down_revision = "073"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenant_integrations",
        sa.Column(
            "limit_linkedin_post_reaction",
            sa.Integer(),
            nullable=False,
            server_default="40",
        ),
    )
    op.add_column(
        "tenant_integrations",
        sa.Column(
            "limit_linkedin_post_comment",
            sa.Integer(),
            nullable=False,
            server_default="40",
        ),
    )
    op.add_column(
        "tenant_integrations",
        sa.Column(
            "limit_linkedin_inmail",
            sa.Integer(),
            nullable=False,
            server_default="40",
        ),
    )


def downgrade() -> None:
    op.drop_column("tenant_integrations", "limit_linkedin_inmail")
    op.drop_column("tenant_integrations", "limit_linkedin_post_comment")
    op.drop_column("tenant_integrations", "limit_linkedin_post_reaction")
