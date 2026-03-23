"""
integrations/tts/voicebox_provider.py

Provider TTS para Voicebox — plataforma self-hosted de TTS + voice cloning.
Roda em Docker na mesma VPS (CPU-only).

API ref: http://localhost:17493
  POST   /generate            → sintetiza áudio
  GET    /profiles            → lista perfis de voz
  POST   /profiles            → cria voice clone
  DELETE /profiles/{id}       → deleta perfil

Imagem Docker: ghcr.io/jamiepine/voicebox:latest
"""

from __future__ import annotations

import httpx
import structlog

from integrations.tts.base import TTSProvider, TTSVoice

logger = structlog.get_logger()

_TIMEOUT = 120.0  # Voice synthesis no CPU pode ser lento


class VoiceboxProvider(TTSProvider):

    def __init__(self, base_url: str = "http://localhost:17493") -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=_TIMEOUT,
        )

    @property
    def provider_name(self) -> str:
        return "voicebox"

    async def synthesize(
        self,
        text: str,
        voice_id: str,
        language: str = "pt-BR",
    ) -> bytes:
        resp = await self._client.post(
            "/generate",
            json={
                "text": text,
                "profile_id": voice_id,
                "language": language,
            },
        )
        resp.raise_for_status()

        # Voicebox retorna áudio binário diretamente
        audio_bytes = resp.content

        logger.info(
            "tts.voicebox.synthesized",
            voice_id=voice_id,
            text_chars=len(text),
            audio_bytes=len(audio_bytes),
        )
        return audio_bytes

    async def list_voices(self) -> list[TTSVoice]:
        resp = await self._client.get("/profiles")
        resp.raise_for_status()
        raw_profiles: list[dict] = resp.json() if isinstance(resp.json(), list) else resp.json().get("profiles", [])

        voices: list[TTSVoice] = []
        for p in raw_profiles:
            voices.append(
                TTSVoice(
                    id=str(p.get("id", "")),
                    name=p.get("name", ""),
                    language=p.get("language", "en-US"),
                    provider="voicebox",
                    is_cloned=p.get("is_cloned", True),
                )
            )
        return voices

    async def create_voice(
        self,
        name: str,
        audio_data: bytes,
        language: str = "pt-BR",
    ) -> TTSVoice:
        """Cria voice clone via POST /profiles com áudio de referência."""
        resp = await self._client.post(
            "/profiles",
            data={"name": name, "language": language},
            files={"audio": (f"{name}.mp3", audio_data, "audio/mpeg")},
        )
        resp.raise_for_status()
        data = resp.json()

        voice = TTSVoice(
            id=str(data.get("id", "")),
            name=data.get("name", name),
            language=language,
            provider="voicebox",
            is_cloned=True,
        )
        logger.info("tts.voicebox.voice_created", voice_id=voice.id, name=name)
        return voice

    async def delete_voice(self, voice_id: str) -> None:
        resp = await self._client.delete(f"/profiles/{voice_id}")
        resp.raise_for_status()
        logger.info("tts.voicebox.voice_deleted", voice_id=voice_id)

    async def aclose(self) -> None:
        await self._client.aclose()
