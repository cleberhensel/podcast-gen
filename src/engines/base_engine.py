"""
Interface Base para Engines TTS
Define o contrato que todos os engines devem implementar
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import io
import logging

from ..models.character import Character
from ..models.dialogue import Dialogue

logger = logging.getLogger(__name__)

@dataclass
class TTSResult:
    """Resultado da síntese TTS"""
    audio_data: bytes
    format: str = "wav"
    sample_rate: int = 22050
    channels: int = 1
    duration: float = 0.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class BaseTTSEngine(ABC):
    """Interface base para todos os engines TTS"""
    
    def __init__(self, name: str):
        self.name = name
        self.config = {}
        self._available_voices = None
    
    @abstractmethod
    def synthesize(self, dialogue: Dialogue, character: Character) -> TTSResult:
        """
        Sintetiza fala usando TTS
        
        Args:
            dialogue: Diálogo a ser sintetizado
            character: Personagem que fala
            
        Returns:
            TTSResult com áudio gerado
        """
        pass
    
    @abstractmethod
    def get_available_voices(self) -> List[Dict[str, Any]]:
        """
        Retorna lista de vozes disponíveis
        
        Returns:
            Lista de dicionários com informações das vozes
        """
        return []
    
    @abstractmethod
    def is_voice_available(self, voice_id: str) -> bool:
        """
        Verifica se uma voz específica está disponível
        
        Args:
            voice_id: ID da voz
            
        Returns:
            True se disponível
        """
        available_voices = self.get_available_voices()
        return any(voice.get('id') == voice_id for voice in available_voices)
    
    def configure(self, config: Dict[str, Any]):
        """Configura o engine com parâmetros específicos"""
        self.config.update(config)
    
    def validate_character(self, character: Character) -> List[str]:
        """
        Valida se o personagem é compatível com este engine
        
        Args:
            character: Personagem a validar
            
        Returns:
            Lista de problemas encontrados (vazia se OK)
        """
        issues = []
        
        if not self.is_voice_available(character.voice_id):
            issues.append(f"Voz '{character.voice_id}' não disponível no engine {self.name}")
        
        # Validar configurações específicas
        if character.speed < 0.1 or character.speed > 3.0:
            issues.append(f"Velocidade {character.speed} fora do range suportado (0.1-3.0)")
        
        if character.pitch < 0.1 or character.pitch > 3.0:
            issues.append(f"Pitch {character.pitch} fora do range suportado (0.1-3.0)")
        
        if character.volume < 0.1 or character.volume > 2.0:
            issues.append(f"Volume {character.volume} fora do range suportado (0.1-2.0)")
        
        return issues
    
    def get_voice_info(self, voice_id: str) -> Optional[Dict[str, Any]]:
        """
        Retorna informações detalhadas sobre uma voz
        
        Args:
            voice_id: ID da voz
            
        Returns:
            Dicionário com informações da voz ou None se não encontrada
        """
        voices = self.get_available_voices()
        for voice in voices:
            if voice.get('id') == voice_id:
                return voice
        return None
    
    def configure_podcast_voices(self, male_voice: str = None, female_voice_1: str = None, female_voice_2: str = None, characters_in_script: set = None):
        """
        Configura vozes para um podcast específico de forma consistente
        
        MÉTODO BASE - Implementações específicas devem sobrescrever
        
        Args:
            male_voice: Caminho para voz masculina (será usada para HOST_MALE)
            female_voice_1: Primeira opção de voz feminina 
            female_voice_2: Segunda opção de voz feminina (fallback)
            characters_in_script: Set com IDs dos personagens no roteiro
        """
        logger.info(f"🎭 Engine {self.name} não suporta configuração de vozes específicas")
        logger.info(f"   • Usando vozes padrão do engine")
        
        # Para engines que não suportam vozes específicas, apenas log
        if male_voice:
            logger.debug(f"   • Voz masculina ignorada: {male_voice}")
        if female_voice_1:
            logger.debug(f"   • Voz feminina ignorada: {female_voice_1}")

    def test_synthesis(self, text: str = "Teste de síntese de voz") -> bool:
        """
        Testa se o engine está funcionando
        
        Args:
            text: Texto de teste
            
        Returns:
            True se funcionando
        """
        try:
            # Implementação básica - tentar síntese com personagem padrão
            from ..models.character import Character
            from ..models.dialogue import Dialogue
            
            test_character = Character(
                id="test",
                name="Test Speaker",
                voice_id="default"
            )
            
            test_dialogue = Dialogue(
                character_id="test",
                text=text[:50]  # Texto curto para teste
            )
            
            result = self.synthesize(test_dialogue, test_character)
            return result is not None and len(result.audio_data) > 0
            
        except Exception as e:
            logger.debug(f"Teste de síntese falhou: {e}")
            return False
    
    def get_engine_info(self) -> Dict[str, Any]:
        """
        Retorna informações sobre o engine
        
        Returns:
            Dicionário com informações do engine
        """
        return {
            'name': self.name,
            'available_voices': len(self.get_available_voices()),
            'config': self.config,
            'test_status': self.test_synthesis()
        } 