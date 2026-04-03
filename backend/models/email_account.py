"""
models/email_account.py

EmailAccount — conta de e-mail conectada ao tenant.

Cada tenant pode ter múltiplas contas de e-mail configuradas com diferentes
provedores (Unipile Gmail, Google OAuth direto, SMTP genérico).

Campos sensíveis (tokens, senhas) são armazenados criptografados com Fernet.
Use email_account_service.encrypt_credential / decrypt_credential para acessá-los.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TenantMixin, TimestampMixin


class EmailAccount(Base, TenantMixin, TimestampMixin):
    """
    Conta de e-mail de um tenant.

    provider_type define como o envio é feito:
      - unipile_gmail: via Unipile API (conta Gmail conectada lá)
      - google_oauth:  via Gmail API com refresh_token OAuth
      - smtp:          via SMTP genérico (aiosmtplib)
    """

    __tablename__ = "email_accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ── Identificação ──────────────────────────────────────────────────
    display_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Nome amigável ex: 'Adriano - gmail principal'",
    )
    email_address: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Endereço de e-mail do remetente",
    )
    from_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Nome exibido no From: — se NULL usa display_name",
    )

    # ── Tipo de provider ───────────────────────────────────────────────
    provider_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="unipile_gmail | google_oauth | smtp",
    )

    # ── Unipile ────────────────────────────────────────────────────────
    unipile_account_id: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="ID da conta Gmail no Unipile (account_id)",
    )

    # ── Google OAuth ───────────────────────────────────────────────────
    # Armazenado criptografado com Fernet (EMAIL_ACCOUNT_ENCRYPTION_KEY)
    google_refresh_token: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
        comment="Google OAuth refresh_token (Fernet-encrypted)",
    )
    # Usado para polling incremental da inbox via Gmail History API
    gmail_history_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="historyId do último poll Gmail — checkpoint de sincronização",
    )

    # ── SMTP ───────────────────────────────────────────────────────────
    smtp_host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    smtp_port: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        default=587,
        comment="Porta SMTP (587 STARTTLS, 465 SSL, 25 plain)",
    )
    smtp_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Armazenado criptografado com Fernet
    smtp_password: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
        comment="Senha SMTP (Fernet-encrypted)",
    )
    smtp_use_tls: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        comment="True = STARTTLS/SSL; False = sem criptografia",
    )

    # ── IMAP (opcional — para polling de replies em contas SMTP) ──────
    imap_host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    imap_port: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Porta IMAP (993 SSL, 143 STARTTLS)",
    )
    imap_use_ssl: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        comment="True = IMAP over SSL (porta 993)",
    )
    # Armazenado criptografado com Fernet (EMAIL_ACCOUNT_ENCRYPTION_KEY)
    imap_password: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
        comment="Senha IMAP (Fernet-encrypted) — usa mesmo usuário do SMTP",
    )
    # Checkpoint de sincronização (UID do último email processado no IMAP)
    imap_last_uid: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="UID do último e-mail inbound processado via IMAP",
    )

    # ── Limites e controles ────────────────────────────────────────────
    daily_send_limit: Mapped[int] = mapped_column(
        Integer,
        default=50,
        server_default="50",
        comment="Máximo de e-mails por dia para esta conta",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        comment="False = conta pausada / desconectada",
    )

    # ── Warmup ────────────────────────────────────────────────────────
    is_warmup_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        comment="True = conta participando de campanha de warmup",
    )

    # ── Assinatura de e-mail ───────────────────────────────────────────
    email_signature: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Assinatura HTML/texto inserida ao final dos e-mails enviados",
    )
