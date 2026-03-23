"""
alembic/versions/004_interaction_direction_enum.py

Converte interactions.direction de String(10) para ENUM interaction_direction.
Dados existentes ('outbound'/'inbound') são preservados na conversão.

Revisão: 004
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "004_interaction_direction_enum"
down_revision = "003_add_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Cria o tipo ENUM (idempotente via DO block para PG < 17)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'interaction_direction') THEN
                CREATE TYPE interaction_direction AS ENUM ('outbound', 'inbound');
            END IF;
        END$$;
    """)

    # Converte a coluna de VARCHAR(10) para o ENUM, preservando dados
    op.execute("""
        ALTER TABLE interactions
        ALTER COLUMN direction TYPE interaction_direction
        USING direction::interaction_direction;
    """)


def downgrade() -> None:
    # Reverte para String(10)
    op.execute("""
        ALTER TABLE interactions
        ALTER COLUMN direction TYPE VARCHAR(10)
        USING direction::TEXT;
    """)

    op.execute("DROP TYPE IF EXISTS interaction_direction;")
