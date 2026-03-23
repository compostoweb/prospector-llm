"""
models/cadence.py  (trecho relevante — campos LLM adicionados)

Cada cadência agora carrega sua própria configuração de LLM:
  - llm_provider:  "openai" | "gemini"
  - llm_model:     ID do modelo (ex: "gpt-4o-mini", "gemini-2.5-flash")
  - llm_temperature: float 0.0–1.0
  - llm_max_tokens:  int

Isso permite que cadências diferentes usem modelos diferentes.
Exemplo: cadência de prospecção low-cost usa gemini-2.5-flash-lite,
cadência de alto valor usa gpt-4o ou gemini-2.5-pro.
"""

import uuid
from datetime import datetime
from sqlalchemy import String, Float, Integer, Boolean, DateTime, ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column
from models.base import Base, TenantMixin


# Defaults globais — usados quando cadência não sobrescreve
DEFAULT_LLM_PROVIDER = "openai"
DEFAULT_LLM_MODEL = "gpt-4o-mini"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 1024


class Cadence(Base, TenantMixin):
    __tablename__ = "cadences"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_personal_email: Mapped[bool] = mapped_column(Boolean, default=False)

    # -------------------------------------------------------
    # Configuração LLM por cadência
    # -------------------------------------------------------
    llm_provider: Mapped[str] = mapped_column(
        String(50),
        default=DEFAULT_LLM_PROVIDER,
        server_default=DEFAULT_LLM_PROVIDER,
        comment="Provedor LLM: openai | gemini",
    )
    llm_model: Mapped[str] = mapped_column(
        String(100),
        default=DEFAULT_LLM_MODEL,
        server_default=DEFAULT_LLM_MODEL,
        comment="ID do modelo (ex: gpt-4o-mini, gemini-2.5-flash)",
    )
    llm_temperature: Mapped[float] = mapped_column(
        Float,
        default=DEFAULT_TEMPERATURE,
        server_default=str(DEFAULT_TEMPERATURE),
        comment="Temperatura (0.0–1.0) — maior = mais criativo",
    )
    llm_max_tokens: Mapped[int] = mapped_column(
        Integer,
        default=DEFAULT_MAX_TOKENS,
        server_default=str(DEFAULT_MAX_TOKENS),
        comment="Máximo de tokens de saída por geração",
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
