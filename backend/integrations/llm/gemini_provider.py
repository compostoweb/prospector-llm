"""
integrations/llm/gemini_provider.py

Provedor Google Gemini usando o SDK oficial GA: google-genai >= 1.0.0
(O pacote google-generativeai foi descontinuado em novembro/2025 — não usar)

Suporta:
  - Gemini 2.5 Pro      (gemini-2.5-pro)
  - Gemini 2.5 Flash    (gemini-2.5-flash)       ← recomendado: custo/qualidade
  - Gemini 2.5 Flash-Lite (gemini-2.5-flash-lite) ← mais barato
  - Gemini 3 Flash      (gemini-3-flash) [preview]
  - Gemini 3.1 Pro      (gemini-3.1-pro-preview) [preview]

Lista modelos dinamicamente via client.models.list() + filtra apenas chat models.
"""

from __future__ import annotations

import structlog
from google import genai
from google.genai import types
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from integrations.llm.base import LLMMessage, LLMProvider, LLMResponse, ModelInfo

logger = structlog.get_logger()

# Status HTTP que NÃO devem ser retentados (auth/config — retry é inútil)
_NON_RETRYABLE_STATUSES = {401, 402, 403, 404}


def _is_retryable_error(exc: BaseException) -> bool:
    """Retorna True se o erro deve ser retentado (429, 5xx, timeout)."""
    from google.api_core.exceptions import GoogleAPIError

    # google-genai levanta ClientError / ServerError que herdam GoogleAPIError
    if isinstance(exc, GoogleAPIError):
        code = getattr(exc, "code", None) or getattr(exc, "grpc_status_code", None)
        if code and int(code) in _NON_RETRYABLE_STATUSES:
            return False
        return True
    # Timeout / connection errors — sempre retentável
    if isinstance(exc, (TimeoutError, ConnectionError, OSError)):
        return True
    return False


# Preços ESTIMADOS USD/1M tokens (input / output) — podem estar desatualizados.
# Fonte oficial: https://ai.google.dev/gemini-api/docs/pricing
# → price_is_estimated=True em ModelInfo
_GEMINI_PRICES: dict[str, tuple[float, float]] = {
    "gemini-2.5-pro": (1.25, 10.00),  # até 200k tokens; acima 2.50/15.00
    "gemini-2.5-flash": (0.30, 2.50),  # com thinking; sem: 0.15/0.60
    "gemini-2.5-flash-lite": (0.10, 0.40),
    "gemini-2.0-flash": (0.10, 0.40),
    "gemini-3-flash": (0.15, 0.60),  # preview — sujeito a alteração
    "gemini-3.1-pro": (1.25, 10.00),  # preview
    "gemini-3.1-flash": (0.15, 0.60),  # preview
}

# Modelos que NÃO são de chat/text generation — filtrar da lista
_EXCLUDED_PATTERNS = (
    "embedding",
    "imagen",
    "veo",
    "tts",
    "audio",
    "aqa",
    "code-gecko",
    "text-bison",
    "chat-bison",
)


def _is_chat_model(model_name: str) -> bool:
    name_lower = model_name.lower()
    if not name_lower.startswith("models/gemini"):
        return False
    return not any(p in name_lower for p in _EXCLUDED_PATTERNS)


def _strip_prefix(name: str) -> str:
    """'models/gemini-2.5-flash' → 'gemini-2.5-flash'"""
    return name.replace("models/", "")


def _price_for(model_id: str) -> tuple[float, float]:
    if model_id in _GEMINI_PRICES:
        return _GEMINI_PRICES[model_id]
    for key, prices in _GEMINI_PRICES.items():
        if model_id.startswith(key):
            return prices
    return (0.0, 0.0)


