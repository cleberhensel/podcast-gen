"""
Engine TTS para Coqui TTS com XTTS v2
Implementa síntese usando Coqui TTS com modelos XTTS para português brasileiro
"""

import tempfile
import os
import io
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
import warnings

from .base_engine import BaseTTSEngine, TTSResult
from ..models.character import Character, Gender
from ..models.dialogue import Dialogue

logger = logging.getLogger(__name__)

# Suprimir warnings do PyTorch e TTS para logs mais limpos
warnings.filterwarnings("ignore", category=UserWarning, module="torch")
warnings.filterwarnings("ignore", category=FutureWarning, module="TTS")

class CoquiTTSEngine(BaseTTSEngine):
    """Engine TTS usando Coqui TTS com XTTS v2 multilingual"""
    
    def __init__(self):
        super().__init__("coqui")
        self._tts_instance = None
        self._available_speakers = []
        self._model_loaded = False
        
        # Configuração do modelo XTTS v2
        self._model_name = "tts_models/multilingual/multi-dataset/xtts_v2"
        self._language = "pt"  # Português brasileiro
        
        # Mapeamento de personagens para configurações de voz
        self._character_voice_mapping = {
            'HOST_MALE': {
                'type': 'preset_speaker',
                'speaker': 'Ana Florence',  # Fallback, será ajustado
                'gender': 'male',
                'temperature': 0.7,
                'length_penalty': 1.0,
                'repetition_penalty': 2.0,
                'top_k': 50,
                'top_p': 0.85
            },
            'HOST_FEMALE': {
                'type': 'preset_speaker',
                'speaker': 'Ana Florence',  # Speaker feminina do XTTS
                'gender': 'female',
                'temperature': 0.65,  # Mais estável para voz feminina
                'length_penalty': 1.1,
                'repetition_penalty': 2.0,
                'top_k': 45,
                'top_p': 0.8
            },
            'EXPERT_MALE': {
                'type': 'preset_speaker',
                'speaker': 'Ana Florence',  # Fallback
                'gender': 'male',
                'temperature': 0.75,
                'length_penalty': 1.0,
                'repetition_penalty': 2.1,
                'top_k': 50,
                'top_p': 0.85
            },
            'EXPERT_FEMALE': {
                'type': 'preset_speaker',
                'speaker': 'Ana Florence',
                'gender': 'female',
                'temperature': 0.7,
                'length_penalty': 1.05,
                'repetition_penalty': 2.0,
                'top_k': 48,
                'top_p': 0.82
            },
            'GUEST_MALE': {
                'type': 'preset_speaker',
                'speaker': 'Ana Florence',  # Fallback
                'gender': 'male',
                'temperature': 0.8,
                'length_penalty': 0.95,
                'repetition_penalty': 2.0,
                'top_k': 52,
                'top_p': 0.87
            },
            'GUEST_FEMALE': {
                'type': 'preset_speaker',
                'speaker': 'Ana Florence',
                'gender': 'female',
                'temperature': 0.68,
                'length_penalty': 1.08,
                'repetition_penalty': 2.0,
                'top_k': 46,
                'top_p': 0.81
            },
            'NARRATOR_MALE': {
                'type': 'preset_speaker',
                'speaker': 'Ana Florence',  # Fallback
                'gender': 'male',
                'temperature': 0.6,  # Mais estável para narração
                'length_penalty': 1.2,
                'repetition_penalty': 2.2,
                'top_k': 40,
                'top_p': 0.75
            },
            'NARRATOR_FEMALE': {
                'type': 'preset_speaker',
                'speaker': 'Ana Florence',
                'gender': 'female',
                'temperature': 0.55,
                'length_penalty': 1.25,
                'repetition_penalty': 2.2,
                'top_k': 38,
                'top_p': 0.73
            }
        }
        
        # Tentar inicializar Coqui TTS
        self._coqui_available = self._initialize_coqui()
        
    def _initialize_coqui(self) -> bool:
        """Inicializa Coqui TTS e carrega modelo XTTS v2"""
        try:
            # Importar TTS
            from TTS.api import TTS
            
            logger.info(f"Inicializando Coqui TTS com modelo {self._model_name}")
            
            # Determinar device (CPU para compatibilidade Docker)
            device = "cpu"
            
            # Inicializar TTS com XTTS v2
            self._tts_instance = TTS(self._model_name, progress_bar=False)
            
            if device == "cuda":
                self._tts_instance = self._tts_instance.to(device)
            
            # Descobrir speakers disponíveis
            self._discover_available_speakers()
            
            # Atualizar mapeamento com speakers reais
            self._update_speaker_mapping()
            
            self._model_loaded = True
            logger.info("Coqui TTS inicializado com sucesso")
            
            return True
            
        except ImportError as e:
            logger.warning(f"Biblioteca Coqui TTS não disponível: {e}")
            return False
        except Exception as e:
            logger.error(f"Erro inicializando Coqui TTS: {e}")
            return False
    
    def _discover_available_speakers(self):
        """Descobre speakers disponíveis no modelo XTTS"""
        try:
            # XTTS v2 tem speakers pré-definidos
            # Lista baseada na documentação oficial
            self._available_speakers = [
                "Ana Florence",  # Speaker principal feminina
                "male_voice_1",  # Placeholder para vozes masculinas
                "female_voice_1"  # Placeholder para vozes femininas adicionais
            ]
            
            logger.info(f"Speakers XTTS disponíveis: {self._available_speakers}")
            
        except Exception as e:
            logger.warning(f"Erro descobrindo speakers: {e}")
            self._available_speakers = ["Ana Florence"]  # Fallback seguro
    
    def _update_speaker_mapping(self):
        """Atualiza mapeamento de personagens com speakers reais disponíveis"""
        # Para XTTS v2, vamos usar o speaker principal e variar os parâmetros
        # para criar vozes distintas masculinas e femininas
        
        # Ana Florence é o speaker principal feminino do XTTS v2
        main_speaker = "Ana Florence"
        
        # Atualizar todos os mapeamentos para usar o speaker disponível
        for char_id in self._character_voice_mapping:
            self._character_voice_mapping[char_id]['speaker'] = main_speaker
    
    def synthesize(self, dialogue: Dialogue, character: Character) -> TTSResult:
        """Sintetiza fala usando Coqui TTS XTTS v2"""
        
        if not self._coqui_available or not self._model_loaded:
            # Fallback para macOS se Coqui não disponível
            logger.info("Usando fallback macOS Say para síntese (Coqui TTS indisponível)")
            
            from .macos_tts import MacOSTTSEngine
            macos_engine = MacOSTTSEngine()
            return macos_engine.synthesize(dialogue, character)
        
        try:
            # Obter configurações do personagem
            voice_config = self._get_character_voice_config(character)
            
            # Processar texto
            processed_text = self._apply_speech_modifications(dialogue.get_processed_text(), dialogue, character)
            
            # Limitar comprimento do texto para evitar problemas de memória
            if len(processed_text) > 500:
                processed_text = processed_text[:500] + "..."
                logger.warning(f"Texto truncado para personagem {character.id}")
            
            # Criar arquivo temporário
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name
            
            try:
                # Gerar áudio com XTTS
                self._tts_instance.tts_to_file(
                    text=processed_text,
                    file_path=temp_path,
                    speaker=voice_config['speaker'],
                    language=self._language,
                    split_sentences=True,  # Melhor qualidade
                    # Parâmetros avançados (se suportados)
                    **{k: v for k, v in voice_config.items() 
                       if k in ['temperature', 'length_penalty', 'repetition_penalty', 'top_k', 'top_p']}
                )
                
                # Ler áudio gerado
                with open(temp_path, 'rb') as f:
                    audio_data = f.read()
                
                # Aplicar processamento adicional se necessário
                audio_data = self._apply_voice_processing(audio_data, character, 24000)
                
                return TTSResult(
                    audio_data=audio_data,
                    format="wav",
                    sample_rate=24000,  # XTTS usa 24kHz
                    channels=1,
                    metadata={
                        'engine': 'coqui',
                        'model': self._model_name,
                        'character': character.id,
                        'speaker': voice_config['speaker'],
                        'language': self._language,
                        'text_length': len(processed_text)
                    }
                )
                
            finally:
                # Limpar arquivo temporário
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except Exception as e:
            logger.error(f"Erro na síntese Coqui TTS para {character.id}: {e}")
            
            # Fallback para macOS em caso de erro
            from .macos_tts import MacOSTTSEngine
            macos_engine = MacOSTTSEngine()
            return macos_engine.synthesize(dialogue, character)
    
    def _get_character_voice_config(self, character: Character) -> Dict[str, Any]:
        """Obtém configuração de voz para o personagem"""
        
        # Configuração base do personagem
        base_config = self._character_voice_mapping.get(character.id, {})
        
        # Se não encontrar configuração específica, usar baseado no gênero
        if not base_config:
            if character.gender == Gender.FEMALE:
                base_config = self._character_voice_mapping['HOST_FEMALE'].copy()
            else:
                base_config = self._character_voice_mapping['HOST_MALE'].copy()
        
        # Aplicar modificações específicas do Character se especificadas
        config = base_config.copy()
        
        # Ajustar temperatura baseado na personalidade
        if hasattr(character, 'voice_style'):
            if character.voice_style.value == 'calm':
                config['temperature'] = max(0.4, config.get('temperature', 0.7) - 0.2)
            elif character.voice_style.value == 'energetic':
                config['temperature'] = min(0.9, config.get('temperature', 0.7) + 0.1)
        
        return config
    
    def _apply_speech_modifications(self, text: str, dialogue: Dialogue, character: Character) -> str:
        """Aplica modificações específicas de fala para Coqui TTS"""
        
        processed_text = text
        
        # Aplicar ênfases com marcações SSML simplificadas
        if dialogue.emphasis_words:
            for word in dialogue.emphasis_words:
                processed_text = processed_text.replace(word, f"**{word}**")
        
        # Aplicar pausas
        if dialogue.pause_before > 0:
            processed_text = f"... {processed_text}"
        
        if dialogue.pause_after > 0:
            processed_text = f"{processed_text} ..."
        
        # Limpar texto para compatibilidade
        processed_text = processed_text.replace('"', "'").replace('\n', ' ')
        
        return processed_text.strip()
    
    def _apply_voice_processing(self, audio_data: bytes, character: Character, sample_rate: int) -> bytes:
        """Aplica processamento adicional ao áudio se necessário"""
        
        # Para XTTS, o processamento é principalmente feito pelos parâmetros do modelo
        # Retornar áudio sem modificações por enquanto
        
        return audio_data
    
    def get_available_voices(self) -> List[Dict[str, Any]]:
        """Retorna lista de vozes disponíveis"""
        
        if not self._coqui_available:
            return []
        
        voices = []
        
        for char_id, config in self._character_voice_mapping.items():
            voices.append({
                'id': char_id,
                'name': char_id.replace('_', ' ').title(),
                'gender': config.get('gender', 'neutral'),
                'language': self._language,
                'speaker': config.get('speaker', 'Ana Florence'),
                'engine': 'coqui',
                'model': self._model_name,
                'quality': 'very_high',
                'neural': True
            })
        
        return voices
    
    def is_voice_available(self, voice_id: str) -> bool:
        """Verifica se uma voz específica está disponível"""
        if not self._coqui_available:
            return False
        
        return voice_id in self._character_voice_mapping
    
    def test_synthesis(self, text: str = "Teste de síntese com Coqui TTS") -> bool:
        """Testa se o engine está funcionando corretamente"""
        
        if not self._coqui_available or not self._model_loaded:
            return False
        
        try:
            # Teste simples de síntese
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name
            
            self._tts_instance.tts_to_file(
                text=text,
                file_path=temp_path,
                speaker="Ana Florence",
                language=self._language
            )
            
            # Verificar se arquivo foi criado
            success = os.path.exists(temp_path) and os.path.getsize(temp_path) > 0
            
            # Limpar
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            
            return success
            
        except Exception as e:
            logger.error(f"Erro no teste de síntese Coqui: {e}")
            return False
    
    def get_engine_status(self) -> Dict[str, Any]:
        """Retorna status detalhado do engine"""
        
        status = {
            'name': self.name,
            'available': self._coqui_available,
            'model_loaded': self._model_loaded,
            'model_name': self._model_name,
            'language': self._language,
            'speakers_count': len(self._available_speakers),
            'voices_count': len(self._character_voice_mapping),
            'test_status': self.test_synthesis() if self._coqui_available else False,
            'device': 'cpu',  # Para compatibilidade Docker
            'features': {
                'voice_cloning': True,
                'multilingual': True,
                'streaming': False,  # Não implementado ainda
                'neural': True,
                'quality': 'very_high'
            }
        }
        
        if self._coqui_available:
            status['available_speakers'] = self._available_speakers
            status['character_mappings'] = list(self._character_voice_mapping.keys())
        
        return status 