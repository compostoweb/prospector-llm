"""
models/linkedin_account.py

LinkedInAccount — conta LinkedIn conectada ao tenant.

Cada tenant pode ter múltiplas contas LinkedIn configuradas com diferentes
provedores (Unipile ou nativo via cookie li_at).

Campos sensíveis (li_at_cookie) são armazenados criptografados com Fernet.
Use linkedin_account_service.encrypt_credential / decrypt_credential.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TenantMixin, TimestampMixin


class LinkedInAccount(Base, TenantMixin, TimestampMixin):
    """
    Conta LinkedIn de um tenant.

    provider_type define como o envio é feito:
      - unipile: via Unipile API (conta LinkedIn conectada lá)
      - native:  via API Voyager do LinkedIn com cookie li_at
    """

    __tablename__ = "linkedin_accounts"
    __table_args__ = (
        Index("ix_linkedin_accounts_tenant_owner", "tenant_id", "owner_user_id"),
        Index(
            "ix_linkedin_accounts_tenant_unipile_account",
            "tenant_id",
            "unipile_account_id",
            postgresql_where=text("unipile_account_id IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ── Identificação ──────────────────────────────────────────────────
    display_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Nome amigável ex: 'Adriano - conta principal'",
    )
    linkedin_username: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Username do LinkedIn (parte final da URL do perfil)",
    )
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Usuário do tenant dono operacional desta conta.",
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Usuário que conectou/criou esta conta no sistema.",
    )

    # ── Tipo de provider ───────────────────────────────────────────────
    provider_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="unipile | native",
    )

    # ── Unipile ────────────────────────────────────────────────────────
    unipile_account_id: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="ID da conta LinkedIn no Unipile (account_id)",
    )

    # ── Native (cookie li_at) ──────────────────────────────────────────
    # Armazenado criptografado com Fernet (LINKEDIN_ACCOUNT_ENCRYPTION_KEY)
    li_at_cookie: Mapped[str | None] = mapped_column(
        String(2000),
        nullable=True,
        comment="Cookie li_at do LinkedIn (Fernet-encrypted)",
    )

    # ── Limites e controles ────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        comment="False = conta pausada / desconectada",
    )
    supports_inmail: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        comment="True quando a conta emissora tem capability operacional para InMail",
    )
    provider_status: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Status operacional reportado pelo provider, ex: OK, CREDENTIALS, ERROR.",
    )
    last_status_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Última atualização de status recebida do provider.",
    )
    last_health_check_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Última verificação ativa de saúde da conta.",
    )
    health_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Último erro de health check ou reconexão, sem credenciais sensíveis.",
    )
    connected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Momento em que a conta foi conectada com sucesso.",
    )
    disconnected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Momento em que a conta foi marcada como desconectada.",
    )
    reconnect_required_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Momento em que o sistema detectou necessidade de reconexão.",
    )

    # ── Polling state (provider nativo) ───────────────────────────────
    last_polled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Última vez que o poller verificou novas mensagens",
    )
