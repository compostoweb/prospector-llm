"""Add extra fields to leads: first_name, last_name, job_title, company_domain, industry, company_size, location

Revision ID: 007
Revises: 006
Create Date: 2025-01-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("leads", sa.Column("first_name", sa.String(150), nullable=True))
    op.add_column("leads", sa.Column("last_name", sa.String(150), nullable=True))
    op.add_column("leads", sa.Column("job_title", sa.String(200), nullable=True))
    op.add_column("leads", sa.Column("company_domain", sa.String(500), nullable=True))
    op.add_column("leads", sa.Column("industry", sa.String(200), nullable=True))
    op.add_column("leads", sa.Column("company_size", sa.String(50), nullable=True))
    op.add_column("leads", sa.Column("location", sa.String(300), nullable=True))


def downgrade() -> None:
    op.drop_column("leads", "location")
    op.drop_column("leads", "company_size")
    op.drop_column("leads", "industry")
    op.drop_column("leads", "company_domain")
    op.drop_column("leads", "job_title")
    op.drop_column("leads", "last_name")
    op.drop_column("leads", "first_name")
