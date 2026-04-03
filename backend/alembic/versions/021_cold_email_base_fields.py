"""021 — Cold email: campos base em cadences, interactions, cadence_steps e leads.

Revision ID: 021
Revises: 020

Alterações:
  cadences:
    - cadence_type VARCHAR(50) DEFAULT 'mixed'

  interactions:
    - opened_at TIMESTAMP WITH TIME ZONE (NULL)

  cadence_steps:
    - subject_used VARCHAR(500) (NULL)

  leads:
    - timezone VARCHAR(100) (NULL)
    - email_bounced_at TIMESTAMP WITH TIME ZONE (NULL)
"""

import sqlalchemy as sa
from alembic import op


revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── cadences ────────────────────────────────────────────────────────
    op.add_column(
        "cadences",
        sa.Column(
            "cadence_type",
            sa.String(50),
            nullable=False,
            server_default="mixed",
            comment="Tipo: mixed | email_only",
        ),
    )

    # ── interactions ────────────────────────────────────────────────────
    op.add_column(
        "interactions",
        sa.Column(
            "opened_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp da primeira abertura do e-mail (tracking pixel)",
        ),
    )

    # ── cadence_steps ────────────────────────────────────────────────────
    op.add_column(
        "cadence_steps",
        sa.Column(
            "subject_used",
            sa.String(500),
            nullable=True,
            comment="Variante de assunto usada no envio (A/B testing)",
        ),
    )

    # ── leads ────────────────────────────────────────────────────────────
    op.add_column(
        "leads",
        sa.Column(
            "timezone",
            sa.String(100),
            nullable=True,
            comment="Fuso horário do lead ex: America/Sao_Paulo",
        ),
    )
    op.add_column(
        "leads",
        sa.Column(
            "email_bounced_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Se preenchido, e-mails para este lead são pulados (bounce detectado)",
        ),
    )


def downgrade() -> None:
    op.drop_column("leads", "email_bounced_at")
    op.drop_column("leads", "timezone")
    op.drop_column("cadence_steps", "subject_used")
    op.drop_column("interactions", "opened_at")
    op.drop_column("cadences", "cadence_type")
