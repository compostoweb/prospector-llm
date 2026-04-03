"""030 — Adiciona campos de polling de inbox (Gmail historyId + IMAP) em email_accounts.

Revision ID: 030
Revises: 029
"""

import sqlalchemy as sa
from alembic import op


revision = "030"
down_revision = "029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Gmail History API — checkpoint de sincronização
    op.add_column(
        "email_accounts",
        sa.Column("gmail_history_id", sa.String(100), nullable=True),
    )
    # IMAP — polling de replies para contas SMTP
    op.add_column(
        "email_accounts",
        sa.Column("imap_host", sa.String(255), nullable=True),
    )
    op.add_column(
        "email_accounts",
        sa.Column("imap_port", sa.Integer, nullable=True),
    )
    op.add_column(
        "email_accounts",
        sa.Column(
            "imap_use_ssl",
            sa.Boolean,
            nullable=False,
            server_default="true",
        ),
    )
    op.add_column(
        "email_accounts",
        sa.Column("imap_password", sa.String(1000), nullable=True),
    )
    op.add_column(
        "email_accounts",
        sa.Column("imap_last_uid", sa.String(100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("email_accounts", "gmail_history_id")
    op.drop_column("email_accounts", "imap_host")
    op.drop_column("email_accounts", "imap_port")
    op.drop_column("email_accounts", "imap_use_ssl")
    op.drop_column("email_accounts", "imap_password")
    op.drop_column("email_accounts", "imap_last_uid")
