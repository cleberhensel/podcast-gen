"""
Parser de Roteiros para Podcast TTS
Converte roteiros em texto para objetos Podcast estruturados
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from ..models.podcast import Podcast, PodcastMetadata
from ..models.dialogue import Dialogue, parse_dialogue_markup, EmotionType
from ..models.character import Character, DEFAULT_CHARACTERS, Gender, VoiceStyle

class ScriptParser:
    """Parser de roteiros de podcast"""
    
    def __init__(self):
        self.character_map = {}
        self.auto_assign_characters = True
        
    def parse_file(self, file_path: str, **kwargs) -> Podcast:
        """Parse de arquivo de roteiro"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        title = Path(file_path).stem
        return self.parse_content(content, title=title, **kwargs)
    
    def parse_content(self, content: str, title: str = "Podcast", **kwargs) -> Podcast:
        """Parse de conteúdo de roteiro"""
        
        # Extrair título se presente
        title_match = re.search(r'^#\s*(.+)$', content, re.MULTILINE)
        if title_match:
            title = title_match.group(1).strip()
        
        # Criar metadata
        metadata = PodcastMetadata(
            title=title,
            description=kwargs.get('description'),
            category=kwargs.get('category', 'Technology'),
            author=kwargs.get('author', 'Podcast Generator TTS'),
            language=kwargs.get('language', 'pt-BR')
        )
        
        # Criar podcast
        podcast = Podcast(
            title=title,
            metadata=metadata,
            max_duration=kwargs.get('max_duration', 900),  # 15 min
            max_segment_duration=kwargs.get('max_segment_duration', 60)
        )
        
        # Parse dos diálogos
        dialogues = self._parse_dialogues(content)
        
        # Auto-atribuir personagens se necessário
        if self.auto_assign_characters:
            self._auto_assign_characters(dialogues)
        
        # Adicionar personagens ao podcast
        for char_id in set(d['character_id'] for d in dialogues):
            if char_id in self.character_map:
                podcast.add_character(self.character_map[char_id])
            elif char_id.upper() in DEFAULT_CHARACTERS:
                podcast.add_character(DEFAULT_CHARACTERS[char_id.upper()])
        
        # Adicionar diálogos ao podcast
        for i, dialogue_data in enumerate(dialogues, 1):
            dialogue = Dialogue(
                character_id=dialogue_data['character_id'],
                text=dialogue_data['text'],
                sequence=i,
                emotion=dialogue_data.get('emotion', EmotionType.NEUTRAL),
                emphasis_words=dialogue_data.get('emphasis_words', []),
                slow_words=dialogue_data.get('slow_words', []),
                loud_words=dialogue_data.get('loud_words', []),
                pause_before=dialogue_data.get('pause_before', 0.0),
                pause_after=dialogue_data.get('pause_after', 0.5),
                override_speed=dialogue_data.get('override_speed'),
                override_pitch=dialogue_data.get('override_pitch'),
                override_volume=dialogue_data.get('override_volume')
            )
            podcast.dialogues.append(dialogue)
        
        return podcast
    
    def _parse_dialogues(self, content: str) -> List[Dict[str, Any]]:
        """Extrai diálogos do conteúdo"""
        dialogues = []
        
        # Pattern para capturar diálogos: [PERSONAGEM]: Texto ou PERSONAGEM: Texto
        pattern = r'^(?:\[([^\]]+)\]|([A-Z_]+)):\s*(.+)$'
        
        for line in content.split('\n'):
            line = line.strip()
            
            # Pular linhas vazias, comentários e títulos
            if not line or line.startswith('#') or line.startswith('//'):
                continue
            
            match = re.match(pattern, line)
            if match:
                # Primeiro grupo: [PERSONAGEM], segundo grupo: PERSONAGEM simples
                character_id = (match.group(1) or match.group(2)).strip().upper()
                text = match.group(3).strip()
                
                # Parse de marcações no texto
                markup_data = parse_dialogue_markup(text)
                
                dialogue_data = {
                    'character_id': character_id,
                    'text': markup_data['text'],
                    'emotion': markup_data.get('emotion', EmotionType.NEUTRAL),
                    'emphasis_words': markup_data.get('emphasis_words', []),
                    'slow_words': markup_data.get('slow_words', []),
                    'loud_words': markup_data.get('loud_words', []),
                    'pause_after': markup_data.get('pause_after', 0.5),
                    'override_speed': markup_data.get('override_speed'),
                    'override_pitch': markup_data.get('override_pitch'),
                    'override_volume': markup_data.get('override_volume')
                }
                
                dialogues.append(dialogue_data)
        
        return dialogues
    
    def _auto_assign_characters(self, dialogues: List[Dict[str, Any]]):
        """Auto-atribui personagens baseado nos IDs encontrados"""
        
        # Mapear IDs encontrados para personagens padrão
        for dialogue in dialogues:
            char_id = dialogue['character_id']
            
            if char_id not in self.character_map:
                # Tentar mapear para personagem padrão
                if char_id in DEFAULT_CHARACTERS:
                    self.character_map[char_id] = DEFAULT_CHARACTERS[char_id]
                else:
                    # Criar personagem baseado no padrão do ID
                    self.character_map[char_id] = self._create_character_from_id(char_id)
    
    def _create_character_from_id(self, char_id: str) -> Character:
        """Cria personagem baseado no ID"""
        
        # Analisar padrão do ID
        char_id_lower = char_id.lower()
        
        # Determinar gênero
        if '_m' in char_id_lower or 'male' in char_id_lower:
            gender = Gender.MALE
        elif '_f' in char_id_lower or 'female' in char_id_lower:
            gender = Gender.FEMALE
        else:
            gender = Gender.NEUTRAL
        
        # Determinar papel
        if 'host' in char_id_lower:
            role = 'host'
            voice_style = VoiceStyle.AUTHORITATIVE
        elif 'expert' in char_id_lower:
            role = 'expert'
            voice_style = VoiceStyle.FORMAL
        elif 'guest' in char_id_lower:
            role = 'guest'
            voice_style = VoiceStyle.CONVERSATIONAL
        elif 'narrator' in char_id_lower:
            role = 'narrator'
            voice_style = VoiceStyle.CALM
        else:
            role = 'speaker'
            voice_style = VoiceStyle.CONVERSATIONAL
        
        # Escolher voz baseada no gênero
        if gender == Gender.MALE:
            voice_options = ['Alex', 'Daniel', 'Tom', 'Fred']
        elif gender == Gender.FEMALE:
            voice_options = ['Samantha', 'Victoria', 'Kate', 'Susan']
        else:
            voice_options = ['Alex', 'Samantha']
        
        # Usar primeira voz disponível ou Alex como fallback
        voice_id = voice_options[0] if voice_options else 'Alex'
        
        return Character(
            name=char_id.replace('_', ' ').title(),
            id=char_id,
            gender=gender,
            voice_id=voice_id,
            voice_style=voice_style,
            role=role,
            description=f"Personagem {role} auto-gerado"
        )
    
    def add_custom_character(self, char_id: str, character: Character):
        """Adiciona personagem customizado"""
        self.character_map[char_id.upper()] = character
    
    def load_characters_from_file(self, file_path: str):
        """Carrega personagens de arquivo YAML"""
        import yaml
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        for char_id, char_data in data.items():
            character = Character.from_dict(char_data)
            self.add_custom_character(char_id, character)
    
    def validate_script(self, content: str) -> List[str]:
        """Valida roteiro e retorna lista de problemas"""
        issues = []
        
        dialogues = self._parse_dialogues(content)
        
        if not dialogues:
            issues.append("Nenhum diálogo encontrado no roteiro")
        
        # Verificar personagens
        character_ids = set(d['character_id'] for d in dialogues)
        
        for char_id in character_ids:
            if (char_id not in DEFAULT_CHARACTERS and 
                char_id not in self.character_map):
                issues.append(f"Personagem '{char_id}' não definido")
        
        # Verificar comprimento dos textos
        for i, dialogue in enumerate(dialogues, 1):
            text_length = len(dialogue['text'])
            if text_length > 500:
                issues.append(f"Diálogo {i} muito longo ({text_length} caracteres)")
            elif text_length < 10:
                issues.append(f"Diálogo {i} muito curto ({text_length} caracteres)")
        
        # Verificar diversidade de personagens
        if len(character_ids) < 2:
            issues.append("Recomenda-se pelo menos 2 personagens para maior dinâmica")
        
        return issues
    
    def get_script_statistics(self, content: str) -> Dict[str, Any]:
        """Retorna estatísticas do roteiro"""
        dialogues = self._parse_dialogues(content)
        
        character_counts = {}
        total_words = 0
        total_chars = 0
        
        for dialogue in dialogues:
            char_id = dialogue['character_id']
            text = dialogue['text']
            
            character_counts[char_id] = character_counts.get(char_id, 0) + 1
            total_words += len(text.split())
            total_chars += len(text)
        
        # Estimar duração (150 palavras por minuto)
        estimated_duration = (total_words / 150) * 60
        
        return {
            'total_dialogues': len(dialogues),
            'total_characters': len(character_counts),
            'character_distribution': character_counts,
            'total_words': total_words,
            'total_characters': total_chars,
            'estimated_duration_seconds': estimated_duration,
            'estimated_duration_minutes': estimated_duration / 60,
            'average_words_per_dialogue': total_words / len(dialogues) if dialogues else 0
        } 