"""
integrations/llm/__init__.py

Exports públicos do módulo LLM.
O restante do sistema só importa daqui — nunca diretamente de openai_provider ou gemini_provider.
"""

from integrations.llm.base import LLMMessage, LLMProvider, LLMResponse, LLMUsageContext, ModelInfo
from integrations.llm.registry import LLMRegistry

__all__ = [
    "LLMMessage",
    "LLMProvider",
    "LLMResponse",
    "LLMUsageContext",
    "ModelInfo",
    "LLMRegistry",
]
