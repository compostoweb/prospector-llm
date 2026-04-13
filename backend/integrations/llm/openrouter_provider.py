"""
integrations/llm/openrouter_provider.py

Provedor OpenRouter: acesso a centenas de modelos via API OpenAI-compatible.
Modelos gratuitos e pagos — preços consultados dinamicamente via GET /api/v1/models.

API: https://openrouter.ai/api/v1  (OpenAI-compatible)
Auth: Bearer token via header Authorization
"""

from __future__ import annotations

import httpx
import structlog
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from integrations.llm.base import LLMMessage, LLMProvider, LLMResponse, ModelInfo

logger = structlog.get_logger()

_BASE_URL = "https://openrouter.ai/api/v1"

# Status HTTP que NÃO devem ser retentados
_NON_RETRYABLE_STATUSES = {400, 401, 402, 403, 404}

# Prefixos de modelos que não são de chat (filtrar)
_EXCLUDE_PREFIXES = (
    "openrouter/",  # modelos meta/router do próprio OpenRouter
)

# Modelos que exigem max_completion_tokens
_MAX_COMPLETION_TOKENS_PREFIXES = ("openai/gpt-5", "openai/o1", "openai/o3", "openai/o4")


def _is_retryable_error(exc: BaseException) -> bool:
    """Retorna True se o erro deve ser retentado (429, 5xx, timeout)."""
    from openai import APIConnectionError, APIStatusError, APITimeoutError

    if isinstance(exc, (APITimeoutError, APIConnectionError)):
        return True
    if isinstance(exc, APIStatusError):
        return exc.status_code not in _NON_RETRYABLE_STATUSES
    return False


def _uses_max_completion_tokens(model: str) -> bool:
    return any(model.startswith(p) for p in _MAX_COMPLETION_TOKENS_PREFIXES)


def _is_free(pricing: dict[str, str] | None) -> bool:
    """Verifica se o modelo é gratuito com base no pricing."""
    if not pricing:
        return False
    prompt = pricing.get("prompt", "1")
    completion = pricing.get("completion", "1")
    try:
        return float(prompt) == 0.0 and float(completion) == 0.0
    except (ValueError, TypeError):
        return False


class OpenRouterProvider(LLMProvider):
    def __init__(self, api_key: str) -> None:
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=_BASE_URL,
            default_headers={
                "HTTP-Referer": "https://compostoweb.com.br",
                "X-OpenRouter-Title": "Prospector LLM",
            },
        )
        self._raw_http = httpx.AsyncClient(
            base_url=_BASE_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://compostoweb.com.br",
                "X-OpenRouter-Title": "Prospector LLM",
            },
            timeout=30.0,
        )

    @property
    def provider_name(self) -> str:
        return "openrouter"

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

        if _uses_max_completion_tokens(model):
            kwargs["max_completion_tokens"] = max_tokens
        else:
            kwargs["max_tokens"] = max_tokens

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        logger.debug("openrouter.complete", model=model, json_mode=json_mode)

        response: ChatCompletion = await self._client.chat.completions.create(**kwargs)

        choice = response.choices[0]
        usage = response.usage

        return LLMResponse(
            text=choice.message.content or "",
            model=response.model or model,
            provider="openrouter",
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            raw=response.model_dump(),
        )

    async def list_models(self) -> list[ModelInfo]:
        """
        Busca modelos do OpenRouter via GET /api/v1/models.
        Filtra apenas text output. Ordena: gratuitos primeiro, depois por preço.
        """
        response = await self._raw_http.get("/models")
        response.raise_for_status()
        data = response.json()

        models: list[ModelInfo] = []
        for item in data.get("data", []):
            mid: str = item.get("id", "")

            # Filtra modelos meta do router
            if any(mid.startswith(p) for p in _EXCLUDE_PREFIXES):
                continue

            # Filtra por modality: só text output
            arch = item.get("architecture") or {}
            output_mods = arch.get("output_modalities") or []
            if "text" not in output_mods:
                continue

            pricing = item.get("pricing") or {}
            free = _is_free(pricing)

            # Preço por token → preço por 1M tokens
            prompt_per_tok = _safe_float(pricing.get("prompt", "0"))
            completion_per_tok = _safe_float(pricing.get("completion", "0"))
            price_in = prompt_per_tok * 1_000_000
            price_out = completion_per_tok * 1_000_000

            name = item.get("name", mid)
            display_name = f"{'🆓 ' if free else ''}{name}"

            models.append(
                ModelInfo(
                    id=mid,
                    name=display_name,
                    provider="openrouter",
                    context_window=item.get("context_length", 0) or 0,
                    supports_json_mode="response_format"
                    in (item.get("supported_parameters") or []),
                    price_input_per_mtok=round(price_in, 4),
                    price_output_per_mtok=round(price_out, 4),
                    price_is_estimated=False,  # OpenRouter fornece preços exatos
                    pricing_tag="free" if free else "paid",
                )
            )

        # Ordena: gratuitos primeiro, depois por preço de input crescente
        models.sort(key=lambda m: (m.price_input_per_mtok > 0, m.price_input_per_mtok, m.id))
        logger.info("openrouter.models.listed", count=len(models))
        return models


def _safe_float(value: str | float | int | None) -> float:
    """Converte valor para float seguro."""
    if value is None:
        return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0
