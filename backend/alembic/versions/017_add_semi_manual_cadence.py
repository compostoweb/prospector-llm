"""017 — Cadência semi-manual: mode, manual_tasks, linkedin_connection.

Adiciona:
  - Campo `mode` na tabela cadences (automatic | semi_manual)
  - Campos `linkedin_connection_status` e `linkedin_connected_at` na tabela leads
  - Enum `manual_task_status` no PostgreSQL
  - Tabela `manual_tasks`

Revision ID: 017
Revises: 016
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Campo mode na cadence ─────────────────────────────────────────
    op.add_column(
        "cadences",
        sa.Column(
            "mode",
            sa.String(50),
            nullable=False,
            server_default="automatic",
            comment="Modo: automatic | semi_manual",
        ),
    )

    # ── Campos de conexão LinkedIn no lead ────────────────────────────
    op.add_column(
        "leads",
        sa.Column(
            "linkedin_connection_status",
            sa.String(50),
            nullable=True,
            comment="Status da conexão LinkedIn: pending | connected | None",
        ),
    )
    op.add_column(
        "leads",
        sa.Column(
            "linkedin_connected_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    # ── Enum manual_task_status ───────────────────────────────────────
    manual_task_status_enum = sa.Enum(
        "pending",
        "content_generated",
        "sent",
        "done_external",
        "skipped",
        name="manual_task_status",
    )
    manual_task_status_enum.create(op.get_bind(), checkfirst=True)

    # ── Tabela manual_tasks ───────────────────────────────────────────
    op.create_table(
        "manual_tasks",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "cadence_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("cadences.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "lead_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("leads.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "cadence_step_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("cadence_steps.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "channel",
            sa.Enum(
                "linkedin_connect",
                "linkedin_dm",
                "email",
                "manual_task",
                name="channel",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("step_number", sa.Integer, nullable=False, server_default="1"),
        sa.Column(
            "status",
            manual_task_status_enum,
            nullable=False,
            server_default="pending",
            index=True,
        ),
        sa.Column("generated_text", sa.Text, nullable=True),
        sa.Column("generated_audio_url", sa.String(500), nullable=True),
        sa.Column("edited_text", sa.Text, nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("unipile_message_id", sa.String(200), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
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


def downgrade() -> None:
    op.drop_table("manual_tasks")

    sa.Enum(name="manual_task_status").drop(op.get_bind(), checkfirst=True)

    op.drop_column("leads", "linkedin_connected_at")
    op.drop_column("leads", "linkedin_connection_status")
    op.drop_column("cadences", "mode")
