"""
Gerador Principal de Podcast TTS
Orquestra todo o processo de geração de podcasts
"""

import os
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
import concurrent.futures
from datetime import datetime
import time

from ..models.podcast import Podcast
from ..models.dialogue import Dialogue
from ..models.character import Character
from ..engines.base_engine import BaseTTSEngine, TTSResult
from ..engines.engine_factory import tts_factory
from .script_parser import ScriptParser
from .audio_processor import AudioProcessor

# 🚀 INTEGRAÇÃO COM PLATAFORMA
try:
    from ..platform import current_platform
    from .performance_monitor import PerformanceMonitor
    PLATFORM_AVAILABLE = True
except ImportError:
    PLATFORM_AVAILABLE = False
    current_platform = None
    PerformanceMonitor = None

logger = logging.getLogger(__name__)

class PodcastGenerator:
    """Gerador principal de podcasts TTS"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # 🚀 CONFIGURAÇÃO BASEADA NA PLATAFORMA
        if PLATFORM_AVAILABLE and current_platform:
            # Aplicar otimizações da plataforma
            current_platform.initialize_optimizations()
            
            # Obter configurações de performance da plataforma
            platform_config = current_platform.get_performance_config()
            
            # Usar configurações da plataforma como padrão
            self.max_workers = self.config.get('performance', {}).get('max_workers', platform_config['max_workers'])
            self.batch_size = platform_config['batch_size']
            
            logger.info(f"🚀 PodcastGenerator configurado para {platform_config['platform_type']}")
            logger.info(f"🚀 Workers: {self.max_workers} | Batch: {self.batch_size}")
        else:
            # Configurações padrão se plataforma não disponível
            self.max_workers = self.config.get('performance', {}).get('max_workers', 4)
            self.batch_size = 5
            logger.warning("🚀 PodcastGenerator usando configurações padrão")
        
        # Configurar engine TTS
        self.engine = self._setup_engine()
        
        # Configurar processador de áudio
        self.audio_processor = AudioProcessor(config)
        
        # Configurar parser de scripts
        self.script_parser = ScriptParser()
        
        # 📊 MONITOR DE PERFORMANCE
        self.performance_monitor = PerformanceMonitor(current_platform) if PerformanceMonitor else None
        
        # Configurações de saída
        self.output_dir = Path(self.config.get('output', {}).get('default_directory', 'output/final'))
        self.segments_dir = Path(self.config.get('output', {}).get('segments_directory', 'output/segments'))
        self.temp_dir = Path(self.config.get('output', {}).get('temp_directory', 'output/temp'))
        
        # Criar diretórios se não existirem
        for directory in [self.output_dir, self.segments_dir, self.temp_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Configurações de performance
        self.parallel_synthesis = self.config.get('performance', {}).get('parallel_synthesis', True)
    
    def _setup_engine(self) -> BaseTTSEngine:
        """Configura engine TTS baseado na configuração usando Factory Pattern"""
        
        # Obter engine preferido da configuração
        preferred_engine = self.config.get('engines', {}).get('default', 'macos')
        
        # Configurações específicas do engine
        engine_config = self.config.get('engines', {}).get(preferred_engine, {})
        
        try:
            # Usar factory com fallback automático
            logger.info(f"Configurando engine TTS: {preferred_engine}")
            
            engine = tts_factory.create_engine_with_fallback(
                preferred_engine=preferred_engine,
                config=engine_config
            )
            
            logger.info(f"Engine TTS configurado: {engine.name}")
            
            # Log de engines disponíveis
            available_engines = tts_factory.get_available_engines()
            logger.debug(f"Engines disponíveis: {available_engines}")
            
            return engine
            
        except Exception as e:
            logger.error(f"Erro configurando engine TTS: {e}")
            
            # Fallback de emergência - tentar qualquer engine disponível
            try:
                available_engines = tts_factory.get_available_engines()
                if available_engines:
                    emergency_engine = available_engines[0]
                    logger.warning(f"Usando engine de emergência: {emergency_engine}")
                    return tts_factory.create_engine(emergency_engine, engine_config)
                else:
                    raise RuntimeError("Nenhum engine TTS disponível")
            except Exception as fallback_error:
                logger.critical(f"Falha total na configuração de TTS: {fallback_error}")
                raise RuntimeError("Sistema TTS completamente indisponível")
    
    def generate_from_script_file(self, script_file: str, output_file: Optional[str] = None, **kwargs) -> str:
        """Gera podcast a partir de arquivo de roteiro"""
        
        logger.info(f"Iniciando geração de podcast: {script_file}")
        
        # Parse do roteiro
        podcast = self.script_parser.parse_file(script_file, **kwargs)
        
        # Gerar podcast
        return self.generate_podcast(podcast, output_file)
    
    def generate_from_content(self, content: str, title: str = "Podcast", output_file: Optional[str] = None, **kwargs) -> str:
        """Gera podcast a partir de conteúdo de roteiro"""
        
        logger.info(f"Iniciando geração de podcast: {title}")
        
        # Parse do conteúdo
        podcast = self.script_parser.parse_content(content, title=title, **kwargs)
        
        # Gerar podcast
        return self.generate_podcast(podcast, output_file)
    
    def generate_podcast(self, podcast: Podcast, output_file: Optional[str] = None) -> str:
        """Gera podcast completo"""
        
        # Validar podcast
        issues = podcast.validate()
        if issues:
            logger.warning(f"Problemas encontrados no podcast: {issues}")
        
        # Determinar arquivo de saída
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.output_dir / f"{podcast.title}_{timestamp}.{podcast.output_format}"
        else:
            output_file = Path(output_file)
        
        logger.info(f"Gerando podcast: {podcast.title}")
        logger.info(f"Total de diálogos: {len(podcast.dialogues)}")
        logger.info(f"Duração estimada: {podcast.get_total_estimated_duration():.1f}s")
        
        # 📊 INICIAR MONITORAMENTO DE PERFORMANCE
        if self.performance_monitor:
            self.performance_monitor.start_monitoring(len(podcast.dialogues))
        
        # 🚀 MOSTRAR INFORMAÇÕES DA PLATAFORMA
        if PLATFORM_AVAILABLE and current_platform:
            if hasattr(current_platform, 'print_optimization_summary'):
                current_platform.print_optimization_summary()
            else:
                logger.debug("Plataforma não tem método print_optimization_summary")
        
        try:
            # Gerar segmentos de áudio
            segment_files = self._generate_audio_segments(podcast)
            
            # Combinar segmentos
            final_file = self._combine_segments(segment_files, output_file, podcast)
            
            # Limpeza opcional
            if not self.config.get('output', {}).get('keep_segments', True):
                self._cleanup_segments(segment_files)
            
            logger.info(f"Podcast gerado com sucesso: {final_file}")
            return str(final_file)
            
        finally:
            # 📊 PARAR MONITORAMENTO E GERAR RELATÓRIO
            if self.performance_monitor:
                self.performance_monitor.stop_monitoring()
    
    def _generate_audio_segments(self, podcast: Podcast) -> List[Path]:
        """Gera segmentos de áudio individuais"""
        
        segment_files = []
        
        if self.parallel_synthesis and len(podcast.dialogues) > 1:
            # Geração paralela
            logger.info("Gerando segmentos em paralelo...")
            segment_files = self._generate_segments_parallel(podcast)
        else:
            # Geração sequencial
            logger.info("Gerando segmentos sequencialmente...")
            segment_files = self._generate_segments_sequential(podcast)
        
        return segment_files
    
    def _generate_segments_sequential(self, podcast: Podcast) -> List[Path]:
        """Gera segmentos sequencialmente"""
        segment_files = []
        
        for i, dialogue in enumerate(podcast.dialogues, 1):
            logger.info(f"Gerando segmento {i}/{len(podcast.dialogues)}: {dialogue.character_id}")
            
            # 📊 TIMING DO SEGMENTO
            segment_start = time.time()
            
            character = podcast.characters[dialogue.character_id]
            segment_file = self._generate_single_segment(dialogue, character, i)
            
            if segment_file:
                segment_files.append(segment_file)
                
                # 📊 ATUALIZAR MONITOR COM TEMPO DO SEGMENTO
                segment_duration = time.time() - segment_start
                if self.performance_monitor:
                    self.performance_monitor.update_progress(i, segment_duration)
        
        return segment_files
    
    def _generate_segments_parallel(self, podcast: Podcast) -> List[Path]:
        """Gera segmentos em paralelo"""
        segment_files = [None] * len(podcast.dialogues)
        completed_count = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submeter tasks
            future_to_index = {}
            for i, dialogue in enumerate(podcast.dialogues):
                character = podcast.characters[dialogue.character_id]
                future = executor.submit(self._generate_single_segment, dialogue, character, i + 1)
                future_to_index[future] = i
            
            # Coletar resultados
            for future in concurrent.futures.as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    segment_file = future.result()
                    segment_files[index] = segment_file
                    completed_count += 1
                    
                    # 📊 ATUALIZAR MONITOR (paralelo não tem timing individual preciso)
                    if self.performance_monitor:
                        self.performance_monitor.update_progress(completed_count)
                        
                    logger.info(f"Segmento {index + 1} gerado: {segment_file}")
                except Exception as e:
                    logger.error(f"Erro gerando segmento {index + 1}: {e}")
        
        # Filtrar segmentos válidos
        return [f for f in segment_files if f is not None]
    
    def _generate_single_segment(self, dialogue: Dialogue, character: Character, segment_num: int) -> Optional[Path]:
        """Gera um único segmento de áudio"""
        
        try:
            # Sintetizar áudio
            result = self.engine.synthesize(dialogue, character)
            
            # Salvar segmento
            segment_file = self.segments_dir / f"segment_{segment_num:03d}_{character.id}.{result.format}"
            
            with open(segment_file, 'wb') as f:
                f.write(result.audio_data)
            
            logger.debug(f"Segmento salvo: {segment_file}")
            
            # 🧹 CLEANUP BASEADO NA PLATAFORMA A CADA SEGMENTO
            if PLATFORM_AVAILABLE and current_platform and hasattr(current_platform, 'should_cleanup_memory') and callable(current_platform.should_cleanup_memory) and current_platform.should_cleanup_memory():
                current_platform.cleanup_gpu_memory()
                logger.debug("🧹 Cleanup de memória executado")
            
            return segment_file
            
        except Exception as e:
            logger.error(f"Erro gerando segmento {segment_num}: {e}")
            return None
    
    def _combine_segments(self, segment_files: List[Path], output_file: Path, podcast: Podcast) -> Path:
        """Combina segmentos em arquivo final"""
        
        logger.info(f"Combinando {len(segment_files)} segmentos...")
        
        # Usar processador de áudio para combinar
        final_file = self.audio_processor.combine_segments(
            segment_files, 
            output_file,
            format=podcast.output_format,
            sample_rate=podcast.sample_rate,
            channels=podcast.channels,
            normalize=podcast.normalize_audio,
            apply_compression=podcast.apply_compression
        )
        
        # Gerar versão MP3 automaticamente
        self._generate_mp3_version(final_file)
        
        return final_file
    
    def _generate_mp3_version(self, wav_file: Path) -> Optional[Path]:
        """Gera versão MP3 do arquivo WAV"""
        
        try:
            import subprocess
            
            # Determinar arquivo MP3
            mp3_file = wav_file.with_suffix('.mp3')
            
            logger.info(f"Gerando versão MP3: {mp3_file}")
            
            # Comando ffmpeg para conversão
            cmd = [
                'ffmpeg',
                '-i', str(wav_file),
                '-codec:a', 'libmp3lame',
                '-b:a', '192k',
                '-y',  # Sobrescrever arquivo se existir
                str(mp3_file)
            ]
            
            # Executar conversão
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True,
                check=True
            )
            
            if mp3_file.exists():
                # Calcular informações do arquivo
                wav_size = wav_file.stat().st_size / (1024 * 1024)  # MB
                mp3_size = mp3_file.stat().st_size / (1024 * 1024)  # MB
                compression_ratio = (1 - mp3_size / wav_size) * 100
                
                logger.info(f"MP3 gerado com sucesso: {mp3_file}")
                logger.info(f"Tamanho WAV: {wav_size:.1f} MB")
                logger.info(f"Tamanho MP3: {mp3_size:.1f} MB")
                logger.info(f"Compressão: {compression_ratio:.1f}%")
                
                return mp3_file
            else:
                logger.error("Arquivo MP3 não foi criado")
                return None
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Erro na conversão ffmpeg: {e.stderr}")
            return None
        except FileNotFoundError:
            logger.warning("ffmpeg não encontrado. Instale com: brew install ffmpeg")
            logger.info("Pulando geração de MP3...")
            return None
        except Exception as e:
            logger.error(f"Erro inesperado gerando MP3: {e}")
            return None
    
    def _cleanup_segments(self, segment_files: List[Path]):
        """Remove arquivos de segmentos temporários"""
        logger.info("Limpando segmentos temporários...")
        
        for segment_file in segment_files:
            try:
                if segment_file.exists():
                    segment_file.unlink()
            except Exception as e:
                logger.warning(f"Erro removendo segmento {segment_file}: {e}")
    
    def generate_preview(self, podcast: Podcast, duration: float = 30.0) -> str:
        """Gera preview do podcast com duração limitada"""
        
        logger.info(f"Gerando preview de {duration}s")
        
        # Selecionar diálogos para o preview
        preview_dialogues = []
        current_duration = 0.0
        
        for dialogue in podcast.dialogues:
            estimated_duration = dialogue.get_estimated_duration()
            
            if current_duration + estimated_duration <= duration:
                preview_dialogues.append(dialogue)
                current_duration += estimated_duration
            else:
                break
        
        # Criar podcast temporário para preview
        preview_podcast = Podcast(
            title=f"{podcast.title} - Preview",
            metadata=podcast.metadata,
            dialogues=preview_dialogues,
            characters=podcast.characters
        )
        
        # Gerar preview no diretório temp configurado
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.temp_dir / f"{podcast.title}_preview_{timestamp}.wav"
        return self.generate_podcast(preview_podcast, output_file)
    
    def validate_setup(self) -> Dict[str, Any]:
        """Valida configuração do gerador"""
        
        validation_result = {
            'engine_status': 'unknown',
            'voices_available': 0,
            'directories_ok': False,
            'issues': []
        }
        
        # Testar engine
        try:
            if self.engine.test_synthesis():
                validation_result['engine_status'] = 'ok'
            else:
                validation_result['engine_status'] = 'error'
                validation_result['issues'].append("Engine TTS não está funcionando")
        except Exception as e:
            validation_result['engine_status'] = 'error'
            validation_result['issues'].append(f"Erro testando engine: {e}")
        
        # Verificar vozes
        try:
            voices = self.engine.get_available_voices()
            validation_result['voices_available'] = len(voices)
            
            if len(voices) == 0:
                validation_result['issues'].append("Nenhuma voz TTS disponível")
        except Exception as e:
            validation_result['issues'].append(f"Erro listando vozes: {e}")
        
        # Verificar diretórios
        try:
            for directory in [self.output_dir, self.segments_dir, self.temp_dir]:
                if not directory.exists():
                    directory.mkdir(parents=True, exist_ok=True)
            validation_result['directories_ok'] = True
        except Exception as e:
            validation_result['issues'].append(f"Erro criando diretórios: {e}")
        
        return validation_result
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas do gerador"""
        
        return {
            'engine': self.engine.name,
            'available_voices': len(self.engine.get_available_voices()),
            'output_directory': str(self.output_dir),
            'parallel_synthesis': self.parallel_synthesis,
            'max_workers': self.max_workers,
            'config': self.config
        } 