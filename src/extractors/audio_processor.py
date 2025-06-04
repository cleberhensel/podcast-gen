"""
Processador de Samples de Áudio
Processa e otimiza arquivos de áudio existentes para uso com engines TTS
"""

import logging
import shutil
from pathlib import Path
from typing import List, Optional, Union

from .base_extractor import BaseSampleExtractor

logger = logging.getLogger(__name__)

class AudioSampleProcessor(BaseSampleExtractor):
    """Processador de samples de áudio para otimização e conversão"""
    
    def __init__(self, output_dir: str = "static/speaker_samples"):
        super().__init__(output_dir)
    
    def extract_sample(self, source: str, **kwargs) -> Path:
        """Processa arquivo de áudio existente"""
        return self.process_file(Path(source), **kwargs)
    
    def process_file(self, input_file: Path, output_name: Optional[str] = None,
                    optimize: bool = True) -> Path:
        """
        Processa arquivo de áudio existente
        
        Args:
            input_file: Caminho para o arquivo de entrada
            output_name: Nome do arquivo de saída (sem extensão)
            optimize: Se deve otimizar para CoquiTTS
            
        Returns:
            Path para o arquivo processado
        """
        
        if not input_file.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {input_file}")
        
        # Nome de saída
        if not output_name:
            output_name = f"processed_{input_file.stem}"
        
        output_file = self.output_dir / f"{output_name}.wav"
        
        logger.info(f"🔄 Processando: {input_file}")
        logger.info(f"💾 Saída: {output_file}")
        
        try:
            if optimize:
                # Otimizar para CoquiTTS
                self.optimize_for_coqui(input_file, output_file)
            else:
                # Apenas converter para WAV se necessário
                if input_file.suffix.lower() == '.wav':
                    shutil.copy2(input_file, output_file)
                else:
                    self._convert_to_wav(input_file, output_file)
            
            # Validar resultado
            if not output_file.exists():
                raise RuntimeError("Falha ao processar arquivo")
            
            # Informações do resultado
            info = self.get_audio_info(output_file)
            file_size = output_file.stat().st_size
            
            logger.info(f"✅ Arquivo processado com sucesso!")
            logger.info(f"  📏 Tamanho: {file_size / 1024:.1f} KB")
            logger.info(f"  ⏱️ Duração: {info.get('duration', 0):.1f}s")
            logger.info(f"  📊 Sample Rate: {info.get('sample_rate', 0)}Hz")
            
            # Validar para CoquiTTS
            self.validate_for_coqui(output_file)
            
            return output_file
            
        except Exception as e:
            logger.error(f"❌ Erro no processamento: {e}")
            raise
    
    def _convert_to_wav(self, input_file: Path, output_file: Path) -> None:
        """Converte arquivo para WAV básico"""
        import subprocess
        
        ffmpeg_cmd = [
            'ffmpeg',
            '-i', str(input_file),
            '-c:a', 'pcm_s16le',  # PCM 16-bit
            '-y',
            str(output_file)
        ]
        
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, check=True)
        logger.debug(f"ffmpeg conversion output: {result.stderr}")
    
    def batch_process(self, input_dir: Union[str, Path], pattern: str = "*.wav",
                     optimize: bool = True) -> List[Path]:
        """
        Processa múltiplos arquivos em lote
        
        Args:
            input_dir: Diretório com arquivos de entrada
            pattern: Padrão de arquivos para processar
            optimize: Se deve otimizar para CoquiTTS
            
        Returns:
            Lista de arquivos processados
        """
        input_path = Path(input_dir)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Diretório não encontrado: {input_path}")
        
        files = list(input_path.glob(pattern))
        if not files:
            logger.warning(f"Nenhum arquivo encontrado com padrão '{pattern}' em {input_path}")
            return []
        
        logger.info(f"🔄 Processando {len(files)} arquivos em lote...")
        
        results = []
        for i, file in enumerate(files, 1):
            try:
                logger.info(f"📝 Arquivo {i}/{len(files)}: {file.name}")
                output_name = f"batch_{i:03d}_{file.stem}"
                
                processed_file = self.process_file(file, output_name, optimize)
                results.append(processed_file)
                
            except Exception as e:
                logger.error(f"❌ Erro no arquivo {file.name}: {e}")
                continue
        
        logger.info(f"✅ {len(results)}/{len(files)} arquivos processados com sucesso")
        return results
    
    def segment_audio(self, input_file: Path, segments: List[dict],
                     optimize: bool = True) -> List[Path]:
        """
        Segmenta arquivo de áudio em múltiplos samples
        
        Args:
            input_file: Arquivo de áudio para segmentar
            segments: Lista de dicts com 'start', 'duration', 'name'
            optimize: Se deve otimizar para CoquiTTS
            
        Returns:
            Lista de arquivos segmentados
        """
        
        if not input_file.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {input_file}")
        
        logger.info(f"✂️ Segmentando {input_file.name} em {len(segments)} partes...")
        
        results = []
        for i, segment in enumerate(segments, 1):
            try:
                start = segment['start']
                duration = segment.get('duration', 8)
                name = segment.get('name', f"{input_file.stem}_segment_{i}")
                
                logger.info(f"📝 Segmento {i}/{len(segments)}: {name}")
                
                output_file = self.output_dir / f"{name}.wav"
                
                # Extrair segmento
                self._extract_segment(input_file, output_file, start, duration, optimize)
                
                if output_file.exists():
                    results.append(output_file)
                    
                    # Validar resultado
                    self.validate_for_coqui(output_file)
                
            except Exception as e:
                logger.error(f"❌ Erro no segmento {i}: {e}")
                continue
        
        logger.info(f"✅ {len(results)}/{len(segments)} segmentos criados com sucesso")
        return results
    
    def _extract_segment(self, input_file: Path, output_file: Path,
                        start_time: int, duration: int, optimize: bool = True) -> None:
        """Extrai segmento específico do arquivo"""
        import subprocess
        
        if optimize:
            # Otimizar para CoquiTTS durante extração
            ffmpeg_cmd = [
                'ffmpeg',
                '-i', str(input_file),
                '-ss', str(start_time),
                '-t', str(duration),
                '-ar', '24000',  # 24kHz para CoquiTTS
                '-ac', '1',      # Mono
                '-c:a', 'pcm_f32le',  # Float32 PCM
                '-af', 'volume=0.8,highpass=f=80,lowpass=f=8000',
                '-y',
                str(output_file)
            ]
        else:
            # Extração básica
            ffmpeg_cmd = [
                'ffmpeg',
                '-i', str(input_file),
                '-ss', str(start_time),
                '-t', str(duration),
                '-c:a', 'pcm_s16le',
                '-y',
                str(output_file)
            ]
        
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, check=True)
        logger.debug(f"ffmpeg segment output: {result.stderr}")
    
    def clean_samples(self, min_duration: float = 3.0, max_duration: float = 60.0) -> None:
        """
        Remove samples que não atendem aos critérios de duração
        
        Args:
            min_duration: Duração mínima em segundos
            max_duration: Duração máxima em segundos
        """
        samples = list(self.output_dir.glob("*.wav"))
        
        if not samples:
            logger.info("Nenhum sample para limpar")
            return
        
        removed_count = 0
        
        for sample in samples:
            try:
                info = self.get_audio_info(sample)
                duration = info.get('duration', 0)
                
                if duration < min_duration or duration > max_duration:
                    logger.info(f"🗑️ Removendo {sample.name} (duração: {duration:.1f}s)")
                    sample.unlink()
                    removed_count += 1
                    
            except Exception as e:
                logger.error(f"Erro ao verificar {sample.name}: {e}")
        
        logger.info(f"🧹 Limpeza concluída: {removed_count} samples removidos")
    
    def analyze_samples(self) -> dict:
        """Analisa estatísticas dos samples disponíveis"""
        samples = list(self.output_dir.glob("*.wav"))
        
        if not samples:
            return {'count': 0, 'total_size': 0, 'total_duration': 0}
        
        total_size = 0
        total_duration = 0
        durations = []
        sample_rates = []
        
        for sample in samples:
            try:
                info = self.get_audio_info(sample)
                size = sample.stat().st_size
                duration = info.get('duration', 0)
                sample_rate = info.get('sample_rate', 0)
                
                total_size += size
                total_duration += duration
                durations.append(duration)
                sample_rates.append(sample_rate)
                
            except Exception as e:
                logger.error(f"Erro ao analisar {sample.name}: {e}")
        
        stats = {
            'count': len(samples),
            'total_size_mb': total_size / (1024 * 1024),
            'total_duration_min': total_duration / 60,
            'avg_duration': sum(durations) / len(durations) if durations else 0,
            'min_duration': min(durations) if durations else 0,
            'max_duration': max(durations) if durations else 0,
            'common_sample_rate': max(set(sample_rates), key=sample_rates.count) if sample_rates else 0
        }
        
        logger.info("📊 Estatísticas dos Samples:")
        logger.info(f"  📁 Total: {stats['count']} arquivos")
        logger.info(f"  📏 Tamanho total: {stats['total_size_mb']:.1f} MB")
        logger.info(f"  ⏱️ Duração total: {stats['total_duration_min']:.1f} min")
        logger.info(f"  📊 Duração média: {stats['avg_duration']:.1f}s")
        logger.info(f"  📊 Sample rate comum: {stats['common_sample_rate']}Hz")
        
        return stats 