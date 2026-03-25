"""
integrations/tts/registry.py

TTSRegistry: ponto central de acesso a todos os provedores de TTS.

Responsabilidades:
  - Instanciar e guardar providers (Speechify, Voicebox)
  - Agregar a lista de vozes disponíveis de todos os providers
  - Fazer cache das vozes (TTL 1h no Redis)
  - Resolver qual provider usar dado o nome
  - Ser injetado via Depends() nas rotas e workers

Uso:
    registry = TTSRegistry(settings=settings, redis=redis_client)
    audio = await registry.synthesize("speechify", "henry", "Olá mundo")
    voices = await registry.list_all_voices()
"""

from __future__ import annotations

import json
from datetime import timedelta

import structlog

from core.config import Settings
from core.redis_client import RedisClient
from integrations.tts.base import TTSProvider, TTSVoice

logger = structlog.get_logger()

_VOICES_CACHE_KEY = "tts:voices:all"
_VOICES_CACHE_TTL = int(timedelta(hours=1).total_seconds())


class TTSRegistry:

    def __init__(self, settings: Settings, redis: RedisClient) -> None:
        self._redis = redis
        self._providers: dict[str, TTSProvider] = {}

        if settings.SPEECHIFY_API_KEY:
            from integrations.tts.speechify_provider import SpeechifyProvider
            self._providers["speechify"] = SpeechifyProvider(
                api_key=settings.SPEECHIFY_API_KEY,
                default_voice_id=settings.SPEECHIFY_VOICE_ID,
            )
            logger.info("tts.registry.provider_loaded", provider="speechify")

        if settings.VOICEBOX_ENABLED:
            from integrations.tts.voicebox_provider import VoiceboxProvider
            self._providers["voicebox"] = VoiceboxProvider(
                base_url=settings.VOICEBOX_BASE_URL,
            )
            logger.info("tts.registry.provider_loaded", provider="voicebox")

        if settings.EDGE_TTS_ENABLED:
            from integrations.tts.edge_provider import EdgeTTSProvider
            self._providers["edge"] = EdgeTTSProvider(
                default_voice_id=settings.EDGE_TTS_DEFAULT_VOICE,
            )
            logger.info("tts.registry.provider_loaded", provider="edge")

        if not self._providers:
            logger.warning("tts.registry.no_providers", msg="Nenhum provedor TTS configurado.")

    # ------------------------------------------------------------------
    # Síntese
    # ------------------------------------------------------------------

    async def synthesize(
        self,
        provider: str,
        voice_id: str,
        text: str,
        language: str = "pt-BR",
        speed: float = 1.0,
        pitch: float = 0.0,
    ) -> bytes:
        """Sintetiza áudio com o provider e voz especificados."""
        tts = self._get_provider(provider)
        return await tts.synthesize(text=text, voice_id=voice_id, language=language, speed=speed, pitch=pitch)

    # ------------------------------------------------------------------
    # Listagem de vozes — com cache Redis 1h
    # ------------------------------------------------------------------

    async def list_all_voices(self, force_refresh: bool = False) -> list[TTSVoice]:
        """
        Retorna todas as vozes de todos os providers configurados.
        Cache Redis com TTL de 1h. Degrada gracefully se Redis indisponível.
        """
        if not force_refresh:
            try:
                cached = await self._redis.get(_VOICES_CACHE_KEY)
            except Exception as exc:
                logger.warning("tts.voices.cache_read_error", error=str(exc))
                cached = None
            if cached:
                raw: list[dict] = json.loads(cached)
                return [TTSVoice(**item) for item in raw]

        all_voices: list[TTSVoice] = []
        for provider_name, provider in self._providers.items():
            try:
                voices = await provider.list_voices()
                all_voices.extend(voices)
                logger.info("tts.voices.fetched", provider=provider_name, count=len(voices))
            except Exception as exc:
                logger.error("tts.voices.fetch_error", provider=provider_name, error=str(exc))

        # Salva no cache
        cache_data = [
            {
                "id": v.id,
                "name": v.name,
                "language": v.language,
                "provider": v.provider,
                "is_cloned": v.is_cloned,
            }
            for v in all_voices
        ]
        try:
            await self._redis.set(_VOICES_CACHE_KEY, json.dumps(cache_data), ex=_VOICES_CACHE_TTL)
        except Exception as exc:
            logger.warning("tts.voices.cache_write_error", error=str(exc))

        return all_voices

    async def list_voices_by_provider(self, provider: str) -> list[TTSVoice]:
        all_voices = await self.list_all_voices()
        return [v for v in all_voices if v.provider == provider]

    # ------------------------------------------------------------------
    # Voice cloning
    # ------------------------------------------------------------------

    async def create_voice(
        self,
        provider: str,
        name: str,
        audio_data: bytes,
        language: str = "pt-BR",
    ) -> TTSVoice:
        """Cria voice clone no provider especificado. Invalida cache."""
        tts = self._get_provider(provider)
        voice = await tts.create_voice(name=name, audio_data=audio_data, language=language)
        await self._invalidate_cache()
        return voice

    async def delete_voice(self, provider: str, voice_id: str) -> None:
        """Deleta voz clonada no provider especificado. Invalida cache."""
        tts = self._get_provider(provider)
        await tts.delete_voice(voice_id)
        await self._invalidate_cache()

    # ------------------------------------------------------------------
    # Providers
    # ------------------------------------------------------------------

    def available_providers(self) -> list[str]:
        return list(self._providers.keys())

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    def _get_provider(self, provider: str) -> TTSProvider:
        if provider not in self._providers:
            available = list(self._providers.keys())
            raise ValueError(
                f"Provedor TTS '{provider}' não configurado. "
                f"Disponíveis: {available}"
            )
        return self._providers[provider]

    async def _invalidate_cache(self) -> None:
        """Remove cache de vozes para forçar refresh na próxima listagem."""
        try:
            await self._redis.delete(_VOICES_CACHE_KEY)
        except Exception as exc:
            logger.warning("tts.voices.cache_invalidate_error", error=str(exc))
