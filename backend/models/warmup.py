"""
models/warmup.py

Modelos para o sistema de warmup de e-mail.

WarmupCampaign: campanha de warmup vinculada a uma EmailAccount.
WarmupLog:      registro de cada e-mail de warmup enviado/recebido.
WarmupSeedPool: pool global de contas semente (não é tenant-specific).

Regra de negócio:
  - O warmup aumenta gradualmente o volume de envio para aquecer o IP/domínio.
  - daily_volume_start → daily_volume_target ao longo de ramp_days dias.
  - Os e-mails são trocados entre a conta "real" e contas do seed pool.
  - Cada e-mail enviado deve receber uma resposta (WarmupLog direction=RECEIVED).
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TenantMixin, TimestampMixin


class WarmupCampaign(Base, TenantMixin, TimestampMixin):
    """
    Campanha de warmup vinculada a uma EmailAccount.

    O volume diário cresce linearmente de daily_volume_start até daily_volume_target
    ao longo de ramp_days dias. Após completar os ramp_days, status = COMPLETED.
    """

    __tablename__ = "warmup_campaigns"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email_account_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("email_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Status ────────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(50),
        default="active",
        server_default="active",
        comment="active | paused | completed",
    )

    # ── Progresso ─────────────────────────────────────────────────────
    current_day: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        comment="Dia atual do warmup (0 = primeiro dia)",
    )
    total_sent: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        comment="Total de e-mails enviados nesta campanha",
    )
    total_replied: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        comment="Total de respostas recebidas",
    )
    spam_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        comment="Quantos foram para spam (monitorado via seed pool)",
    )

    # ── Configuração ──────────────────────────────────────────────────
    daily_volume_start: Mapped[int] = mapped_column(
        Integer,
        default=5,
        server_default="5",
        comment="E-mails por dia no início do warmup",
    )
    daily_volume_target: Mapped[int] = mapped_column(
        Integer,
        default=80,
        server_default="80",
        comment="E-mails por dia ao final do warmup",
    )
    ramp_days: Mapped[int] = mapped_column(
        Integer,
        default=30,
        server_default="30",
        comment="Dias para atingir daily_volume_target",
    )


class WarmupLog(Base, TenantMixin):
    """
    Registro individual de um e-mail de warmup.

    direction = SENT:  e-mail enviado pela conta para uma semente
    direction = RECEIVED: resposta recebida de volta de uma semente
    """

    __tablename__ = "warmup_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("warmup_campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    direction: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="sent | received",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="delivered",
        server_default="delivered",
        comment="delivered | opened | replied | spam | failed",
    )
    partner_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="E-mail da conta semente parceira",
    )
    # IDs de mensagem para correlacionar envio ↔ resposta
    message_id_sent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    message_id_reply: Mapped[str | None] = mapped_column(String(500), nullable=True)

    sent_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Hora do envio",
    )
    replied_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Hora da resposta (NULL se ainda não respondeu)",
    )


class WarmupSeedPool(Base):
    """
    Pool global de contas semente de warmup.
    NÃO é tenant-specific — é compartilhado por todos os tenants.

    Cada semente é uma conta de e-mail controlada pelo sistema
    que troca e-mails com as contas em warmup para aquecê-las.
    """

    __tablename__ = "warmup_seed_pool"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        comment="E-mail da conta semente",
    )
    display_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Nome exibido no From: desta semente",
    )
    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="smtp",
        server_default="smtp",
        comment="Provedor desta semente: smtp | google_oauth",
    )
    # Credenciais SMTP opcionais (criptografadas)
    smtp_host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    smtp_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    smtp_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    smtp_password: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
        comment="Fernet-encrypted",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
    )
    last_used_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Última vez que esta semente enviou um e-mail",
    )
