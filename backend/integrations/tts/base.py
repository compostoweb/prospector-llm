"""
integrations/tts/base.py

Contrato base para todos os provedores de TTS (Text-to-Speech).
Cada provedor implementa esta interface — o restante do sistema
nunca importa Speechify ou Voicebox diretamente, só usa TTSProvider.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class TTSVoice:
    """Informações de uma voz disponível no provedor."""
    id: str
    name: str
    language: str
    provider: str       # "speechify" | "voicebox" | "edge"
    is_cloned: bool     # True se é um voice clone (não built-in)


class TTSProvider(ABC):
    """Interface base para provedores de TTS."""

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice_id: str,
        language: str = "pt-BR",
        speed: float = 1.0,
        pitch: float = 0.0,
    ) -> bytes:
        """Converte texto em áudio MP3. Retorna raw bytes."""
        ...

    @abstractmethod
    async def list_voices(self) -> list[TTSVoice]:
        """Retorna todas as vozes disponíveis (built-in + clonadas)."""
        ...

    @abstractmethod
    async def create_voice(
        self,
        name: str,
        audio_data: bytes,
        language: str = "pt-BR",
    ) -> TTSVoice:
        """Cria um voice clone a partir de áudio de referência."""
        ...

    @abstractmethod
    async def delete_voice(self, voice_id: str) -> None:
        """Deleta uma voz clonada. Lança ValueError se for built-in."""
        ...
