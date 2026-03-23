"""
models/user.py

Model de usuário humano que autentica via Google OAuth.

Separado de Tenant (acesso máquina/API key) — usado para login no painel admin.

Fluxo de acesso:
  1. Superadmin cadastra o email do usuário na tabela `users` (allowlist).
  2. Usuário faz login via GET /auth/google/login.
  3. Google authenica e redireciona para GET /auth/google/callback.
  4. O sistema verifica se o email está na allowlist e ativo.
  5. JWT de usuário é emitido com user_id, email, is_superuser.

Nenhum email pode logar sem estar previamente cadastrado na tabela.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    """
    Usuário humano autenticado via Google OAuth.

    O campo google_sub (claim 'sub' do Google) é preenchido no primeiro login
    e serve como chave de busca em acessos subsequentes para maior eficiência.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(
        String(254),
        nullable=False,
        unique=True,
        index=True,
    )
    name: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
        comment="Nome completo vindo do perfil Google — preenchido no primeiro login",
    )
    google_sub: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        unique=True,
        index=True,
        comment="ID único do Google (claim 'sub') — preenchido no primeiro login via OAuth",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Super-admin com acesso total — pode gerenciar tenants e usuários",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )
