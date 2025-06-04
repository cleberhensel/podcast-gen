"""
Classe Base para Extratores de Samples de Áudio
"""

import logging
import subprocess
import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class BaseSampleExtractor(ABC):
    """Classe base para extratores de samples de áudio"""
    
    def __init__(self, output_dir: str = "static/speaker_samples"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    @abstractmethod
    def extract_sample(self, source: str, **kwargs) -> Path:
        """Extrai sample de áudio da fonte especificada"""
        pass
    
    def check_dependencies(self) -> bool:
        """Verifica se as dependências necessárias estão disponíveis"""
        return self._check_ffmpeg()
    
    def _check_ffmpeg(self) -> bool:
        """Verifica se ffmpeg está disponível"""
        try:
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True, check=True)
            version_line = result.stdout.split('\n')[0]
            logger.info(f"ffmpeg disponível: {version_line}")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.error("ffmpeg não encontrado!")
            return False
    
    def get_audio_info(self, audio_file: Path) -> Dict[str, Any]:
        """Obtém informações detalhadas do arquivo de áudio"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_streams',
                '-show_format',
                str(audio_file)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            
            # Extrair informações principais
            stream = data['streams'][0]
            format_info = data['format']
            
            return {
                'duration': float(format_info.get('duration', 0)),
                'sample_rate': int(stream.get('sample_rate', 0)),
                'channels': int(stream.get('channels', 0)),
                'codec': stream.get('codec_name', 'unknown'),
                'bit_rate': int(stream.get('bit_rate', 0)),
                'size': int(format_info.get('size', 0))
            }
        except Exception as e:
            logger.error(f"Erro ao obter informações do áudio: {e}")
            return {}
    
    def validate_for_coqui(self, wav_file: Path) -> bool:
        """Valida se o WAV está adequado para CoquiTTS"""
        try:
            info = self.get_audio_info(wav_file)
            
            sample_rate = info.get('sample_rate', 0)
            channels = info.get('channels', 0)
            duration = info.get('duration', 0)
            
            logger.info(f"Validação CoquiTTS - {wav_file.name}:")
            logger.info(f"  Sample Rate: {sample_rate}Hz {'✅' if sample_rate == 24000 else '⚠️'}")
            logger.info(f"  Canais: {channels} {'✅' if channels == 1 else '⚠️'}")
            logger.info(f"  Duração: {duration:.1f}s {'✅' if 3 <= duration <= 60 else '⚠️'}")
            
            # Critérios para CoquiTTS
            is_valid = (
                sample_rate in [22050, 24000, 44100] and  # Sample rates aceitos
                channels == 1 and  # Mono
                3 <= duration <= 60  # Duração adequada
            )
            
            if is_valid:
                logger.info("  ✅ Formato adequado para CoquiTTS!")
            else:
                logger.warning("  ⚠️ Formato pode não ser ideal para CoquiTTS")
                
            return is_valid
                
        except Exception as e:
            logger.error(f"Erro na validação: {e}")
            return False
    
    def list_samples(self) -> None:
        """Lista samples disponíveis no diretório de saída"""
        samples = list(self.output_dir.glob("*.wav"))
        
        if not samples:
            logger.info(f"Nenhum sample encontrado em {self.output_dir}/")
            return
        
        logger.info(f"Samples disponíveis em {self.output_dir}:")
        for sample in sorted(samples):
            info = self.get_audio_info(sample)
            size_kb = sample.stat().st_size / 1024
            duration = info.get('duration', 0)
            sample_rate = info.get('sample_rate', 0)
            
            logger.info(f"  🎵 {sample.name}")
            logger.info(f"     Tamanho: {size_kb:.1f}KB | Duração: {duration:.1f}s | Sample Rate: {sample_rate}Hz")
    
    def optimize_for_coqui(self, input_file: Path, output_file: Optional[Path] = None) -> Path:
        """Otimiza arquivo de áudio para uso com CoquiTTS"""
        if output_file is None:
            output_file = self.output_dir / f"optimized_{input_file.name}"
        
        try:
            ffmpeg_cmd = [
                'ffmpeg',
                '-i', str(input_file),
                '-ar', '24000',  # 24kHz sample rate
                '-ac', '1',      # Mono
                '-c:a', 'pcm_f32le',  # Float32 PCM
                '-af', 'volume=0.8,highpass=f=80,lowpass=f=8000',  # Filtros de áudio
                '-y',  # Sobrescrever se existir
                str(output_file)
            ]
            
            result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, check=True)
            
            if output_file.exists():
                logger.info(f"✅ Arquivo otimizado: {output_file}")
                self.validate_for_coqui(output_file)
                return output_file
            else:
                raise RuntimeError("Falha ao criar arquivo otimizado")
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Erro ao otimizar áudio: {e}")
            if e.stderr:
                logger.error(f"stderr: {e.stderr}")
            raise
        except Exception as e:
            logger.error(f"Erro inesperado: {e}")
            raise 