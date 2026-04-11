"""Create engagement events and discovery queries.

Revision ID: 052
Revises: 051
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "052"
down_revision = "051"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "content_engagement_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_engagement_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_content_engagement_events_tenant_id",
        "content_engagement_events",
        ["tenant_id"],
    )
    op.create_index(
        "ix_content_engagement_events_session_id",
        "content_engagement_events",
        ["session_id"],
    )
    op.create_index(
        "ix_content_engagement_events_event_type",
        "content_engagement_events",
        ["event_type"],
    )

    op.create_table(
        "content_engagement_discovery_queries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(30), nullable=False, server_default="google_operators"),
        sa.Column("query_text", sa.String(500), nullable=False),
        sa.Column("criteria", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "imported_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_engagement_sessions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_content_engagement_discovery_queries_tenant_id",
        "content_engagement_discovery_queries",
        ["tenant_id"],
    )
    op.create_index(
        "ix_content_engagement_discovery_queries_provider",
        "content_engagement_discovery_queries",
        ["provider"],
    )
    op.create_index(
        "ix_content_engagement_discovery_queries_imported_session_id",
        "content_engagement_discovery_queries",
        ["imported_session_id"],
    )


def downgrade() -> None:
    op.drop_table("content_engagement_discovery_queries")
    op.drop_table("content_engagement_events")
