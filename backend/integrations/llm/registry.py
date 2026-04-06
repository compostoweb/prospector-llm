"""
integrations/llm/registry.py

LLMRegistry: ponto central de acesso a todos os provedores.

Responsabilidades:
  - Instanciar e guardar providers (OpenAI, Gemini)
  - Agregar a lista de modelos disponíveis de todos os providers
  - Fazer cache dos modelos (TTL 1h no Redis)
  - Resolver qual provider usar dado um LLMConfig (provider + model_id)
  - Ser injetado via Depends() nas rotas e services

Uso:
    registry = LLMRegistry(settings)
    response = await registry.complete(config=cadence.llm_config, messages=[...])
    models = await registry.list_all_models()
"""

from __future__ import annotations

import json
from datetime import timedelta

import structlog

from core.config import Settings
from core.redis_client import RedisClient
from integrations.llm.anthropic_provider import AnthropicProvider
from integrations.llm.base import LLMMessage, LLMProvider, LLMResponse, ModelInfo
from integrations.llm.gemini_provider import GeminiProvider
from integrations.llm.openai_provider import OpenAIProvider

logger = structlog.get_logger()

_MODELS_CACHE_KEY = "llm:models:all"
_MODELS_CACHE_TTL = int(timedelta(hours=1).total_seconds())


class LLMRegistry:
    def __init__(self, settings: Settings, redis: RedisClient) -> None:
        self._redis = redis
        self._providers: dict[str, LLMProvider] = {}

        if settings.OPENAI_API_KEY:
            self._providers["openai"] = OpenAIProvider(api_key=settings.OPENAI_API_KEY)
            logger.info("llm.registry.provider_loaded", provider="openai")

        if settings.GEMINI_API_KEY:
            self._providers["gemini"] = GeminiProvider(api_key=settings.GEMINI_API_KEY)
            logger.info("llm.registry.provider_loaded", provider="gemini")

        if settings.ANTHROPIC_API_KEY:
            self._providers["anthropic"] = AnthropicProvider(api_key=settings.ANTHROPIC_API_KEY)
            logger.info("llm.registry.provider_loaded", provider="anthropic")

        if not self._providers:
            raise RuntimeError(
                "Nenhum provedor LLM configurado. "
                "Configure OPENAI_API_KEY, GEMINI_API_KEY ou ANTHROPIC_API_KEY."
            )

    # ------------------------------------------------------------------
    # Completions
    # ------------------------------------------------------------------

    async def complete(
        self,
        messages: list[LLMMessage],
        provider: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        json_mode: bool = False,
    ) -> LLMResponse:
        """
        Executa uma completion com o provider e modelo especificados.
        Levanta ValueError se o provider não estiver configurado.
        """
        llm = self._get_provider(provider)
        return await llm.complete(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=json_mode,
        )

    # ------------------------------------------------------------------
    # Listagem de modelos — com cache Redis 1h
    # ------------------------------------------------------------------

    async def list_all_models(self, force_refresh: bool = False) -> list[ModelInfo]:
        """
        Retorna todos os modelos disponíveis de todos os providers configurados.
        Usa Redis como cache com TTL de 1h para não chamar as APIs a cada request.
        Degrada gracefully se o Redis estiver indisponível.
        """
        if not force_refresh:
            try:
                cached = await self._redis.get(_MODELS_CACHE_KEY)
            except Exception as exc:
                logger.warning("llm.models.cache_read_error", error=str(exc))
                cached = None
            if cached:
                raw: list[dict] = json.loads(cached)
                return [ModelInfo(**item) for item in raw]

        all_models: list[ModelInfo] = []
        for provider_name, provider in self._providers.items():
            try:
                models = await provider.list_models()
                all_models.extend(models)
                logger.info("llm.models.fetched", provider=provider_name, count=len(models))
            except Exception as exc:
                logger.error("llm.models.fetch_error", provider=provider_name, error=str(exc))

        # Salva no cache
        cache_data = [
            {
                "id": m.id,
                "name": m.name,
                "provider": m.provider,
                "context_window": m.context_window,
                "supports_json_mode": m.supports_json_mode,
                "price_input_per_mtok": m.price_input_per_mtok,
                "price_output_per_mtok": m.price_output_per_mtok,
            }
            for m in all_models
        ]
        try:
            await self._redis.set(_MODELS_CACHE_KEY, json.dumps(cache_data), ex=_MODELS_CACHE_TTL)
        except Exception as exc:
            logger.warning("llm.models.cache_write_error", error=str(exc))

        return all_models

    async def list_models_by_provider(self, provider: str) -> list[ModelInfo]:
        all_models = await self.list_all_models()
        return [m for m in all_models if m.provider == provider]

    def available_providers(self) -> list[str]:
        return list(self._providers.keys())

    # ------------------------------------------------------------------
    # Geração de imagem
    # ------------------------------------------------------------------

    async def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "4:5",
        image_size: str = "1K",
    ) -> bytes:
        """
        Gera imagem via Gemini Nano Banana 2 (gemini-3.1-flash-image-preview).
        Levanta ValueError se Gemini não estiver configurado.
        """
        gemini = self._get_provider("gemini")
        return await gemini.generate_image(  # type: ignore[attr-defined]
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            image_size=image_size,
        )

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    def _get_provider(self, provider: str) -> LLMProvider:
        if provider not in self._providers:
            available = list(self._providers.keys())
            raise ValueError(f"Provedor '{provider}' não configurado. Disponíveis: {available}")
        return self._providers[provider]
