"""
Engine TTS do Google Cloud
Implementa síntese usando Google Cloud Text-to-Speech API
"""

import io
import logging
from typing import List, Dict, Any, Optional

from .base_engine import BaseTTSEngine, TTSResult
from ..models.character import Character
from ..models.dialogue import Dialogue

logger = logging.getLogger(__name__)

class GoogleTTSEngine(BaseTTSEngine):
    """Engine TTS usando Google Cloud Text-to-Speech"""
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__("Google Cloud TTS")
        self.api_key = api_key
        self._client = None
        self._voices_cache = None
        
    def _init_client(self):
        """Inicializa cliente Google TTS"""
        if self._client is not None:
            return
            
        try:
            # Tentar importar biblioteca Google
            from google.cloud import texttospeech
            import os
            
            # Configurar autenticação se API key fornecida
            if self.api_key:
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = self.api_key
            
            self._client = texttospeech.TextToSpeechClient()
            logger.info("Cliente Google TTS inicializado")
            
        except ImportError:
            logger.error("Biblioteca google-cloud-texttospeech não encontrada. Instale com: pip install google-cloud-texttospeech")
            raise
        except Exception as e:
            logger.error(f"Erro inicializando cliente Google TTS: {e}")
            raise
    
    def synthesize(self, dialogue: Dialogue, character: Character) -> TTSResult:
        """Sintetiza fala usando Google TTS"""
        
        self._init_client()
        
        if not self._client:
            raise Exception("Cliente Google TTS não inicializado")
        
        try:
            from google.cloud import texttospeech
            
            # Processar texto
            processed_text = dialogue.get_processed_text()
            
            # Obter modificadores de emoção
            emotion_mods = dialogue.get_emotion_modifiers()
            
            # Configurar síntese
            synthesis_input = texttospeech.SynthesisInput(text=processed_text)
            
            # Configurar voz
            voice = texttospeech.VoiceSelectionParams(
                language_code="pt-BR",
                name=self._map_voice_to_google(character.voice_id),
                ssml_gender=self._get_google_gender(character.gender.value)
            )
            
            # Configurar áudio
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.LINEAR16,
                sample_rate_hertz=22050,
                speaking_rate=character.speed * emotion_mods.get('speed', 1.0),
                pitch=character.pitch * emotion_mods.get('pitch', 1.0) * 0.2 - 10.0,  # Converter para semitones
                volume_gain_db=max(-96.0, min(16.0, (character.volume * emotion_mods.get('volume', 1.0) - 1.0) * 20))
            )
            
            # Aplicar overrides do diálogo
            if dialogue.override_speed:
                audio_config.speaking_rate = dialogue.override_speed
            if dialogue.override_pitch:
                audio_config.pitch = dialogue.override_pitch * 0.2 - 10.0
            if dialogue.override_volume:
                audio_config.volume_gain_db = max(-96.0, min(16.0, (dialogue.override_volume - 1.0) * 20))
            
            # Realizar síntese
            response = self._client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            # Calcular duração estimada
            duration = dialogue.get_estimated_duration()
            
            return TTSResult(
                audio_data=response.audio_content,
                format="wav",
                sample_rate=22050,
                channels=1,
                duration=duration,
                metadata={
                    'engine': 'google',
                    'voice': voice.name,
                    'language': voice.language_code,
                    'emotion': dialogue.emotion.value
                }
            )
            
        except Exception as e:
            logger.error(f"Erro na síntese Google TTS: {e}")
            raise
    
    def get_available_voices(self) -> List[Dict[str, Any]]:
        """Retorna lista de vozes disponíveis do Google"""
        
        if self._voices_cache is not None:
            return self._voices_cache
        
        try:
            self._init_client()
            
            if not self._client:
                return []
            
            from google.cloud import texttospeech
            
            # Listar vozes
            voices = self._client.list_voices()
            
            voice_list = []
            for voice in voices.voices:
                # Filtrar apenas vozes em português
                if voice.language_codes and any('pt' in lang for lang in voice.language_codes):
                    voice_list.append({
                        'id': voice.name,
                        'name': voice.name,
                        'language': voice.language_codes[0] if voice.language_codes else 'pt-BR',
                        'gender': self._google_gender_to_string(voice.ssml_gender),
                        'quality': 'high' if 'Neural2' in voice.name or 'Journey' in voice.name else 'standard',
                        'engine': 'google'
                    })
            
            self._voices_cache = voice_list
            return voice_list
            
        except Exception as e:
            logger.error(f"Erro listando vozes Google: {e}")
            return []
    
    def is_voice_available(self, voice_id: str) -> bool:
        """Verifica se uma voz está disponível"""
        voices = self.get_available_voices()
        return any(voice['id'] == voice_id or 
                  self._map_voice_to_google(voice_id) == voice['id'] 
                  for voice in voices)
    
    def _map_voice_to_google(self, macos_voice: str) -> str:
        """Mapeia voz do macOS para equivalente Google"""
        
        # Mapeamento de vozes conhecidas
        voice_mapping = {
            'Alex': 'pt-BR-Neural2-B',
            'Samantha': 'pt-BR-Neural2-A', 
            'Daniel': 'pt-BR-Neural2-C',
            'Victoria': 'pt-BR-Standard-A',
            'Tom': 'pt-BR-Standard-B',
            'Kate': 'pt-BR-Wavenet-A',
            'Fred': 'pt-BR-Wavenet-B',
            'Susan': 'pt-BR-Wavenet-C'
        }
        
        return voice_mapping.get(macos_voice, 'pt-BR-Neural2-A')
    
    def _get_google_gender(self, gender_str: str):
        """Converte string de gênero para enum Google"""
        try:
            from google.cloud import texttospeech
            
            if gender_str.lower() == 'male':
                return texttospeech.SsmlVoiceGender.MALE
            elif gender_str.lower() == 'female':
                return texttospeech.SsmlVoiceGender.FEMALE
            else:
                return texttospeech.SsmlVoiceGender.NEUTRAL
        except ImportError:
            return 1  # MALE como fallback
    
    def _google_gender_to_string(self, google_gender) -> str:
        """Converte enum Google para string"""
        try:
            from google.cloud import texttospeech
            
            if google_gender == texttospeech.SsmlVoiceGender.MALE:
                return 'male'
            elif google_gender == texttospeech.SsmlVoiceGender.FEMALE:
                return 'female'
            else:
                return 'neutral'
        except ImportError:
            return 'neutral'
    
    def test_synthesis(self, text: str = "Teste de síntese Google TTS") -> bool:
        """Testa se o engine está funcionando"""
        try:
            self._init_client()
            
            if not self._client:
                return False
            
            from google.cloud import texttospeech
            
            # Teste simples
            synthesis_input = texttospeech.SynthesisInput(text=text)
            voice = texttospeech.VoiceSelectionParams(
                language_code="pt-BR",
                ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            )
            
            response = self._client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            return len(response.audio_content) > 0
            
        except Exception as e:
            logger.error(f"Erro no teste Google TTS: {e}")
            return False
    
    def get_portuguese_voices(self) -> List[Dict[str, Any]]:
        """Retorna apenas vozes em português (todas já são)"""
        return self.get_available_voices()
    
    def configure_api_key(self, api_key: str):
        """Configura chave da API"""
        self.api_key = api_key
        self._client = None  # Forçar reinicialização 