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

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TenantMixin, TimestampMixin


# Defaults globais — usados quando cadência não sobrescreve
DEFAULT_LLM_PROVIDER = "openai"
DEFAULT_LLM_MODEL = "gpt-4o-mini"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 1024


class Cadence(Base, TenantMixin, TimestampMixin):
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

    # -------------------------------------------------------
    # Template de steps customizável (JSONB)
    # -------------------------------------------------------
    # Formato: [{"channel": "linkedin_connect", "day_offset": 0, "use_voice": false}, ...]
    # Se NULL, usa _DEFAULT_TEMPLATE do cadence_manager.
    steps_template: Mapped[list[dict] | None] = mapped_column(
        JSONB,
        nullable=True,
        default=None,
        comment="Template de steps customizado (JSON). NULL = template padrão.",
    )

    # -------------------------------------------------------
    # Configuração TTS por cadência (opcional)
    # -------------------------------------------------------
    tts_provider: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        default=None,
        comment="Provedor TTS: speechify | voicebox. NULL = usa VOICE_PROVIDER global.",
    )
    tts_voice_id: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        default=None,
        comment="ID da voz/profile TTS. NULL = usa default do provider.",
    )

    # -------------------------------------------------------
    # Lista de leads associada (opcional)
    # -------------------------------------------------------
    lead_list_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("lead_lists.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
        comment="Lista de leads vinculada. NULL = sem lista.",
    )
