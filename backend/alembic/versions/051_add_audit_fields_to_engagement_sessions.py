"""Add audit fields to content_engagement_sessions.

Revision ID: 051
Revises: 050
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "051"
down_revision = "050"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "content_engagement_sessions",
        sa.Column(
            "selected_theme_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="IDs dos temas selecionados nesta execucao",
        ),
    )
    op.add_column(
        "content_engagement_sessions",
        sa.Column(
            "selected_theme_titles",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Titulos dos temas selecionados nesta execucao",
        ),
    )
    op.add_column(
        "content_engagement_sessions",
        sa.Column(
            "manual_keywords",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Keywords digitadas manualmente pelo usuario",
        ),
    )
    op.add_column(
        "content_engagement_sessions",
        sa.Column(
            "effective_keywords",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Keywords efetivamente usadas no scan",
        ),
    )
    op.add_column(
        "content_engagement_sessions",
        sa.Column(
            "linked_post_context_keywords",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Keywords derivadas do post vinculado",
        ),
    )
    op.add_column(
        "content_engagement_sessions",
        sa.Column(
            "icp_titles_used",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Titulos ICP usados na execucao",
        ),
    )
    op.add_column(
        "content_engagement_sessions",
        sa.Column(
            "icp_sectors_used",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Setores ICP usados na execucao",
        ),
    )


def downgrade() -> None:
    op.drop_column("content_engagement_sessions", "icp_sectors_used")
    op.drop_column("content_engagement_sessions", "icp_titles_used")
    op.drop_column("content_engagement_sessions", "linked_post_context_keywords")
    op.drop_column("content_engagement_sessions", "effective_keywords")
    op.drop_column("content_engagement_sessions", "manual_keywords")
    op.drop_column("content_engagement_sessions", "selected_theme_titles")
    op.drop_column("content_engagement_sessions", "selected_theme_ids")
