"""
integrations/tts/edge_provider.py

Provider TTS usando Microsoft Edge Neural Voices via edge-tts.

Vantagens:
  - Gratuito, sem API key
  - Vozes pt-BR nativas (Francisca, Antonio, Thalita, Brenda, etc.)
  - Qualidade neural — indistinguível de humano em pt-BR
  - Suporte nativo a controle de velocidade e pitch
  - Saída MP3

Vozes pt-BR disponíveis (Neural):
  - pt-BR-FranciscaNeural  (feminina — padrão)
  - pt-BR-AntonioNeural    (masculino)
  - pt-BR-ThalitaNeural    (feminina)
  - pt-BR-BrendaNeural     (feminina)
  - pt-BR-DonatoNeural     (masculino)
  - pt-BR-ElzaNeural       (feminina)
  - pt-BR-FabioNeural      (masculino)
  - pt-BR-GiovannaNeural   (feminina)
  - pt-BR-HumbertoNeural   (masculino)
  - pt-BR-LeilaNeural      (feminina)
  - pt-BR-LeticiaNeural    (feminina)
  - pt-BR-ManuelaNeural    (feminina)
  - pt-BR-NicolauNeural    (masculino)
  - pt-BR-ValerioNeural    (masculino)
  - pt-BR-YaraNeural       (feminina)
"""

from __future__ import annotations

import io

import edge_tts
import structlog

from integrations.tts.base import TTSProvider, TTSVoice

logger = structlog.get_logger()


class EdgeTTSProvider(TTSProvider):
    """Provider TTS usando Microsoft Edge Neural Voices (gratuito)."""

    def __init__(self, default_voice_id: str = "pt-BR-FranciscaNeural") -> None:
        self._default_voice_id = default_voice_id

    @property
    def provider_name(self) -> str:
        return "edge"

    @staticmethod
    def _format_rate(speed: float) -> str:
        """Converte speed (0.5–2.0) para formato edge-tts: '+50%', '-30%', etc."""
        pct = round((speed - 1) * 100)
        return f"{pct:+d}%"

    @staticmethod
    def _format_pitch(pitch: float) -> str:
        """Converte pitch (-50 a +50) para formato edge-tts em Hz."""
        hz = round(max(-50, min(pitch, 50)))
        return f"{hz:+d}Hz"

    async def synthesize(
        self,
        text: str,
        voice_id: str,
        language: str = "pt-BR",
        speed: float = 1.0,
        pitch: float = 0.0,
    ) -> bytes:
        """Converte texto em áudio MP3 usando Edge TTS."""
        vid = voice_id or self._default_voice_id
        rate = self._format_rate(speed)
        pitch_str = self._format_pitch(pitch)

        communicate = edge_tts.Communicate(
            text=text,
            voice=vid,
            rate=rate,
            pitch=pitch_str,
        )

        audio_buffer = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_buffer.write(chunk["data"])

        audio_bytes = audio_buffer.getvalue()
        logger.info(
            "tts.edge.synthesized",
            voice_id=vid,
            text_chars=len(text),
            audio_bytes=len(audio_bytes),
            rate=rate,
            pitch=pitch_str,
        )
        return audio_bytes

    async def list_voices(self) -> list[TTSVoice]:
        """Retorna todas as vozes Edge TTS disponíveis."""
        raw_voices = await edge_tts.list_voices()
        voices: list[TTSVoice] = []
        for v in raw_voices:
            voices.append(
                TTSVoice(
                    id=v["ShortName"],
                    name=v["FriendlyName"],
                    language=v["Locale"],
                    provider="edge",
                    is_cloned=False,
                )
            )
        return voices

    async def create_voice(
        self,
        name: str,
        audio_data: bytes,
        language: str = "pt-BR",
    ) -> TTSVoice:
        """Edge TTS não suporta voice cloning."""
        raise NotImplementedError(
            "Edge TTS não suporta voice cloning. "
            "Use Speechify ou Voicebox para criar vozes personalizadas."
        )

    async def delete_voice(self, voice_id: str) -> None:
        """Edge TTS não tem vozes customizadas para deletar."""
        raise NotImplementedError(
            "Edge TTS não suporta deleção de vozes — todas são built-in."
        )
