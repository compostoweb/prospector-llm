"""
integrations/llm/base.py

Contrato base para todos os provedores de LLM.
Cada provedor implementa esta interface — o restante do sistema
nunca importa OpenAI ou Gemini diretamente, só usa LLMProvider.
"""

import inspect
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMMessage:
    """Mensagem no formato agnóstico ao provedor."""

    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMResponse:
    """Resposta normalizada de qualquer provedor."""

    text: str
    model: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMUsageContext:
    """Contexto opcional para observabilidade e analytics de consumo."""

    tenant_id: str
    module: str
    task_type: str
    feature: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    secondary_entity_type: str | None = None
    secondary_entity_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelInfo:
    """Informações de um modelo disponível."""

    id: str
    name: str
    provider: str  # "openai" | "gemini" | "anthropic" | "openrouter"
    context_window: int = 0
    supports_json_mode: bool = True
    price_input_per_mtok: float = 0.0  # USD por 1M tokens de input
    price_output_per_mtok: float = 0.0  # USD por 1M tokens de output
    price_is_estimated: bool = True  # Preços são aproximados — conferir site do provider
    pricing_tag: str = ""  # "free" | "paid" | "" (vazio = sem tag)


class LLMNonRetryableError(Exception):
    """Erro permanente de LLM que não deve ser retentado (billing, auth, config)."""

    pass


class LLMProvider(ABC):
    """Interface base para provedores de LLM."""

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @abstractmethod
    async def complete(
        self,
        messages: list[LLMMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        json_mode: bool = False,
    ) -> LLMResponse: ...

    @abstractmethod
    async def list_models(self) -> list[ModelInfo]: ...

    async def aclose(self) -> None:
        """Fecha recursos assíncronos do provider quando existirem."""
        return None


async def close_async_resource(resource: object | None) -> None:
    """Fecha um recurso que exponha close/aclose síncrono ou assíncrono."""
    if resource is None:
        return

    for method_name in ("aclose", "close"):
        method = getattr(resource, method_name, None)
        if not callable(method):
            continue

        result = method()
        if inspect.isawaitable(result):
            await result
        return
