"""
Módulo de Extração de Samples de Áudio
======================================

Contém funcionalidades para extrair samples de áudio de diversas fontes
para uso com engines TTS, especialmente otimizado para CoquiTTS.

Classes disponíveis:
- YouTubeSampleExtractor: Extração de samples do YouTube
- AudioSampleProcessor: Processamento e validação de samples
"""

from .youtube_extractor import YouTubeSampleExtractor
from .audio_processor import AudioSampleProcessor

__all__ = [
    'YouTubeSampleExtractor',
    'AudioSampleProcessor'
] 