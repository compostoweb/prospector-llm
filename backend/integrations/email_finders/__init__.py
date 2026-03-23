"""
integrations/email_finders/__init__.py

Pacote de finders de e-mail.

Exporta:
  - EmailFinderResult — resultado padronizado de qualquer finder
  - ProspeoClient, HunterClient, ApolloClient — clientes individuais
"""

from __future__ import annotations

from dataclasses import dataclass

from integrations.email_finders.apollo import ApolloClient
from integrations.email_finders.hunter import HunterClient
from integrations.email_finders.prospeo import ProspeoClient

__all__ = [
    "EmailFinderResult",
    "ProspeoClient",
    "HunterClient",
    "ApolloClient",
]


@dataclass
class EmailFinderResult:
    """Resultado padronizado de qualquer finder de e-mail."""
    email: str
    source: str                 # "prospeo" | "hunter" | "apollo"
    confidence: float           # 0.0 – 1.0
    first_name: str | None = None
    last_name: str | None = None
    domain: str | None = None
