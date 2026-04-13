"""059 — Cria tabela normalizada de emails do lead."""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "059"
down_revision = "058"
branch_labels = None
depends_on = None


def upgrade() -> None:
    email_type = postgresql.ENUM(
        "CORPORATE",
        "PERSONAL",
        "UNKNOWN",
        name="email_type",
        create_type=False,
    )
    email_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "lead_emails",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("lead_id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("email_type", email_type, nullable=False),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lead_id", "email", name="uq_lead_emails_lead_id_email"),
    )
    op.create_index(op.f("ix_lead_emails_email"), "lead_emails", ["email"], unique=False)
    op.create_index(op.f("ix_lead_emails_lead_id"), "lead_emails", ["lead_id"], unique=False)
    op.create_index(op.f("ix_lead_emails_tenant_id"), "lead_emails", ["tenant_id"], unique=False)

    op.execute(
        """
        INSERT INTO lead_emails (
            id, lead_id, email, email_type, source,
            verified, is_primary, tenant_id, created_at, updated_at
        )
        SELECT
            gen_random_uuid(),
            id,
            lower(email_corporate),
            'CORPORATE',
            email_corporate_source,
            email_corporate_verified,
            TRUE,
            tenant_id,
            created_at,
            updated_at
        FROM leads
        WHERE email_corporate IS NOT NULL AND btrim(email_corporate) <> ''
        ON CONFLICT ON CONSTRAINT uq_lead_emails_lead_id_email DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO lead_emails (
            id, lead_id, email, email_type, source,
            verified, is_primary, tenant_id, created_at, updated_at
        )
        SELECT
            gen_random_uuid(),
            id,
            lower(email_personal),
            'PERSONAL',
            email_personal_source,
            FALSE,
            TRUE,
            tenant_id,
            created_at,
            updated_at
        FROM leads
        WHERE email_personal IS NOT NULL AND btrim(email_personal) <> ''
        ON CONFLICT ON CONSTRAINT uq_lead_emails_lead_id_email DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_lead_emails_tenant_id"), table_name="lead_emails")
    op.drop_index(op.f("ix_lead_emails_lead_id"), table_name="lead_emails")
    op.drop_index(op.f("ix_lead_emails_email"), table_name="lead_emails")
    op.drop_table("lead_emails")

    email_type = postgresql.ENUM(
        "CORPORATE",
        "PERSONAL",
        "UNKNOWN",
        name="email_type",
        create_type=False,
    )
    email_type.drop(op.get_bind(), checkfirst=True)
