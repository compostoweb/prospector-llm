"""066_add_capture_schedule_configs.py

Revision ID: 066
Revises: 065
Create Date: 2026-04-15
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "066"
down_revision = "065"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "capture_schedule_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("max_items", sa.Integer(), nullable=False, server_default="25"),
        # Google Maps
        sa.Column("maps_search_terms", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("maps_location", sa.String(300), nullable=True),
        sa.Column("maps_categories", postgresql.ARRAY(sa.Text()), nullable=True),
        # B2B Database
        sa.Column("b2b_job_titles", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("b2b_locations", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("b2b_cities", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("b2b_industries", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("b2b_company_keywords", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("b2b_company_sizes", postgresql.ARRAY(sa.Text()), nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("tenant_id", "source", name="uq_capture_schedule_tenant_source"),
    )
    op.create_index(
        "ix_capture_schedule_configs_tenant_id",
        "capture_schedule_configs",
        ["tenant_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_capture_schedule_configs_tenant_id")
    op.drop_table("capture_schedule_configs")
