"""
Engine TTS para macOS
Implementa síntese usando o comando 'say' nativo do macOS
"""

import subprocess
import tempfile
import os
import re
from typing import List, Dict, Any
import wave
import struct

from .base_engine import BaseTTSEngine, TTSResult
from ..models.character import Character
from ..models.dialogue import Dialogue

class MacOSTTSEngine(BaseTTSEngine):
    """Engine TTS usando comando 'say' do macOS"""
    
    def __init__(self):
        super().__init__("macOS")
        self._voices_cache = None
    
    def synthesize(self, dialogue: Dialogue, character: Character) -> TTSResult:
        """Sintetiza fala usando comando 'say' do macOS"""
        
        # Mapear voice_id para nome correto do macOS
        mapped_voice = self._map_voice_name(character.voice_id)
        
        # Processar texto com marcações
        processed_text = dialogue.get_processed_text()
        
        # Obter modificadores de emoção
        emotion_mods = dialogue.get_emotion_modifiers()
        
        # Calcular parâmetros finais
        final_speed = character.speed * emotion_mods.get('speed', 1.0)
        final_pitch = character.pitch * emotion_mods.get('pitch', 1.0)  
        final_volume = character.volume * emotion_mods.get('volume', 1.0)
        
        # Aplicar overrides do diálogo
        if dialogue.override_speed:
            final_speed = dialogue.override_speed
        if dialogue.override_pitch:
            final_pitch = dialogue.override_pitch
        if dialogue.override_volume:
            final_volume = dialogue.override_volume
        
        # Criar arquivos temporários
        with tempfile.NamedTemporaryFile(suffix='.aiff', delete=False) as temp_aiff:
            temp_aiff_path = temp_aiff.name
            
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
            temp_wav_path = temp_wav.name
        
        try:
            # Construir comando 'say' para gerar AIFF
            cmd = [
                'say',
                '-v', mapped_voice,  # Usar voz mapeada
                '-r', str(int(200 * final_speed)),  # Rate em palavras por minuto
                '-o', temp_aiff_path,
                processed_text
            ]
            
            # Executar comando
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"Erro no comando 'say': {result.stderr}")
            
            # Converter AIFF para WAV usando afconvert
            convert_cmd = [
                'afconvert',
                temp_aiff_path,
                temp_wav_path,
                '-d', 'LEI16',  # Linear PCM 16-bit Little Endian
                '-f', 'WAVE'    # Formato WAV
            ]
            
            convert_result = subprocess.run(convert_cmd, capture_output=True, text=True)
            
            if convert_result.returncode != 0:
                raise Exception(f"Erro na conversão para WAV: {convert_result.stderr}")
            
            # Ler arquivo WAV gerado
            with open(temp_wav_path, 'rb') as f:
                audio_data = f.read()
            
            # Calcular duração estimada
            duration = dialogue.get_estimated_duration()
            
            return TTSResult(
                audio_data=audio_data,
                format="wav",
                sample_rate=22050,
                channels=1,
                duration=duration,
                metadata={
                    'engine': 'macos',
                    'voice': mapped_voice,  # Usar voz mapeada nos metadados
                    'speed': final_speed,
                    'pitch': final_pitch,
                    'volume': final_volume,
                    'emotion': dialogue.emotion.value
                }
            )
            
        finally:
            # Limpar arquivos temporários
            for temp_path in [temp_aiff_path, temp_wav_path]:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
    
    def _map_voice_name(self, voice_id: str) -> str:
        """
        Mapeia nome de voz para formato correto do macOS
        
        Args:
            voice_id: ID da voz (pode ser nome curto ou completo)
            
        Returns:
            Nome da voz no formato esperado pelo macOS
        """
        # Se já está no formato completo, usar diretamente
        if '(' in voice_id and ')' in voice_id:
            return voice_id
        
        # Mapeamento de nomes curtos para nomes completos em português
        voice_mapping = {
            'Eddy': 'Eddy (Português (Brasil))',
            'Flo': 'Flo (Português (Brasil))',
            'Reed': 'Reed (Português (Brasil))',
            'Rocko': 'Rocko (Português (Brasil))',
            'Sandy': 'Sandy (Português (Brasil))',
            'Grandpa': 'Grandpa (Português (Brasil))',
            'Grandma': 'Grandma (Português (Brasil))',
            'Shelley': 'Shelley (Português (Brasil))',
            # Luciana é nativa em português, não tem parênteses
            'Luciana': 'Luciana',
            # Vozes em inglês como fallback
            'Alex': 'Alex',
            'Samantha': 'Samantha',
            'Daniel': 'Daniel',
            'Victoria': 'Victoria'
        }
        
        mapped_voice = voice_mapping.get(voice_id, voice_id)
        
        # Verificar se a voz mapeada existe
        if self.is_voice_available(mapped_voice):
            return mapped_voice
        
        # Fallback para Luciana (voz mais confiável em português)
        print(f"[WARNING] Voz '{voice_id}' não encontrada, usando fallback: Luciana")
        return 'Luciana'
    
    def get_available_voices(self) -> List[Dict[str, Any]]:
        """Retorna lista de vozes disponíveis do macOS"""
        
        if self._voices_cache is not None:
            return self._voices_cache
        
        try:
            # Executar comando para listar vozes
            result = subprocess.run(['say', '-v', '?'], capture_output=True, text=True)
            
            if result.returncode != 0:
                return []
            
            voices = []
            for line in result.stdout.strip().split('\n'):
                if not line.strip():
                    continue
                
                # Parse da linha melhorado para nomes complexos com parênteses
                # Formato: "Nome da Voz    idioma_codigo    # Descrição"
                # Exemplo: "Eddy (Português (Brasil)) pt_BR    # Olá, meu nome é Eddy."
                
                # Separar por # primeiro para isolar a descrição
                if '#' in line:
                    voice_part, description = line.split('#', 1)
                    description = description.strip()
                else:
                    voice_part = line
                    description = ""
                
                # Parse da parte da voz (nome + idioma)
                # Usar regex mais flexível
                match = re.match(r'^(.+?)\s+([a-z_]+(?:_[A-Z0-9]+)?)\s*$', voice_part.strip())
                if match:
                    voice_name = match.group(1).strip()
                    language = match.group(2).strip()
                    
                    # Extrair nome base (sem parênteses para compatibilidade)
                    base_name = voice_name.split(' (')[0].strip()
                    
                    # Determinar gênero e características
                    gender = self._determine_voice_gender(base_name, description)
                    quality = self._determine_voice_quality(base_name, description)
                    
                    voices.append({
                        'id': base_name,  # Usar nome base para compatibilidade
                        'name': voice_name,  # Nome completo para exibição
                        'language': language,
                        'description': description,
                        'gender': gender,
                        'quality': quality,
                        'engine': 'macos'
                    })
            
            self._voices_cache = voices
            return voices
            
        except Exception as e:
            print(f"Erro listando vozes: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def is_voice_available(self, voice_id: str) -> bool:
        """Verifica se uma voz está disponível"""
        voices = self.get_available_voices()
        
        # Verificar correspondência exata
        for voice in voices:
            if voice['id'] == voice_id or voice['name'] == voice_id:
                return True
        
        # Se não encontrou correspondência exata, verificar nome base
        if '(' in voice_id:
            base_name = voice_id.split(' (')[0].strip()
            for voice in voices:
                if voice['id'] == base_name:
                    return True
        
        return False
    
    def _determine_voice_gender(self, voice_name: str, description: str) -> str:
        """Determina gênero da voz baseado no nome e descrição"""
        
        # Vozes masculinas conhecidas
        male_voices = {
            'Alex', 'Daniel', 'Tom', 'Fred', 'Ralph', 'Junior', 'Albert',
            'Bruce', 'Jorge', 'Diego', 'Carlos', 'Joaquim'
        }
        
        # Vozes femininas conhecidas  
        female_voices = {
            'Samantha', 'Victoria', 'Kate', 'Susan', 'Allison', 'Ava',
            'Karen', 'Sarah', 'Monica', 'Paulina', 'Francisca', 'Luciana'
        }
        
        if voice_name in male_voices:
            return 'male'
        elif voice_name in female_voices:
            return 'female'
        else:
            # Tentar deduzir pela descrição
            desc_lower = description.lower()
            if any(word in desc_lower for word in ['female', 'woman', 'girl']):
                return 'female'
            elif any(word in desc_lower for word in ['male', 'man', 'boy']):
                return 'male'
            else:
                return 'neutral'
    
    def _determine_voice_quality(self, voice_name: str, description: str) -> str:
        """Determina qualidade da voz"""
        
        # Vozes de alta qualidade
        high_quality = {'Alex', 'Samantha', 'Victoria', 'Daniel', 'Karen'}
        
        # Vozes médias
        medium_quality = {'Tom', 'Kate', 'Susan', 'Fred'}
        
        if voice_name in high_quality:
            return 'high'
        elif voice_name in medium_quality:
            return 'medium'
        else:
            return 'standard'
    
    def get_portuguese_voices(self) -> List[Dict[str, Any]]:
        """Retorna apenas vozes em português"""
        all_voices = self.get_available_voices()
        
        portuguese_voices = []
        for voice in all_voices:
            lang = voice.get('language', '').lower()
            name = voice.get('name', '').lower()
            desc = voice.get('description', '').lower()
            
            # Verificar se é voz em português
            if ('pt' in lang or 'br' in lang or 
                'brazilian' in desc or 'portuguese' in desc or
                name in ['luciana', 'joaquim', 'francisca']):
                portuguese_voices.append(voice)
        
        return portuguese_voices
    
    def test_voice(self, voice_id: str, text: str = "Teste de voz") -> bool:
        """Testa uma voz específica"""
        try:
            with tempfile.NamedTemporaryFile(suffix='.aiff', delete=False) as temp_aiff:
                temp_aiff_path = temp_aiff.name
                
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
                temp_wav_path = temp_wav.name
            
            # Gerar AIFF
            cmd = ['say', '-v', voice_id, '-o', temp_aiff_path, text]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                return False
            
            # Converter para WAV
            convert_cmd = ['afconvert', temp_aiff_path, temp_wav_path, '-d', 'LEI16', '-f', 'WAVE']
            convert_result = subprocess.run(convert_cmd, capture_output=True, text=True)
            
            success = convert_result.returncode == 0 and os.path.exists(temp_wav_path)
            
            # Limpar
            for temp_path in [temp_aiff_path, temp_wav_path]:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            
            return success
            
        except Exception:
            return False
    
    def get_voice_sample(self, voice_id: str, text: str = "Exemplo de fala") -> bytes:
        """Gera amostra de áudio para uma voz"""
        from ..models.dialogue import Dialogue
        from ..models.character import Character, Gender, VoiceStyle
        
        # Criar personagem temporário
        temp_char = Character(
            name="Teste",
            id="test",
            gender=Gender.NEUTRAL,
            voice_id=voice_id,
            voice_style=VoiceStyle.CONVERSATIONAL
        )
        
        # Criar diálogo temporário
        temp_dialogue = Dialogue(
            character_id="test",
            text=text,
            sequence=1
        )
        
        result = self.synthesize(temp_dialogue, temp_char)
        return result.audio_data 