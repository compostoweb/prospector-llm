"""
integrations/tts/elevenlabs_provider.py

Provider TTS para ElevenLabs.

API ref: https://elevenlabs.io/docs/api-reference/text-to-speech/convert
- Synthesis:    POST /v1/text-to-speech/{voice_id}?output_format=mp3_44100_128
- List voices:  GET  /v1/voices
- Clone voice:  POST /v1/voices/add  (multipart)
- Delete voice: DELETE /v1/voices/{voice_id}

Notas:
  - Speed: controlado via voice_settings.speed (0.25–4.0; 1.0 = normal)
  - Pitch: não tem equivalente na API ElevenLabs — ignorado com aviso de log
  - Modelo padrão: eleven_multilingual_v2 (suporta pt-BR nativamente)
"""

from __future__ import annotations

import httpx
import structlog

from integrations.tts.base import TTSProvider, TTSVoice

logger = structlog.get_logger()

_BASE_URL = "https://api.elevenlabs.io/v1"
_TIMEOUT = 60.0
_DEFAULT_MODEL = "eleven_multilingual_v2"


class ElevenLabsProvider(TTSProvider):
    """Provider TTS via ElevenLabs Cloud API."""

    def __init__(
        self,
        api_key: str,
        default_voice_id: str = "",
        model_id: str = _DEFAULT_MODEL,
    ) -> None:
        self._api_key = api_key
        self._default_voice_id = default_voice_id
        self._model_id = model_id
        self._client = httpx.AsyncClient(
            base_url=_BASE_URL,
            headers={
                "xi-api-key": api_key,
                "Content-Type": "application/json",
            },
            timeout=_TIMEOUT,
        )

    @property
    def provider_name(self) -> str:
        return "elevenlabs"

    async def synthesize(
        self,
        text: str,
        voice_id: str,
        language: str = "pt-BR",
        speed: float = 1.0,
        pitch: float = 0.0,
    ) -> bytes:
        """Converte texto em áudio MP3 via ElevenLabs."""
        vid = voice_id or self._default_voice_id
        if not vid:
            raise ValueError(
                "ElevenLabs requer um voice_id. Configure ELEVENLABS_VOICE_ID "
                "ou selecione uma voz na cadência."
            )

        if pitch != 0.0:
            logger.warning(
                "tts.elevenlabs.pitch_not_supported",
                pitch=pitch,
                msg="ElevenLabs não suporta controle de pitch — parâmetro ignorado.",
            )

        # ElevenLabs speed: 0.25–4.0 (1.0 = normal)
        # O sistema usa 0.5–2.0 — valores caem dentro do range aceito, passa direto
        speed_clamped = max(0.25, min(speed, 4.0))

        payload: dict = {
            "text": text,
            "model_id": self._model_id,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "speed": speed_clamped,
            },
        }

        resp = await self._client.post(
            f"/text-to-speech/{vid}",
            params={"output_format": "mp3_44100_128"},
            json=payload,
        )
        resp.raise_for_status()

        audio_bytes = resp.content
        logger.info(
            "tts.elevenlabs.synthesized",
            voice_id=vid,
            model=self._model_id,
            text_chars=len(text),
            audio_bytes=len(audio_bytes),
            speed=speed_clamped,
        )
        return audio_bytes

    async def list_voices(self) -> list[TTSVoice]:
        """Retorna todas as vozes disponíveis na conta ElevenLabs."""
        resp = await self._client.get("/voices")
        resp.raise_for_status()
        data = resp.json()

        raw_voices: list[dict] = data.get("voices", [])
        voices: list[TTSVoice] = []
        for v in raw_voices:
            # Determina o idioma: tenta extrair de labels
            labels: dict = v.get("labels", {})
            language = labels.get("language", labels.get("accent", "en-US"))
            # Normaliza para BCP-47 simples quando vier só "portuguese"
            if language.lower() in ("portuguese", "portuguese (brazilian)", "pt"):
                language = "pt-BR"

            voices.append(
                TTSVoice(
                    id=v.get("voice_id", ""),
                    name=v.get("name", ""),
                    language=language,
                    provider="elevenlabs",
                    is_cloned=v.get("category") == "cloned",
                )
            )
        return voices

    async def create_voice(
        self,
        name: str,
        audio_data: bytes,
        language: str = "pt-BR",
        filename: str = "audio",
        content_type: str = "audio/mpeg",
    ) -> TTSVoice:
        """
        Cria voice clone via POST /voices/add.
        ElevenLabs aceita arquivos de áudio de 10s–5min, formatos mp3/wav/m4a/ogg.
        """
        # Para multipart precisamos de um client sem o Content-Type fixo de JSON
        async with httpx.AsyncClient(
            base_url=_BASE_URL,
            headers={"xi-api-key": self._api_key},
            timeout=_TIMEOUT,
        ) as client:
            resp = await client.post(
                "/voices/add",
                data={"name": name},
                files={"files": (filename, audio_data, content_type)},
            )
        resp.raise_for_status()
        data = resp.json()

        voice = TTSVoice(
            id=data.get("voice_id", ""),
            name=name,
            language=language,
            provider="elevenlabs",
            is_cloned=True,
        )
        logger.info("tts.elevenlabs.voice_created", voice_id=voice.id, name=name)
        return voice

    async def delete_voice(self, voice_id: str) -> None:
        resp = await self._client.delete(f"/voices/{voice_id}")
        resp.raise_for_status()
        logger.info("tts.elevenlabs.voice_deleted", voice_id=voice_id)

    async def aclose(self) -> None:
        await self._client.aclose()
