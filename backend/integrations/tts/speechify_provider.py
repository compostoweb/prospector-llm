"""
integrations/tts/speechify_provider.py

Provider TTS que encapsula o SpeechifyClient existente.
Adiciona suporte a voice cloning (POST /voices) e delete.

API ref: https://api.sws.speechify.com/v1
"""

from __future__ import annotations

import base64

import httpx
import structlog

from integrations.tts.base import TTSProvider, TTSVoice

logger = structlog.get_logger()

_BASE_URL = "https://api.sws.speechify.com/v1"
_TIMEOUT = 60.0


class SpeechifyProvider(TTSProvider):

    def __init__(self, api_key: str, default_voice_id: str = "henry") -> None:
        self._api_key = api_key
        self._default_voice_id = default_voice_id
        self._client = httpx.AsyncClient(
            base_url=_BASE_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=_TIMEOUT,
        )

    @property
    def provider_name(self) -> str:
        return "speechify"

    async def synthesize(
        self,
        text: str,
        voice_id: str,
        language: str = "pt-BR",
    ) -> bytes:
        vid = voice_id or self._default_voice_id
        resp = await self._client.post(
            "/audio/speech",
            json={
                "input": text,
                "voice_id": vid,
                "language": language,
                "audio_format": "mp3",
            },
        )
        resp.raise_for_status()

        data = resp.json()
        if audio_data := data.get("audio_data"):
            audio_bytes = base64.b64decode(audio_data)
        else:
            audio_bytes = resp.content

        logger.info(
            "tts.speechify.synthesized",
            voice_id=vid,
            text_chars=len(text),
            audio_bytes=len(audio_bytes),
        )
        return audio_bytes

    async def list_voices(self) -> list[TTSVoice]:
        resp = await self._client.get("/voices")
        resp.raise_for_status()
        data = resp.json()

        # API returns a plain list (not {voices: [...]})
        raw_voices: list[dict] = data if isinstance(data, list) else data.get("voices", [])

        voices: list[TTSVoice] = []
        for v in raw_voices:
            voices.append(
                TTSVoice(
                    id=v.get("id", v.get("voice_id", "")),
                    name=v.get("display_name", v.get("name", "")),
                    language=v.get("locale", v.get("language", "en-US")),
                    provider="speechify",
                    is_cloned=v.get("type") == "cloned",
                )
            )
        return voices

    async def create_voice(
        self,
        name: str,
        audio_data: bytes,
        language: str = "pt-BR",
    ) -> TTSVoice:
        """
        Cria voice clone via POST /voices.
        Speechify exige consent=True e sample de áudio (10-30s, <5MB).
        """
        resp = await self._client.post(
            "/voices",
            data={"name": name, "consent": "true"},
            files={"sample": (f"{name}.mp3", audio_data, "audio/mpeg")},
        )
        resp.raise_for_status()
        data = resp.json()

        voice = TTSVoice(
            id=data.get("id", data.get("voice_id", "")),
            name=data.get("name", name),
            language=language,
            provider="speechify",
            is_cloned=True,
        )
        logger.info("tts.speechify.voice_created", voice_id=voice.id, name=name)
        return voice

    async def delete_voice(self, voice_id: str) -> None:
        resp = await self._client.delete(f"/voices/{voice_id}")
        resp.raise_for_status()
        logger.info("tts.speechify.voice_deleted", voice_id=voice_id)

    async def aclose(self) -> None:
        await self._client.aclose()
