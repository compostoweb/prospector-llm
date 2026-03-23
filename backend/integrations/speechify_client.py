"""
integrations/speechify_client.py

Cliente HTTP assíncrono para Speechify — geração de áudio TTS (voice notes).

Base URL: https://api.sws.speechify.com/v1
Auth:     Authorization: Bearer {SPEECHIFY_API_KEY}

Uso no dispatch_worker:
  audio_bytes = await speechify_client.synthesize(text, voice_id)
  → retorna MP3 raw bytes para upload via Unipile

Vozes recomendadas (Speechify SIMBA):
  - "henry"  → masculino, neutro, profissional
  - "aria"   → feminino, natural
  - "george" → masculino, formal

Custo: ~$10/1M chars (tier SIMBA)
"""

from __future__ import annotations

import httpx
import structlog

from core.config import settings

logger = structlog.get_logger()

_BASE_URL = "https://api.sws.speechify.com/v1"
_TIMEOUT = 60.0  # Síntese de áudio pode demorar
_DEFAULT_LANGUAGE = "pt-BR"


class SpeechifyClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=_BASE_URL,
            headers={"Authorization": f"Bearer {settings.SPEECHIFY_API_KEY or ''}"},
            timeout=_TIMEOUT,
        )

    async def synthesize(
        self,
        text: str,
        voice_id: str | None = None,
        language: str = _DEFAULT_LANGUAGE,
    ) -> bytes:
        """
        Converte texto em áudio MP3.

        text:     texto a ser sintetizado (máx ~5.000 chars recomendado)
        voice_id: ID da voz (default: settings.SPEECHIFY_VOICE_ID)
        language: código BCP-47 (default: pt-BR)

        Retorna bytes do arquivo MP3 pronto para upload.
        Lança httpx.HTTPStatusError em caso de falha na API.
        """
        vid = voice_id or settings.SPEECHIFY_VOICE_ID

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

        # A Speechify retorna audio_data como base64 dentro de JSON
        data = resp.json()
        if audio_data := data.get("audio_data"):
            import base64
            audio_bytes = base64.b64decode(audio_data)
        else:
            # Alguns endpoints retornam o binário diretamente
            audio_bytes = resp.content

        logger.info(
            "speechify.synthesized",
            voice_id=vid,
            text_chars=len(text),
            audio_bytes=len(audio_bytes),
        )
        return audio_bytes

    async def list_voices(self) -> list[dict]:
        """Retorna a lista de vozes disponíveis na conta."""
        resp = await self._client.get("/voices")
        resp.raise_for_status()
        return resp.json().get("voices", [])

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "SpeechifyClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()


# Singleton
speechify_client = SpeechifyClient()
