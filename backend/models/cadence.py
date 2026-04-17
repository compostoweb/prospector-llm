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

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
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
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        comment="Cadência ativa para execução real. Novas cadências nascem pausadas até ativação manual.",
    )
    allow_personal_email: Mapped[bool] = mapped_column(Boolean, default=False)

    # -------------------------------------------------------
    # Modo de execução
    # -------------------------------------------------------
    mode: Mapped[str] = mapped_column(
        String(50),
        default="automatic",
        server_default="automatic",
        comment="Modo: automatic | semi_manual",
    )

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
    # Contexto de prospecção (alimenta os prompts da IA)
    # -------------------------------------------------------
    target_segment: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
        default=None,
        comment="Segmento-alvo ex: 'SaaS B2B', 'indústria farmacêutica', 'varejo premium'.",
    )
    persona_description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
        comment="Descrição da persona ideal: cargo, dores, prioridades.",
    )
    offer_description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
        comment="O que a empresa oferece — proposta de valor resumida para a IA.",
    )
    tone_instructions: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
        comment="Instruções extras de tom/voz que o usuário queira injetar no prompt.",
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
    tts_speed: Mapped[float] = mapped_column(
        Float,
        default=1.0,
        server_default="1.0",
        comment="Velocidade da fala TTS (0.5–2.0). 1.0 = normal.",
    )
    tts_pitch: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        server_default="0",
        comment="Entonação/pitch TTS (-50 a +50%). 0 = normal.",
    )

    # -------------------------------------------------------
    # Tipo de cadência (cold email vs mixed)
    # -------------------------------------------------------
    cadence_type: Mapped[str] = mapped_column(
        String(50),
        default="mixed",
        server_default="mixed",
        comment="Tipo: mixed | email_only. email_only força todos os steps no canal EMAIL.",
    )

    # -------------------------------------------------------
    # Conta de e-mail preferencial para steps EMAIL
    # -------------------------------------------------------
    email_account_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("email_accounts.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
        comment="Conta de e-mail usada para envio (EmailAccount). NULL = usa Unipile global.",
    )

    # -------------------------------------------------------
    # Conta LinkedIn preferencial para steps LinkedIn
    # -------------------------------------------------------
    linkedin_account_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("linkedin_accounts.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
        comment="Conta LinkedIn usada nos steps (LinkedInAccount). NULL = usa Unipile global.",
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
