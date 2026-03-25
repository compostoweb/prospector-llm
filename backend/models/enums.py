"""
models/enums.py

Enums centralizados do sistema Prospector.

Todos os enums são definidos aqui para evitar duplicação entre models e schemas.
São importados pelos models SQLAlchemy e pelos schemas Pydantic.
"""

from __future__ import annotations

from enum import Enum


class Channel(str, Enum):
    """Canais de comunicação disponíveis."""
    LINKEDIN_CONNECT = "linkedin_connect"
    LINKEDIN_DM = "linkedin_dm"
    EMAIL = "email"
    MANUAL_TASK = "manual_task"


class LeadSource(str, Enum):
    """Origem do lead no sistema."""
    MANUAL = "manual"
    APIFY_MAPS = "apify_maps"
    APIFY_LINKEDIN = "apify_linkedin"
    IMPORT = "import"
    API = "api"


class LeadStatus(str, Enum):
    """Status do lead na jornada de prospecção."""
    RAW = "raw"
    ENRICHED = "enriched"
    IN_CADENCE = "in_cadence"
    CONVERTED = "converted"
    ARCHIVED = "archived"


class StepStatus(str, Enum):
    """Status de execução de um step da cadência."""
    PENDING = "pending"
    SENT = "sent"
    REPLIED = "replied"
    SKIPPED = "skipped"
    FAILED = "failed"


class Intent(str, Enum):
    """Intenção detectada em uma resposta inbound."""
    INTEREST = "interest"
    OBJECTION = "objection"
    NOT_INTERESTED = "not_interested"
    NEUTRAL = "neutral"
    OUT_OF_OFFICE = "out_of_office"


class EmailType(str, Enum):
    """Tipo de endereço de email."""
    CORPORATE = "corporate"
    PERSONAL = "personal"
    UNKNOWN = "unknown"


class InteractionDirection(str, Enum):
    """Direção da mensagem na interação."""
    OUTBOUND = "outbound"
    INBOUND = "inbound"


class StepType(str, Enum):
    """Tipo de instrução para geração de conteúdo do step."""
    LINKEDIN_CONNECT = "linkedin_connect"
    LINKEDIN_DM_FIRST = "linkedin_dm_first"
    LINKEDIN_DM_POST_CONNECT = "linkedin_dm_post_connect"
    LINKEDIN_DM_POST_CONNECT_VOICE = "linkedin_dm_post_connect_voice"
    LINKEDIN_DM_VOICE = "linkedin_dm_voice"
    LINKEDIN_DM_FOLLOWUP = "linkedin_dm_followup"
    LINKEDIN_DM_BREAKUP = "linkedin_dm_breakup"
    EMAIL_FIRST = "email_first"
    EMAIL_FOLLOWUP = "email_followup"
    EMAIL_BREAKUP = "email_breakup"


class SandboxRunStatus(str, Enum):
    """Status de um sandbox run de cadência."""
    RUNNING = "running"
    COMPLETED = "completed"
    APPROVED = "approved"
    REJECTED = "rejected"


class SandboxStepStatus(str, Enum):
    """Status de um step dentro do sandbox."""
    PENDING = "pending"
    GENERATING = "generating"
    GENERATED = "generated"
    APPROVED = "approved"
    REJECTED = "rejected"


class SandboxLeadSource(str, Enum):
    """Origem dos leads usados no sandbox."""
    REAL = "real"
    SAMPLE = "sample"
    FICTITIOUS = "fictitious"
