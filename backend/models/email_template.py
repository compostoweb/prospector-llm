"""
models/email_template.py

Templates reutilizáveis de e-mail para cold email / cadências email-only.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TenantMixin, TimestampMixin


class EmailTemplate(Base, TenantMixin, TimestampMixin):
    """
    Template de e-mail salvo pelo tenant.
    Pode ser referenciado em steps de cadência (email_template_id em steps_template),
    substituindo a geração via LLM por um corpo fixo personalizado.
    """

    __tablename__ = "email_templates"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Nome interno do template (ex: 'Abordagem SaaS v2')",
    )
    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        default=None,
    )
    category: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        default=None,
        comment="Categoria livre para organização (ex: 'first_contact', 'followup')",
    )

    # ── Conteúdo do e-mail ────────────────────────────────────────────
    subject: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Assunto padrão do e-mail. Suporta variáveis: {{name}}, {{company}}.",
    )
    body_html: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Corpo HTML do e-mail. Suporta variáveis: {{name}}, {{company}}, {{job_title}}.",
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
