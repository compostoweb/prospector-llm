"""082 — Adiciona campos de qualidade aos emails do lead."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "082"
down_revision = "081"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "lead_emails",
        sa.Column(
            "verification_status",
            sa.Enum(
                "VALID",
                "ACCEPT_ALL",
                "UNKNOWN",
                "INVALID",
                "DISPOSABLE",
                "ABUSE",
                "DO_NOT_MAIL",
                "SPAMTRAP",
                "WEBMAIL",
                name="email_verification_status",
                native_enum=False,
            ),
            nullable=True,
        ),
    )
    op.add_column("lead_emails", sa.Column("quality_score", sa.Float(), nullable=True))
    op.add_column(
        "lead_emails",
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
    )

    op.execute(
        """
        UPDATE lead_emails
        SET verification_status = 'VALID',
            quality_score = 0.95,
            quality_bucket = 'GREEN'
        WHERE verified IS TRUE
        """
    )


def downgrade() -> None:
    op.drop_column("lead_emails", "quality_bucket")
    op.drop_column("lead_emails", "quality_score")
    op.drop_column("lead_emails", "verification_status")
