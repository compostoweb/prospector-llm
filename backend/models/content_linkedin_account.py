"""
models/content_linkedin_account.py

ContentLinkedInAccount — conta LinkedIn do tenant para uso exclusivo
no modulo Content Hub (OAuth com w_member_social + r_liteprofile).

Diferente do LinkedInAccount (usado no modulo de prospeccao via Unipile),
esta conta e autenticada diretamente via OAuth 2.0 do LinkedIn para
publicacao de posts UGC.

Tokens sao armazenados criptografados com Fernet se
LINKEDIN_ACCOUNT_ENCRYPTION_KEY estiver configurada.
Um unico registro por tenant (UniqueConstraint na migration).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

# Campos adicionados em 034_content_li_at_sync:
# li_at_cookie, last_voyager_sync_at
from models.base import Base, TenantMixin, TimestampMixin


class ContentLinkedInAccount(Base, TenantMixin, TimestampMixin):
    """
    Conta LinkedIn OAuth para publicacao de posts no Content Hub.

    Exatamente uma conta por tenant (UNIQUE(tenant_id) na migration).
    person_urn = 'urn:li:person:{person_id}' — usado no payload UGC Post.
    """

    __tablename__ = "content_linkedin_accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    person_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="LinkedIn person ID, ex: 'AbCdEfGhIj'",
    )
    person_urn: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="urn:li:person:{person_id}",
    )
    display_name: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
        comment="Nome exibido no LinkedIn",
    )

    # ── Tokens OAuth (Fernet-encrypted se LINKEDIN_ACCOUNT_ENCRYPTION_KEY definida)
    access_token: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="OAuth 2.0 access token (Fernet-encrypted)",
    )
    refresh_token: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="OAuth 2.0 refresh token (Fernet-encrypted)",
    )
    token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    scopes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Scopes concedidos, ex: 'r_liteprofile w_member_social'",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        comment="False = conta desconectada",
    )
    connected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Data/hora da primeira conexao OAuth",
    )

    # ── Voyager Analytics (Analytics pessoal via cookie, migration 034) ──
    li_at_cookie: Mapped[str | None] = mapped_column(
        String(2000),
        nullable=True,
        comment="Cookie li_at criptografado com Fernet — usado para buscar métricas via Voyager API",
    )
    last_voyager_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp da última sincronização de métricas via Voyager API",
    )
