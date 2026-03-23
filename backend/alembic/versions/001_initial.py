"""
alembic/versions/001_initial.py

Migração inicial — cria todas as tabelas do Prospector.

Tabelas criadas:
  - tenants
  - tenant_integrations
  - leads
  - cadences
  - cadence_steps
  - interactions

Cada tabela recebe:
  - Indexes para os campos de busca mais comuns
  - PostgreSQL Row-Level Security (RLS) baseado em app.current_tenant_id

Revisão: 001
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM as PgEnum

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── ENUMs — criação idempotente via DO block (compatível com PG < 17) ──
    # CREATE TYPE IF NOT EXISTS só existe a partir do PostgreSQL 17.
    # O bloco DO ignora DuplicateObjectError caso o tipo já exista.
    _create_enum_sql = """
DO $$
BEGIN
    BEGIN
        CREATE TYPE lead_source AS ENUM ('manual', 'apify_maps', 'apify_linkedin', 'import', 'api');
    EXCEPTION WHEN duplicate_object THEN NULL; END;
    BEGIN
        CREATE TYPE lead_status AS ENUM ('raw', 'enriched', 'in_cadence', 'converted', 'archived');
    EXCEPTION WHEN duplicate_object THEN NULL; END;
    BEGIN
        CREATE TYPE cadence_step_channel AS ENUM ('linkedin_connect', 'linkedin_dm', 'email');
    EXCEPTION WHEN duplicate_object THEN NULL; END;
    BEGIN
        CREATE TYPE cadence_step_status AS ENUM ('pending', 'sent', 'replied', 'skipped', 'failed');
    EXCEPTION WHEN duplicate_object THEN NULL; END;
    BEGIN
        CREATE TYPE interaction_channel AS ENUM ('linkedin_connect', 'linkedin_dm', 'email');
    EXCEPTION WHEN duplicate_object THEN NULL; END;
    BEGIN
        CREATE TYPE interaction_intent AS ENUM ('interest', 'objection', 'not_interested', 'neutral', 'out_of_office');
    EXCEPTION WHEN duplicate_object THEN NULL; END;
