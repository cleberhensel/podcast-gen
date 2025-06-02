"""
Engines de TTS para Gerador de Podcast
"""

from .base_engine import BaseTTSEngine, TTSResult
from .macos_tts import MacOSTTSEngine
from .google_tts import GoogleTTSEngine

__all__ = [
    'BaseTTSEngine', 'TTSResult',
    'MacOSTTSEngine', 'GoogleTTSEngine'
] 