"""
Interface Base para Engines TTS
Define o contrato que todos os engines devem implementar
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import io

from ..models.character import Character
from ..models.dialogue import Dialogue

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
        pass
    
    @abstractmethod
    def is_voice_available(self, voice_id: str) -> bool:
        """
        Verifica se uma voz específica está disponível
        
        Args:
            voice_id: ID da voz
            
        Returns:
            True se a voz estiver disponível
        """
        pass
    
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
    
    def test_synthesis(self, text: str = "Teste de síntese de voz") -> bool:
        """
        Testa se o engine está funcionando corretamente
        
        Args:
            text: Texto de teste
            
        Returns:
            True se o teste foi bem-sucedido
        """
        try:
            from ..models.dialogue import Dialogue
            from ..models.character import Character, Gender, VoiceStyle
            
            # Criar personagem de teste simples
            voices = self.get_available_voices()
            if not voices:
                return False
            
            # Usar primeira voz disponível
            test_voice = voices[0]['id']
            
            test_char = Character(
                name="Teste",
                id="test",
                gender=Gender.NEUTRAL,
                voice_id=test_voice,
                voice_style=VoiceStyle.CONVERSATIONAL
            )
            
            test_dialogue = Dialogue(
                character_id=test_char.id,
                text=text,
                sequence=1
            )
            
            result = self.synthesize(test_dialogue, test_char)
            return len(result.audio_data) > 0
            
        except Exception as e:
            print(f"Erro no teste de síntese: {e}")
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