END
$$;
"""
    op.execute(_create_enum_sql)

    # PgEnum com create_type=False apenas referencia o tipo já criado acima
    lead_source_t = PgEnum(name="lead_source", create_type=False)
    lead_status_t = PgEnum(name="lead_status", create_type=False)
    cs_channel_t = PgEnum(name="cadence_step_channel", create_type=False)
    cs_status_t = PgEnum(name="cadence_step_status", create_type=False)
    int_channel_t = PgEnum(name="interaction_channel", create_type=False)
    int_intent_t = PgEnum(name="interaction_intent", create_type=False)

    # ── tenants ───────────────────────────────────────────────────────

    op.create_table(
        "tenants",
        sa.Column("id", sa.UUID(), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_tenants_slug"),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"])

    # ── tenant_integrations ───────────────────────────────────────────

    op.create_table(
        "tenant_integrations",
        sa.Column("id", sa.UUID(), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("unipile_linkedin_account_id", sa.String(200), nullable=True),
        sa.Column("unipile_gmail_account_id", sa.String(200), nullable=True),
        sa.Column("pipedrive_api_token", sa.String(200), nullable=True),
        sa.Column("pipedrive_domain", sa.String(200), nullable=True),
        sa.Column("pipedrive_stage_interest", sa.Integer(), nullable=True),
        sa.Column("pipedrive_stage_objection", sa.Integer(), nullable=True),
        sa.Column("pipedrive_owner_id", sa.Integer(), nullable=True),
        sa.Column("notify_email", sa.String(254), nullable=True),
        sa.Column("notify_on_interest", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("notify_on_objection", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("allow_personal_email", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("limit_linkedin_connect", sa.Integer(), nullable=False, server_default=sa.text("20")),
        sa.Column("limit_linkedin_dm", sa.Integer(), nullable=False, server_default=sa.text("40")),
        sa.Column("limit_email", sa.Integer(), nullable=False, server_default=sa.text("300")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", name="uq_tenant_integrations_tenant_id"),
    )
    op.create_index("ix_tenant_integrations_tenant_id", "tenant_integrations", ["tenant_id"])

    # Habilita RLS em tenant_integrations
    op.execute("ALTER TABLE tenant_integrations ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON tenant_integrations
        USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
    """)

    # ── leads ─────────────────────────────────────────────────────────

    op.create_table(
        "leads",
        sa.Column("id", sa.UUID(), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("company", sa.String(300), nullable=True),
        sa.Column("website", sa.String(500), nullable=True),
        sa.Column("linkedin_url", sa.String(500), nullable=True),
        sa.Column("linkedin_profile_id", sa.String(200), nullable=True),
        sa.Column("city", sa.String(200), nullable=True),
        sa.Column("segment", sa.String(200), nullable=True),
        sa.Column("source", lead_source_t, nullable=False, server_default=sa.text("'manual'")),
        sa.Column("status", lead_status_t, nullable=False, server_default=sa.text("'raw'")),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("email_corporate", sa.String(254), nullable=True),
        sa.Column("email_corporate_source", sa.String(100), nullable=True),
        sa.Column("email_corporate_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("email_personal", sa.String(254), nullable=True),
        sa.Column("email_personal_source", sa.String(100), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("enriched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("linkedin_url", name="uq_leads_linkedin_url"),
    )
    op.create_index("ix_leads_tenant_id", "leads", ["tenant_id"])
    op.create_index("ix_leads_linkedin_url", "leads", ["linkedin_url"])
    op.create_index("ix_leads_linkedin_profile_id", "leads", ["linkedin_profile_id"])
    op.create_index("ix_leads_status", "leads", ["status"])
    op.create_index("ix_leads_email_corporate", "leads", ["email_corporate"])

    # Trigger para updated_at automático
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ language 'plpgsql'
    """)
    op.execute("""
        CREATE TRIGGER leads_updated_at
        BEFORE UPDATE ON leads
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
    """)

    # Habilita RLS em leads
    op.execute("ALTER TABLE leads ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON leads
        USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
    """)

    # ── cadences ──────────────────────────────────────────────────────

    op.create_table(
        "cadences",
        sa.Column("id", sa.UUID(), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("allow_personal_email", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("llm_provider", sa.String(50), nullable=False, server_default=sa.text("'openai'")),
        sa.Column("llm_model", sa.String(100), nullable=False, server_default=sa.text("'gpt-4o-mini'")),
        sa.Column("llm_temperature", sa.Float(), nullable=False, server_default=sa.text("0.7")),
        sa.Column("llm_max_tokens", sa.Integer(), nullable=False, server_default=sa.text("1024")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cadences_tenant_id", "cadences", ["tenant_id"])

    op.execute("""
        CREATE TRIGGER cadences_updated_at
        BEFORE UPDATE ON cadences
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
    """)

    # Habilita RLS em cadences
    op.execute("ALTER TABLE cadences ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON cadences
        USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
    """)

    # ── cadence_steps ─────────────────────────────────────────────────

    op.create_table(
        "cadence_steps",
        sa.Column("id", sa.UUID(), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("cadence_id", sa.UUID(), nullable=False),
        sa.Column("lead_id", sa.UUID(), nullable=False),
        sa.Column("channel", cs_channel_t, nullable=False),
        sa.Column("step_number", sa.Integer(), nullable=False),
        sa.Column("day_offset", sa.Integer(), nullable=False),
        sa.Column("use_voice", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("status", cs_status_t, nullable=False, server_default=sa.text("'pending'")),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cadence_id"], ["cadences.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cadence_steps_tenant_id", "cadence_steps", ["tenant_id"])
    op.create_index("ix_cadence_steps_cadence_id", "cadence_steps", ["cadence_id"])
    op.create_index("ix_cadence_steps_lead_id", "cadence_steps", ["lead_id"])
    op.create_index("ix_cadence_steps_status", "cadence_steps", ["status"])
    op.create_index("ix_cadence_steps_scheduled_at", "cadence_steps", ["scheduled_at"])

    # Habilita RLS em cadence_steps
    op.execute("ALTER TABLE cadence_steps ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON cadence_steps
        USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
    """)

    # ── interactions ──────────────────────────────────────────────────

    op.create_table(
        "interactions",
        sa.Column("id", sa.UUID(), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("lead_id", sa.UUID(), nullable=False),
        sa.Column("channel", int_channel_t, nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("content_audio_url", sa.String(1000), nullable=True),
        sa.Column("intent", int_intent_t, nullable=True),
        sa.Column("unipile_message_id", sa.String(200), nullable=True),
        sa.Column("opened", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_interactions_tenant_id", "interactions", ["tenant_id"])
    op.create_index("ix_interactions_lead_id", "interactions", ["lead_id"])
    op.create_index("ix_interactions_channel", "interactions", ["channel"])
    op.create_index("ix_interactions_unipile_message_id", "interactions", ["unipile_message_id"])

    # Habilita RLS em interactions
    op.execute("ALTER TABLE interactions ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON interactions
        USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
    """)


def downgrade() -> None:
    # Remove tabelas na ordem inversa de dependência
    for table in ("interactions", "cadence_steps", "cadences", "leads", "tenant_integrations", "tenants"):
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")

    # Remove enums
    for enum_name in (
        "lead_source", "lead_status", "channel", "step_status", "intent",
        "cadence_step_channel", "cadence_step_status",
        "interaction_channel", "interaction_intent",
    ):
        op.execute(f"DROP TYPE IF EXISTS {enum_name} CASCADE")

    # Remove a função de trigger
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column CASCADE")
