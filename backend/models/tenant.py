"""
models/tenant.py

Models de tenant (multi-tenancy) do Prospector.

Responsabilidades:
  - Tenant: representa uma empresa/workspace isolado no sistema
  - TenantIntegration: configurações de integrações externas por tenant
    (Unipile, Pipedrive, limites de rate, preferências de envio)

Cada tenant pode ter suas próprias credenciais de integração,
sobrescrevendo os defaults globais definidos em core/config.py.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.tenant_user import TenantUser


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Tenant(Base):
    """
    Representa uma organização/workspace isolado.
    Toda a data isolation é feita via tenant_id + PostgreSQL RLS.
    """

    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    api_key_hash: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Hash bcrypt da API key — o valor plaintext só é exibido uma vez na criação",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )

    # Relacionamento com as integrações
    integration: Mapped[TenantIntegration | None] = relationship(
        "TenantIntegration",
        back_populates="tenant",
        uselist=False,
        lazy="select",
    )
    members: Mapped[list[TenantUser]] = relationship(
        "TenantUser",
        back_populates="tenant",
        lazy="selectin",
    )


class TenantIntegration(Base):
    """
    Configurações de integrações externas para um tenant específico.
    Cada tenant tem no máximo uma linha nesta tabela (FK unique).
    """

    __tablename__ = "tenant_integrations"
    __table_args__ = (UniqueConstraint("tenant_id", name="uq_tenant_integrations_tenant_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # ── Unipile ───────────────────────────────────────────────────────
    unipile_linkedin_account_id: Mapped[str | None] = mapped_column(String(200))
    unipile_gmail_account_id: Mapped[str | None] = mapped_column(String(200))

    # ── Pipedrive ─────────────────────────────────────────────────────
    pipedrive_api_token: Mapped[str | None] = mapped_column(String(200))
    pipedrive_domain: Mapped[str | None] = mapped_column(String(200))
    pipedrive_stage_interest: Mapped[int | None] = mapped_column(Integer)
    pipedrive_stage_objection: Mapped[int | None] = mapped_column(Integer)
    pipedrive_owner_id: Mapped[int | None] = mapped_column(Integer)

    # ── Notificações ──────────────────────────────────────────────────
    notify_email: Mapped[str | None] = mapped_column(String(254))
    notify_on_interest: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_on_objection: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── Preferências de envio ─────────────────────────────────────────
    allow_personal_email: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── Rate limits por canal (sobrescreve defaults globais) ──────────
    limit_linkedin_connect: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    limit_linkedin_dm: Mapped[int] = mapped_column(Integer, default=40, nullable=False)
    limit_email: Mapped[int] = mapped_column(Integer, default=300, nullable=False)

    # ── LLM — padrão do sistema ───────────────────────────────────────
    llm_default_provider: Mapped[str] = mapped_column(
        String(50),
        default="openai",
        nullable=False,
        comment="Provedor LLM padrão ao criar novas cadências",
    )
    llm_default_model: Mapped[str] = mapped_column(
        String(100),
        default="gpt-5.4-mini",
        nullable=False,
        comment="Modelo LLM padrão ao criar novas cadências",
    )
    llm_default_temperature: Mapped[float] = mapped_column(
        Float,
        default=0.7,
        nullable=False,
        comment="Temperatura LLM padrão (0.0–1.0)",
    )
    llm_default_max_tokens: Mapped[int] = mapped_column(
        Integer,
        default=1024,
        nullable=False,
        comment="Max tokens LLM padrão (64–8192)",
    )

    # ── LLM — padrão Cold Email ───────────────────────────────────────
    cold_email_llm_provider: Mapped[str] = mapped_column(
        String(50),
        default="openai",
        nullable=False,
        comment="Provedor LLM padrão para campanhas de cold email",
    )
    cold_email_llm_model: Mapped[str] = mapped_column(
        String(100),
        default="gpt-5.4-mini",
        nullable=False,
        comment="Modelo LLM padrão para campanhas de cold email",
    )
    cold_email_llm_temperature: Mapped[float] = mapped_column(
        Float,
        default=0.7,
        nullable=False,
        comment="Temperatura LLM para cold email (0.0–1.0)",
    )
    cold_email_llm_max_tokens: Mapped[int] = mapped_column(
        Integer,
        default=512,
        nullable=False,
        comment="Max tokens LLM para cold email (64–8192)",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )

    # Relacionamento reverso
    tenant: Mapped[Tenant] = relationship("Tenant", back_populates="integration")
