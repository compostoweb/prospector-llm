"""070_add_tenant_user_memberships.py

Revision ID: 070
Revises: 069
Create Date: 2026-04-16

Cria a tabela tenant_users para vincular usuários humanos a tenants com papel
de acesso. Também faz backfill dos usuários ativos legados para o primeiro
tenant ativo, preservando o acesso existente ao painel.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "070"
down_revision = "069"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    tenant_user_role = postgresql.ENUM(
        "TENANT_ADMIN",
        "TENANT_USER",
        name="tenant_user_role",
        create_type=False,
    )
    tenant_user_role.create(bind, checkfirst=True)

    existing_tables = set(inspector.get_table_names())
    if "tenant_users" not in existing_tables:
        op.create_table(
            "tenant_users",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "tenant_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("tenants.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "role",
                tenant_user_role,
                nullable=False,
                server_default="TENANT_USER",
            ),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column(
                "invited_by_user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "joined_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.UniqueConstraint("tenant_id", "user_id", name="uq_tenant_users_tenant_user"),
        )

    existing_indexes = {index["name"] for index in inspector.get_indexes("tenant_users")}
    if "ix_tenant_users_tenant_id" not in existing_indexes:
        op.create_index("ix_tenant_users_tenant_id", "tenant_users", ["tenant_id"])
    if "ix_tenant_users_user_id" not in existing_indexes:
        op.create_index("ix_tenant_users_user_id", "tenant_users", ["user_id"])

    op.execute(
        sa.text(
            """
            WITH default_tenant AS (
                SELECT id
                FROM tenants
                WHERE is_active = true
                ORDER BY created_at ASC
                LIMIT 1
            )
            INSERT INTO tenant_users (
                id,
                tenant_id,
                user_id,
                role,
                is_active,
                joined_at,
                created_at,
                updated_at
            )
            SELECT
                gen_random_uuid(),
                default_tenant.id,
                users.id,
                'TENANT_ADMIN',
                true,
                now(),
                now(),
                now()
            FROM users
            CROSS JOIN default_tenant
            WHERE users.is_active = true
              AND coalesce(users.is_superuser, false) = false
              AND NOT EXISTS (
                  SELECT 1
                  FROM tenant_users existing
                  WHERE existing.tenant_id = default_tenant.id
                    AND existing.user_id = users.id
              )
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_tenant_users_user_id", table_name="tenant_users")
    op.drop_index("ix_tenant_users_tenant_id", table_name="tenant_users")
    op.drop_table("tenant_users")
    postgresql.ENUM(name="tenant_user_role").drop(op.get_bind(), checkfirst=True)
