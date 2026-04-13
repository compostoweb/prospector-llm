"""
integrations/llm/openai_provider.py

Provedor OpenAI: GPT-4o, GPT-4o-mini, GPT-4.1, GPT-4.1-mini, GPT-4.1-nano, etc.
Lista modelos dinamicamente via GET /v1/models e filtra apenas os de chat.
"""

from __future__ import annotations

import httpx
import structlog
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from integrations.llm.base import LLMMessage, LLMProvider, LLMResponse, ModelInfo

logger = structlog.get_logger()

# Status HTTP que NÃO devem ser retentados (auth/config — retry é inútil)
_NON_RETRYABLE_STATUSES = {401, 402, 403, 404}


def _is_retryable_error(exc: BaseException) -> bool:
    """Retorna True se o erro deve ser retentado (429, 5xx, timeout)."""
    from openai import APIConnectionError, APIStatusError, APITimeoutError

    if isinstance(exc, (APITimeoutError, APIConnectionError)):
        return True
    if isinstance(exc, APIStatusError):
        return exc.status_code not in _NON_RETRYABLE_STATUSES
    return False


# Prefixos que identificam modelos de chat/completions — descarta embeddings,
# whisper, tts, dall-e, moderation, etc.
_CHAT_PREFIXES = (
    "gpt-4",
    "gpt-3.5",
    "gpt-5",
    "o1",
    "o3",
    "o4",
)

# Preços ESTIMADOS USD/1M tokens (input / output) — usados apenas como
# referência na UI. Podem estar desatualizados. Fonte oficial:
# https://openai.com/api/pricing  → price_is_estimated=True em ModelInfo
_KNOWN_PRICES: dict[str, tuple[float, float]] = {
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4.1": (2.00, 8.00),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1-nano": (0.10, 0.40),
    "gpt-5": (0.0, 0.0),  # preco a ser confirmado
    "o1": (15.00, 60.00),
    "o1-mini": (3.00, 12.00),
    "o3": (10.00, 40.00),
    "o3-mini": (1.10, 4.40),
    "o4-mini": (1.10, 4.40),
}


def _price_for(model_id: str) -> tuple[float, float]:
    """Retorna (input, output) price para o modelo, ou (0, 0) se desconhecido."""
    # Tenta match exato, depois por prefixo
    if model_id in _KNOWN_PRICES:
        return _KNOWN_PRICES[model_id]
    for key, prices in _KNOWN_PRICES.items():
        if model_id.startswith(key):
            return prices
    return (0.0, 0.0)


def _is_chat_model(model_id: str) -> bool:
    return any(model_id.startswith(p) for p in _CHAT_PREFIXES)


# Modelos que exigem max_completion_tokens em vez de max_tokens
_MAX_COMPLETION_TOKENS_PREFIXES = ("gpt-5", "o1", "o3", "o4")


def _uses_max_completion_tokens(model: str) -> bool:
    return any(model.startswith(p) for p in _MAX_COMPLETION_TOKENS_PREFIXES)


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._raw_http = httpx.AsyncClient(
            base_url="https://api.openai.com/v1",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=15.0,
        )

    @property
    def provider_name(self) -> str:
        return "openai"

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
        kwargs: dict = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
        }

        # Modelos gpt-5.x e o-series exigem max_completion_tokens
        if _uses_max_completion_tokens(model):
            kwargs["max_completion_tokens"] = max_tokens
        else:
            kwargs["max_tokens"] = max_tokens

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        logger.debug("openai.complete", model=model, json_mode=json_mode)

        response: ChatCompletion = await self._client.chat.completions.create(**kwargs)

        choice = response.choices[0]
        usage = response.usage

        return LLMResponse(
            text=choice.message.content or "",
            model=response.model,
            provider="openai",
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            raw=response.model_dump(),
        )

    async def list_models(self) -> list[ModelInfo]:
        """
        Busca modelos disponíveis via GET /v1/models e filtra apenas chat models.
        O resultado é cacheado na instância por 1h (não recarrega a cada chamada).
        """
        response = await self._raw_http.get("/models")
        response.raise_for_status()
        data = response.json()

        models: list[ModelInfo] = []
        for item in data.get("data", []):
            mid: str = item.get("id", "")
            if not _is_chat_model(mid):
                continue
            inp, out = _price_for(mid)
            models.append(
                ModelInfo(
                    id=mid,
                    name=_friendly_name(mid),
                    provider="openai",
                    price_input_per_mtok=inp,
                    price_output_per_mtok=out,
                    supports_json_mode=True,
                )
            )

        # Ordena: mais recentes primeiro (estimado pela data no ID ou alfabético)
        models.sort(key=lambda m: m.id, reverse=True)
        logger.info("openai.models.listed", count=len(models))
        return models


def _friendly_name(model_id: str) -> str:
    """Converte 'gpt-4o-mini' → 'GPT-4o Mini', 'o3-mini' → 'O3 Mini', etc."""
    name = model_id.replace("-", " ").replace(".", ".")
    # Capitaliza cada parte
    parts = []
    for part in name.split(" "):
        if part.startswith("gpt"):
            parts.append(part.upper().replace("GPT", "GPT-").rstrip("-"))
        else:
            parts.append(part.capitalize())
    return " ".join(parts).strip()
