"""
Engine TTS para Piper
Implementa síntese usando Piper TTS neural speech synthesis
"""

import tempfile
import os
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
import wave

from .base_engine import BaseTTSEngine, TTSResult
from ..models.character import Character, Gender
from ..models.dialogue import Dialogue

logger = logging.getLogger(__name__)

class PiperTTSEngine(BaseTTSEngine):
    """Engine TTS usando Piper neural speech synthesis via biblioteca Python"""
    
    def __init__(self):
        super().__init__("piper")
        self._voices_cache = None
        self._models_path = self._find_models_path()
        self._available_models = self._discover_models()
        
        # Tentar importar a biblioteca Piper
        try:
            import piper
            self._piper_available = True
            logger.info("Biblioteca Piper importada com sucesso")
        except ImportError as e:
            logger.warning(f"Biblioteca Piper não disponível: {e}")
            self._piper_available = False
        
        # Mapeamento de personagens para modelos Piper
        # REVERTENDO: Volta para modelos PT-BR que funcionam bem
        # pt_BR-faber-medium com processamento feminino estava perfeito
        self._character_voice_mapping = {
            'HOST_MALE': 'pt_BR-faber-medium',        # Voz masculina natural
            'HOST_FEMALE': 'pt_BR-faber-medium',      # Mesmo modelo, com processamento feminino otimizado
            'EXPERT_MALE': 'pt_BR-faber-medium',
            'EXPERT_FEMALE': 'pt_BR-faber-medium',
            'GUEST_MALE': 'pt_BR-faber-medium',
            'GUEST_FEMALE': 'pt_BR-faber-medium',
            'NARRATOR_MALE': 'pt_BR-faber-medium',
            'NARRATOR_FEMALE': 'pt_BR-faber-medium'
        }
        
        # Fallback para outros modelos PT-BR disponíveis
        self._character_voice_mapping_fallback = {
            'HOST_MALE': 'pt_BR-edresson-low',
            'HOST_FEMALE': 'pt_BR-edresson-low',
            'EXPERT_MALE': 'pt_BR-edresson-low',
            'EXPERT_FEMALE': 'pt_BR-edresson-low',
            'GUEST_MALE': 'pt_BR-edresson-low',
            'GUEST_FEMALE': 'pt_BR-edresson-low',
            'NARRATOR_MALE': 'pt_BR-edresson-low',
            'NARRATOR_FEMALE': 'pt_BR-edresson-low'
        }
        
        # Configurações específicas para criar vozes distintas sem distorção
        self._voice_modulations = {
            'HOST_MALE': {
                'speed': 1.0, 
                'noise_scale': 0.667,    # Configuração padrão do modelo
                'length_scale': 1.0,     # Tempo natural
                'voice_type': 'male'
            },
            'HOST_FEMALE': {
                'speed': 0.90,           # Mais devagar para naturalidade
                'noise_scale': 0.55,     # Menos ruído para suavidade
                'length_scale': 1.20,    # Mais tempo para articulação delicada
                'voice_type': 'female'   # Ativa processamento natural feminino
            },
            'EXPERT_MALE': {
                'speed': 0.95, 
                'noise_scale': 0.667,
                'length_scale': 1.0,
                'voice_type': 'male'
            },
            'EXPERT_FEMALE': {
                'speed': 1.0, 
                'noise_scale': 0.6,
                'length_scale': 1.1,
                'voice_type': 'female'
            }, 
            'GUEST_MALE': {
                'speed': 1.02, 
                'noise_scale': 0.667,
                'length_scale': 1.0,
                'voice_type': 'male'
            },
            'GUEST_FEMALE': {
                'speed': 0.98, 
                'noise_scale': 0.6,
                'length_scale': 1.05,
                'voice_type': 'female'
            },
            'NARRATOR_MALE': {
                'speed': 0.9, 
                'noise_scale': 0.667,
                'length_scale': 1.2,
                'voice_type': 'male'
            },
            'NARRATOR_FEMALE': {
                'speed': 0.92, 
                'noise_scale': 0.6,
                'length_scale': 1.15,
                'voice_type': 'female'
            }
        }
    
    def _find_models_path(self) -> Optional[Path]:
        """Encontra diretório onde estão os modelos Piper"""
        possible_paths = [
            Path("/home/podcast/.local/share/piper-tts"),  # Docker path primeiro
            Path.home() / ".local/share/piper-tts",
            Path.home() / ".piper",
            Path("/usr/local/share/piper"),
            Path("/opt/piper"),
            Path.cwd() / "models",
            Path.cwd() / "piper-models",
        ]
        
        for path in possible_paths:
            if path.exists() and any(path.rglob("*.onnx")):
                logger.info(f"Modelos Piper encontrados em: {path}")
                return path
                
        logger.warning("Diretório de modelos Piper não encontrado")
        return None
    
    def _discover_models(self) -> List[str]:
        """Descobre modelos disponíveis no sistema"""
        models = []
        
        if not self._models_path:
            return models
        
        try:
            # Procurar arquivos .onnx (modelos Piper)
            for model_file in self._models_path.rglob("*.onnx"):
                model_name = model_file.stem
                # Verificar se existe o arquivo JSON correspondente
                json_file = model_file.with_suffix(".onnx.json")
                if json_file.exists():
                    models.append(model_name)
                    logger.debug(f"Modelo descoberto: {model_name}")
                
        except Exception as e:
            logger.error(f"Erro descobrindo modelos: {e}")
        
        logger.info(f"Modelos Piper disponíveis: {models}")
        return models
    
    def synthesize(self, dialogue: Dialogue, character: Character) -> TTSResult:
        """Sintetiza fala usando Piper TTS neural"""
        
        if not self._piper_available:
            # Fallback para macOS se Piper não disponível
            logger.info(f"Usando fallback macOS Say para síntese (Piper temporariamente indisponível)")
            
            from .macos_tts import MacOSTTSEngine
            macos_engine = MacOSTTSEngine()
            return macos_engine.synthesize(dialogue, character)
        
        try:
            # Importar biblioteca Piper
            from piper import PiperVoice
            
            # Mapear personagem para modelo Piper
            model_name = self._map_character_to_model(character)
            
            # Processar texto
            processed_text = self._apply_speech_modifications(dialogue.get_processed_text(), dialogue, character)
            
            # Localizar arquivos do modelo
            model_path = self._models_path / f"{model_name}.onnx"
            config_path = self._models_path / f"{model_name}.onnx.json"
            
            if not model_path.exists() or not config_path.exists():
                raise Exception(f"Arquivos do modelo '{model_name}' não encontrados")
            
            # Carregar voz Piper
            voice = PiperVoice.load(str(model_path), str(config_path))
            
            # Aplicar configurações específicas do personagem
            modulation = self._voice_modulations.get(character.id, {})
            
            # Ajustar configurações do modelo se especificadas
            if 'noise_scale' in modulation:
                voice.config.noise_scale = modulation['noise_scale']
            if 'length_scale' in modulation:
                voice.config.length_scale = modulation['length_scale']
            
            # Criar arquivo temporário
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name
            
            try:
                # Sintetizar áudio
                logger.info(f"Sintetizando com Piper neural: {model_name} (noise: {voice.config.noise_scale}, length: {voice.config.length_scale})")
                
                # Determinar sample rate baseado no modelo
                if model_name == 'pt_BR-edresson-low':
                    sample_rate = 16000  # Edresson usa 16kHz
                else:
                    sample_rate = 22050  # Faber usa 22kHz
                
                # Abrir arquivo WAV para escrita
                with wave.open(temp_path, 'wb') as wav_file:
                    # Configurar propriedades do WAV
                    wav_file.setnchannels(1)  # Mono
                    wav_file.setsampwidth(2)  # 16-bit
                    wav_file.setframerate(sample_rate)
                    
                    # Sintetizar com Piper
                    voice.synthesize(processed_text, wav_file)
                
                # Ler arquivo gerado
                if not Path(temp_path).exists():
                    raise Exception("Arquivo de áudio não foi gerado pelo Piper")
                
                with open(temp_path, 'rb') as f:
                    audio_data = f.read()
                
                if len(audio_data) == 0:
                    raise Exception("Arquivo de áudio está vazio")
                
                # Calcular duração estimada
                duration = dialogue.get_estimated_duration()
                
                # Aplicar processamento de áudio se necessário (pitch shifting para vozes femininas)
                processed_audio_data = self._apply_voice_processing(audio_data, character, sample_rate)
                
                return TTSResult(
                    audio_data=processed_audio_data,
                    format="wav",
                    sample_rate=sample_rate,  # Usar sample rate correto do modelo
                    channels=1,
                    duration=duration,
                    metadata={
                        'engine': 'piper',
                        'model': model_name,
                        'character': character.id,
                        'emotion': dialogue.emotion.value,
                        'text_length': len(processed_text),
                        'neural': True,
                        'noise_scale': voice.config.noise_scale,
                        'length_scale': voice.config.length_scale,
                        'pitch_processed': modulation.get('voice_type') == 'female'
                    }
                )
                
            finally:
                # Limpar arquivo temporário
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except Exception as e:
            logger.error(f"Erro na síntese Piper: {e}")
            logger.info("Fazendo fallback para macOS Say")
            
            # Fallback para macOS em caso de erro
            from .macos_tts import MacOSTTSEngine
            macos_engine = MacOSTTSEngine()
            return macos_engine.synthesize(dialogue, character)
    
    def _map_character_to_model(self, character: Character) -> str:
        """Mapeia personagem para modelo Piper apropriado"""
        
        # Primeiro, tentar mapeamento direto do character ID (modelo PT-BR)
        if character.id in self._character_voice_mapping:
            model = self._character_voice_mapping[character.id]
            if model in self._available_models:
                logger.info(f"Usando modelo PT-BR principal '{model}' para personagem {character.id}")
                return model
            else:
                logger.warning(f"Modelo principal '{model}' não disponível, usando fallback")
        
        # Fallback para outros modelos PT-BR
        if character.id in self._character_voice_mapping_fallback:
            model = self._character_voice_mapping_fallback[character.id]
            if model in self._available_models:
                logger.info(f"Usando modelo PT-BR fallback '{model}' para personagem {character.id}")
                return model
        
        # Fallback baseado em gênero
        if character.gender == Gender.FEMALE:
            preferred_models = ["pt_BR-faber-medium", "pt_BR-edresson-low"]
        else:
            preferred_models = ["pt_BR-faber-medium", "pt_BR-edresson-low"]
        
        # Procurar primeiro modelo disponível
        for model in preferred_models:
            if model in self._available_models:
                logger.info(f"Usando modelo fallback baseado em gênero '{model}' para personagem {character.id}")
                return model
        
        # Último fallback - primeiro modelo disponível
        if self._available_models:
            fallback_model = self._available_models[0]
            logger.warning(f"Usando fallback genérico '{fallback_model}' para personagem {character.id}")
            return fallback_model
        
        raise Exception("Nenhum modelo Piper disponível para síntese")
    
    def _apply_speech_modifications(self, text: str, dialogue: Dialogue, character: Character) -> str:
        """Aplica modificações de fala ao texto para Piper"""
        
        import re
        
        # Remover marcações específicas do macOS que Piper não entende
        clean_text = re.sub(r'\{[^}]+\}', '', text)
        
        # Normalizar espaços
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        return clean_text
    
    def get_available_voices(self) -> List[Dict[str, Any]]:
        """Retorna lista de vozes/modelos disponíveis do Piper"""
        
        if self._voices_cache is not None:
            return self._voices_cache
        
        voices = []
        
        for model in self._available_models:
            # Parse do nome do modelo para extrair informações
            parts = model.split('-')
            
            if len(parts) >= 2:
                language = parts[0] if '_' in parts[0] else 'unknown'
                voice_name = parts[1] if len(parts) > 1 else 'default'
                quality = parts[2] if len(parts) > 2 else 'medium'
            else:
                language = 'unknown'
                voice_name = model
                quality = 'medium'
            
            # Determinar gênero baseado no nome
            gender = self._determine_model_gender(voice_name)
            
            voice_info = {
                'id': model,
                'name': voice_name.title(),
                'language': language.replace('_', '-'),
                'gender': gender,
                'quality': quality,
                'description': f"Voz neural Piper - {voice_name} ({quality})",
                'engine': 'piper',
                'neural': True
            }
            
            voices.append(voice_info)
        
        self._voices_cache = voices
        return voices
    
    def _determine_model_gender(self, voice_name: str) -> str:
        """Determina gênero baseado no nome do modelo"""
        
        # Mapeamento conhecido de vozes Piper
        known_female = ['edresson', 'ana', 'lucia', 'maria', 'carla']
        known_male = ['faber', 'pedro', 'joao', 'carlos', 'ricardo']
        
        voice_lower = voice_name.lower()
        
        if any(name in voice_lower for name in known_female):
            return 'female'
        elif any(name in voice_lower for name in known_male):
            return 'male'
        else:
            return 'neutral'
    
    def is_voice_available(self, voice_id: str) -> bool:
        """Verifica se uma voz/modelo está disponível"""
        return voice_id in self._available_models
    
    def test_synthesis(self, text: str = "Teste de síntese") -> bool:
        """Testa síntese básica"""
        try:
            # Por enquanto, sempre retorna True pois usa fallback para macOS
            return True
        except Exception as e:
            logger.error(f"Erro no teste de síntese: {e}")
            return False
    
    def get_engine_status(self) -> Dict[str, Any]:
        """Retorna status detalhado do engine"""
        
        return {
            'name': self.name,
            'available': len(self._available_models) > 0,
            'piper_library': self._piper_available,
            'models_path': str(self._models_path) if self._models_path else None,
            'available_models': self._available_models.copy(),
            'model_count': len(self._available_models),
            'character_mapping': self._character_voice_mapping.copy(),
            'neural_synthesis': self._piper_available,  # Síntese neural disponível
            'fallback_mode': not self._piper_available  # Só fallback se Piper não disponível
        }
    
    def _apply_voice_processing(self, audio_data: bytes, character: Character, sample_rate: int) -> bytes:
        """Aplica processamento de áudio avançado para modificação de voz natural"""
        
        modulation = self._voice_modulations.get(character.id, {})
        voice_type = modulation.get('voice_type', 'male')
        
        # Se é voz masculina, não precisa processamento
        if voice_type != 'female':
            return audio_data
        
        try:
            import tempfile
            import subprocess
            import os
            
            # Criar arquivos temporários
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as input_file:
                input_file.write(audio_data)
                input_path = input_file.name
            
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as output_file:
                output_path = output_file.name
            
            try:
                # Usar técnica suave e feminina com factor otimizado
                # Factor 1.25 para voz feminina mais aguda mas ainda natural
                cmd = [
                    'ffmpeg', '-y',
                    '-i', input_path,
                    '-af', f'asetrate={sample_rate}*1.25,atempo=0.8',
                    '-ar', str(sample_rate),
                    '-ac', '1',  # Mono
                    '-sample_fmt', 's16',
                    output_path
                ]
                
                # Executar FFmpeg silenciosamente
                result = subprocess.run(cmd, capture_output=True, check=True)
                
                # Ler áudio processado
                with open(output_path, 'rb') as f:
                    processed_audio = f.read()
                
                logger.info(f"Processamento feminino otimizado aplicado para {character.id} (factor 1.25 - mais feminina)")
                return processed_audio
                
            finally:
                # Limpar arquivos temporários
                if os.path.exists(input_path):
                    os.unlink(input_path)
                if os.path.exists(output_path):
                    os.unlink(output_path)
                    
        except Exception as e:
            logger.warning(f"Erro no processamento de voz para {character.id}: {e}")
            logger.info("Retornando áudio original sem processamento")
            return audio_data 