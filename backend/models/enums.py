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
