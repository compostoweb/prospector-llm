"""083 — Cria tabela canônica de pontos de contato do lead."""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "083"
down_revision = "082"
branch_labels = None
depends_on = None


def upgrade() -> None:
    contact_point_kind = postgresql.ENUM(
        "EMAIL",
        "PHONE",
        name="contact_point_kind",
        create_type=False,
    )
    contact_point_kind.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "lead_contact_points",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("lead_id", sa.UUID(), nullable=False),
        sa.Column("kind", contact_point_kind, nullable=False),
        sa.Column("value", sa.String(length=255), nullable=False),
        sa.Column("normalized_value", sa.String(length=255), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("verification_status", sa.String(length=50), nullable=True),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column(
            "quality_bucket",
            sa.Enum(
                "RED",
                "ORANGE",
                "GREEN",
                name="contact_quality_bucket",
                native_enum=False,
            ),
            nullable=True,
        ),
        sa.Column("evidence_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "lead_id",
            "kind",
            "normalized_value",
            name="uq_lead_contact_points_lead_kind_value",
        ),
    )
    op.create_index(
        op.f("ix_lead_contact_points_lead_id"),
        "lead_contact_points",
        ["lead_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_lead_contact_points_normalized_value"),
        "lead_contact_points",
        ["normalized_value"],
        unique=False,
    )
    op.create_index(
        op.f("ix_lead_contact_points_tenant_id"),
        "lead_contact_points",
        ["tenant_id"],
        unique=False,
    )

    op.execute(
        """
        INSERT INTO lead_contact_points (
            id, lead_id, kind, value, normalized_value, source,
            verified, verification_status, quality_score, quality_bucket,
            evidence_json, metadata_json, is_primary, tenant_id, created_at, updated_at
        )
        SELECT
            gen_random_uuid(),
            lead_id,
            'EMAIL',
            email,
            email,
            source,
            verified,
            CASE WHEN verification_status IS NULL THEN NULL ELSE lower(verification_status) END,
            quality_score,
            quality_bucket,
            NULL,
            jsonb_build_object('email_type', lower(email_type::text)),
            is_primary,
            tenant_id,
            created_at,
            updated_at
        FROM lead_emails
        ON CONFLICT ON CONSTRAINT uq_lead_contact_points_lead_kind_value DO NOTHING
        """
    )

    op.execute(
        """
        INSERT INTO lead_contact_points (
            id, lead_id, kind, value, normalized_value, source,
            verified, verification_status, quality_score, quality_bucket,
            evidence_json, metadata_json, is_primary, tenant_id, created_at, updated_at
        )
        SELECT
            gen_random_uuid(),
            id,
            'PHONE',
            phone,
            regexp_replace(phone, '[^0-9]', '', 'g'),
            NULL,
            FALSE,
            NULL,
            NULL,
            NULL,
            NULL,
            NULL,
            TRUE,
            tenant_id,
            created_at,
            updated_at
        FROM leads
        WHERE phone IS NOT NULL
          AND btrim(phone) <> ''
          AND regexp_replace(phone, '[^0-9]', '', 'g') <> ''
        ON CONFLICT ON CONSTRAINT uq_lead_contact_points_lead_kind_value DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_lead_contact_points_tenant_id"), table_name="lead_contact_points")
    op.drop_index(
        op.f("ix_lead_contact_points_normalized_value"),
        table_name="lead_contact_points",
    )
    op.drop_index(op.f("ix_lead_contact_points_lead_id"), table_name="lead_contact_points")
    op.drop_table("lead_contact_points")

    contact_point_kind = postgresql.ENUM(
        "EMAIL",
        "PHONE",
        name="contact_point_kind",
        create_type=False,
    )
    contact_point_kind.drop(op.get_bind(), checkfirst=True)
