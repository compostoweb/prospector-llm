"""036 — Adiciona campos LLM padrão (sistema + cold email) em tenant_integrations.

Revision ID: 036
Revises: 029fbde58dfb
"""

import sqlalchemy as sa
from alembic import op


revision = "036"
down_revision = "029fbde58dfb"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # LLM — padrão do sistema
    op.add_column("tenant_integrations", sa.Column("llm_default_provider", sa.String(50), nullable=False, server_default="openai"))
    op.add_column("tenant_integrations", sa.Column("llm_default_model", sa.String(100), nullable=False, server_default="gpt-4o-mini"))
    op.add_column("tenant_integrations", sa.Column("llm_default_temperature", sa.Float(), nullable=False, server_default="0.7"))
    op.add_column("tenant_integrations", sa.Column("llm_default_max_tokens", sa.Integer(), nullable=False, server_default="1024"))

    # LLM — padrão Cold Email
    op.add_column("tenant_integrations", sa.Column("cold_email_llm_provider", sa.String(50), nullable=False, server_default="openai"))
    op.add_column("tenant_integrations", sa.Column("cold_email_llm_model", sa.String(100), nullable=False, server_default="gpt-4o-mini"))
    op.add_column("tenant_integrations", sa.Column("cold_email_llm_temperature", sa.Float(), nullable=False, server_default="0.7"))
    op.add_column("tenant_integrations", sa.Column("cold_email_llm_max_tokens", sa.Integer(), nullable=False, server_default="512"))


def downgrade() -> None:
    op.drop_column("tenant_integrations", "cold_email_llm_max_tokens")
    op.drop_column("tenant_integrations", "cold_email_llm_temperature")
    op.drop_column("tenant_integrations", "cold_email_llm_model")
    op.drop_column("tenant_integrations", "cold_email_llm_provider")
    op.drop_column("tenant_integrations", "llm_default_max_tokens")
    op.drop_column("tenant_integrations", "llm_default_temperature")
    op.drop_column("tenant_integrations", "llm_default_model")
    op.drop_column("tenant_integrations", "llm_default_provider")
