"""
integrations/llm/anthropic_provider.py

Provedor Anthropic Claude usando o SDK oficial: anthropic >= 0.89.0

Suporta:
  - Claude Opus 4.6    (claude-opus-4-6)    ← máxima inteligência, agentes
  - Claude Sonnet 4.6  (claude-sonnet-4-6)  ← recomendado: qualidade/velocidade
  - Claude Haiku 4.5   (claude-haiku-4-5)   ← mais rápido, custo menor
  - Claude Haiku 3     (claude-haiku-3)     ← mais barato
  - Outros modelos ativos listados via GET /v1/models

Lista modelos dinamicamente via client.models.list() + filtra apenas claude-* chat models.

Nota sobre Batch API (50% de desconto):
  Usar AnthropicBatchService em services/anthropic_batch_service.py
  A Batch API é assíncrona (até 24h) — não usar para completions em tempo real.
"""

from __future__ import annotations

import structlog
from anthropic import AsyncAnthropic
from anthropic.types import Message, TextBlock
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from integrations.llm.base import LLMMessage, LLMProvider, LLMResponse, ModelInfo

logger = structlog.get_logger()

# Status HTTP que NÃO devem ser retentados (auth/config — retry é inútil)
_NON_RETRYABLE_STATUSES = {400, 401, 402, 403, 404}


def _is_retryable_error(exc: BaseException) -> bool:
    """Retorna True se o erro deve ser retentado (429, 5xx, timeout)."""
    # Anthropic SDK lança APIStatusError com status_code
    from anthropic import APIConnectionError, APIStatusError, APITimeoutError

    if isinstance(exc, (APITimeoutError, APIConnectionError)):
        return True
    if isinstance(exc, APIStatusError):
        return exc.status_code not in _NON_RETRYABLE_STATUSES
    return False


# Preços ESTIMADOS USD/1M tokens (input / output) — podem estar desatualizados.
# Fonte oficial: https://platform.claude.com/docs/en/about-claude/models/overview
# → price_is_estimated=True em ModelInfo
# Batch API = 50% desses valores.
_ANTHROPIC_PRICES: dict[str, tuple[float, float]] = {
    "claude-opus-4-6": (5.00, 25.00),
    "claude-opus-4-5": (5.00, 25.00),
    "claude-opus-4-1": (15.00, 75.00),
    "claude-opus-4": (15.00, 75.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-sonnet-4-5": (3.00, 15.00),
    "claude-sonnet-4": (3.00, 15.00),
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-haiku-3-5": (0.80, 4.00),
    "claude-haiku-3": (0.25, 1.25),
    "claude-opus-3": (15.00, 75.00),
}

# Padrões de IDs que NÃO são modelos de chat — filtrar da listagem
_EXCLUDED_PATTERNS = (
    "embed",
    "moderat",
)


def _is_chat_model(model_id: str) -> bool:
    model_lower = model_id.lower()
    if not model_lower.startswith("claude-"):
        return False
    return not any(p in model_lower for p in _EXCLUDED_PATTERNS)


def _price_for(model_id: str) -> tuple[float, float]:
    """Retorna (input, output) USD/MTok para o modelo, ou (0, 0) se desconhecido."""
    if model_id in _ANTHROPIC_PRICES:
        return _ANTHROPIC_PRICES[model_id]
    for key, prices in _ANTHROPIC_PRICES.items():
        if model_id.startswith(key):
            return prices
    return (0.0, 0.0)


def _friendly_name(model_id: str) -> str:
    """
    'claude-opus-4-6' → 'Claude Opus 4.6'
    'claude-haiku-3'  → 'Claude Haiku 3'
    """
    # Remove prefixo
    name = model_id.replace("claude-", "Claude ")
    parts = name.split("-")
    formatted: list[str] = []
    for p in parts:
        if p.isdigit():
            # versão inteira — juntar com ponto ao token anterior se possível
            if formatted and formatted[-1][-1].isdigit():
                formatted[-1] = formatted[-1] + "." + p
            else:
                formatted.append(p)
        else:
            formatted.append(p.capitalize())
    return " ".join(formatted)


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str) -> None:
        self._client = AsyncAnthropic(api_key=api_key)

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=10),
        retry=retry_if_exception(_is_retryable_error),
        reraise=True,
    )
    async def complete(
        self,
        messages: list[LLMMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        json_mode: bool = False,
    ) -> LLMResponse:
        """
        Executa completion via Anthropic Messages API.

        Separa o system prompt (role='system') da lista de mensagens —
        Anthropic exige que system seja passado como parâmetro separado.

        json_mode: injeta instrução no system prompt pedindo JSON puro,
        pois a API da Anthropic não tem um parâmetro nativo de JSON mode
        equivalente ao OpenAI (response_format).
        """
        system_parts: list[str] = []
        chat_messages: list[dict] = []

        for msg in messages:
            if msg.role == "system":
                system_parts.append(msg.content)
            else:
                chat_messages.append({"role": msg.role, "content": msg.content})

        system_text = "\n\n".join(system_parts) if system_parts else None

        if json_mode:
            json_instruction = (
                "Responda EXCLUSIVAMENTE com JSON válido. Sem texto antes ou depois. Sem markdown."
            )
            system_text = (
                f"{system_text}\n\n{json_instruction}" if system_text else json_instruction
            )

        kwargs: dict = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": chat_messages,
        }
        if system_text:
            kwargs["system"] = system_text

        logger.debug("anthropic.complete", model=model, json_mode=json_mode)

        response: Message = await self._client.messages.create(**kwargs)

        text = ""
        for block in response.content:
            if isinstance(block, TextBlock):
                text += block.text

        usage = response.usage

        return LLMResponse(
            text=text,
            model=response.model,
            provider="anthropic",
            input_tokens=usage.input_tokens if usage else 0,
            output_tokens=usage.output_tokens if usage else 0,
            raw=response.model_dump(),
        )

    async def list_models(self) -> list[ModelInfo]:
        """
        Lista modelos disponíveis via Anthropic Models API.
        Filtra apenas modelos de chat (claude-*).
        """
        models: list[ModelInfo] = []

        # SDK síncrono paginado — iteramos a resposta
        response = await self._client.models.list(limit=100)

        for model in response.data:
            mid: str = model.id
            if not _is_chat_model(mid):
                continue

            inp, out = _price_for(mid)
            models.append(
                ModelInfo(
                    id=mid,
                    name=_friendly_name(mid),
                    provider="anthropic",
                    context_window=getattr(model, "context_window", 0) or 0,
                    supports_json_mode=True,  # via instrução no system prompt
                    price_input_per_mtok=inp,
                    price_output_per_mtok=out,
                    price_is_estimated=True,
                )
            )

        models.sort(key=lambda m: m.id, reverse=True)
        logger.info("anthropic.models.listed", count=len(models))
        return models
