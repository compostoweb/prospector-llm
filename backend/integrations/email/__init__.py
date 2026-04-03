"""
integrations/email/__init__.py

EmailRegistry — único ponto de acesso para envio de e-mails.
Análogo ao LLMRegistry em integrations/llm/.

Uso (em services ou workers):
    from integrations.email import EmailRegistry, EmailSendResult
"""

from integrations.email.base import EmailProvider, EmailSendResult
from integrations.email.registry import EmailRegistry

__all__ = [
    "EmailRegistry",
    "EmailProvider",
    "EmailSendResult",
]
