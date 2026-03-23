"""
integrations/tts/__init__.py

Exports públicos do módulo TTS.
O restante do sistema só importa daqui — nunca diretamente de speechify_provider ou voicebox_provider.
"""

from integrations.tts.base import TTSProvider, TTSVoice
from integrations.tts.registry import TTSRegistry

__all__ = [
    "TTSProvider",
    "TTSVoice",
    "TTSRegistry",
]