def _friendly_name(model_id: str) -> str:
    """'gemini-2.5-flash' → 'Gemini 2.5 Flash'"""
    return model_id.replace("gemini-", "Gemini ").replace("-", " ").title()


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str) -> None:
        # google-genai SDK GA — usa GEMINI_API_KEY diretamente
        self._client = genai.Client(api_key=api_key)

    @property
    def provider_name(self) -> str:
        return "gemini"

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
        Converte LLMMessage[] para o formato Gemini.
        Extrai system prompt do primeiro message se role='system'.
        """
        system_instruction: str | None = None
        contents: list[types.Content] = []

        for msg in messages:
            if msg.role == "system":
                # Gemini usa system_instruction separado, não no contents
                system_instruction = msg.content
                continue
            role = "user" if msg.role == "user" else "model"
            contents.append(types.Content(role=role, parts=[types.Part(text=msg.content)]))

        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=system_instruction,
        )

        if json_mode:
            # Gemini suporta JSON mode via response_mime_type
            config.response_mime_type = "application/json"

        logger.debug("gemini.complete", model=model, json_mode=json_mode)

        response = await self._client.aio.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )

        text = response.text or ""
        usage = response.usage_metadata

        return LLMResponse(
            text=text,
            model=model,
            provider="gemini",
            input_tokens=usage.prompt_token_count if usage else 0,
            output_tokens=usage.candidates_token_count if usage else 0,
            raw={"candidates": [c.model_dump() for c in response.candidates]},
        )

    async def list_models(self) -> list[ModelInfo]:
        """
        Lista modelos disponíveis via google-genai SDK.
        Filtra apenas modelos de geração de texto (chat).
        """
        models: list[ModelInfo] = []

        # SDK síncrono — wrap em asyncio se necessário
        # client.models.list() retorna iterador paginado
        for model in self._client.models.list():
            name: str = model.name  # ex: "models/gemini-2.5-flash"
            if not _is_chat_model(name):
                continue

            model_id = _strip_prefix(name)
            inp, out = _price_for(model_id)

            models.append(
                ModelInfo(
                    id=model_id,
                    name=_friendly_name(model_id),
                    provider="gemini",
                    context_window=getattr(model, "input_token_limit", 0) or 0,
                    supports_json_mode=True,
                    price_input_per_mtok=inp,
                    price_output_per_mtok=out,
                )
            )

        models.sort(key=lambda m: m.id, reverse=True)
        logger.info("gemini.models.listed", count=len(models))
        return models

    async def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "4:5",
        image_size: str = "1K",
    ) -> bytes:
        """
        Gera uma imagem via Nano Banana 2 (gemini-3.1-flash-image-preview).

        Retorna os bytes raw da imagem PNG.
        aspect_ratio: '4:5' | '1:1' | '16:9'
        image_size: '512' | '1K' | '2K' | '4K'
        """
        logger.debug("gemini.generate_image", aspect_ratio=aspect_ratio, image_size=image_size)

        response = await self._client.aio.models.generate_content(
            model="gemini-3.1-flash-image-preview",
            contents=[prompt],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(
                    aspect_ratio=aspect_ratio,
                    image_size=image_size,
                ),
            ),
        )

        # O modelo 3.1 Flash Image usa Thinking por padrão — thoughts são ocultos
        # por padrão (includeThoughts=False). Partes com inline_data sem thought=True
        # são as imagens finais geradas.
        # NOTA: inline_data.data já é bytes puro (SDK decodifica base64 automaticamente).
        parts = response.parts or []
        image_bytes: bytes | None = None
        text_parts: list[str] = []
        for part in parts:
            if part.text:
                text_parts.append(part.text)
            elif part.inline_data and part.inline_data.data and not getattr(part, "thought", False):
                image_bytes = bytes(part.inline_data.data)

        if image_bytes is None:
            detail = "; ".join(text_parts) if text_parts else "resposta vazia"
            logger.warning(
                "gemini.image_no_data",
                response_text=detail[:500],
                parts_count=len(parts),
            )
            raise ValueError(f"Gemini nao retornou imagem na resposta: {detail[:200]}")

        logger.info("gemini.image_generated", size_bytes=len(image_bytes))
        return image_bytes
