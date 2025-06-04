"""
YouTube Sample Extractor para CoquiTTS
Extrai samples de áudio do YouTube otimizados para síntese TTS
"""

import logging
import subprocess
import tempfile
import re
from pathlib import Path
from typing import Optional

from .base_extractor import BaseSampleExtractor

logger = logging.getLogger(__name__)

class YouTubeSampleExtractor(BaseSampleExtractor):
    """Extrator de samples de áudio do YouTube otimizado para CoquiTTS"""
    
    def __init__(self, output_dir: str = "static/speaker_samples"):
        super().__init__(output_dir)
        
    def check_dependencies(self) -> bool:
        """Verifica se yt-dlp e ffmpeg estão disponíveis"""
        dependencies_ok = super().check_dependencies()
        
        # Verificar yt-dlp
        try:
            result = subprocess.run(['yt-dlp', '--version'], 
                                  capture_output=True, text=True, check=True)
            logger.info(f"yt-dlp disponível: {result.stdout.strip()}")
            return dependencies_ok
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.error("yt-dlp não encontrado! Instale com: pip install yt-dlp")
            return False
    
    def extract_video_id(self, url: str) -> str:
        """Extrai o ID do vídeo da URL do YouTube"""
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([^&\n?#]+)',
            r'youtube\.com/watch.*?v=([^&\n?#]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        raise ValueError(f"URL do YouTube inválida: {url}")
    
    def extract_sample(self, source: str, start_time: int = 0, duration: int = 8, 
                      output_name: Optional[str] = None) -> Path:
        """
        Extrai sample de áudio do YouTube
        
        Args:
            source: URL do vídeo do YouTube
            start_time: Tempo inicial em segundos
            duration: Duração do sample em segundos
            output_name: Nome do arquivo de saída (sem extensão)
            
        Returns:
            Path para o arquivo WAV criado
        """
        
        # Extrair ID do vídeo
        video_id = self.extract_video_id(source)
        
        # Nome de saída automático se não fornecido
        if not output_name:
            output_name = f"youtube_{video_id}_{start_time}s"
        
        output_file = self.output_dir / f"{output_name}.wav"
        
        logger.info(f"🎯 Processando: {source}")
        logger.info(f"📹 ID do vídeo: {video_id}")
        logger.info(f"⏰ Início: {start_time}s, Duração: {duration}s")
        logger.info(f"💾 Saída: {output_file}")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_audio = Path(temp_dir) / f"temp_audio.%(ext)s"
            
            try:
                # Passo 1: Baixar áudio com yt-dlp
                logger.info("📥 Baixando áudio...")
                self._download_audio(source, temp_audio)
                
                # Encontrar arquivo baixado
                downloaded_file = self._find_downloaded_file(temp_dir)
                
                # Passo 2: Extrair segmento e otimizar para CoquiTTS
                logger.info(f"✂️ Extraindo segmento ({start_time}s - {start_time + duration}s)...")
                self._extract_and_optimize_segment(
                    downloaded_file, output_file, start_time, duration
                )
                
                # Validar resultado
                if not output_file.exists():
                    raise RuntimeError("Falha ao criar arquivo de saída")
                
                # Informações do arquivo criado
                info = self.get_audio_info(output_file)
                file_size = output_file.stat().st_size
                
                logger.info(f"✅ Sample extraído com sucesso!")
                logger.info(f"  📏 Tamanho: {file_size / 1024:.1f} KB")
                logger.info(f"  ⏱️ Duração: {info.get('duration', 0):.1f}s")
                logger.info(f"  📊 Sample Rate: {info.get('sample_rate', 0)}Hz")
                
                # Validar para CoquiTTS
                self.validate_for_coqui(output_file)
                
                return output_file
                
            except Exception as e:
                logger.error(f"❌ Erro na extração: {e}")
                raise
    
    def _download_audio(self, url: str, temp_audio: Path) -> None:
        """Baixa áudio do YouTube usando yt-dlp"""
        yt_dlp_cmd = [
            'yt-dlp',
            '--extract-audio',
            '--audio-format', 'wav',
            '--audio-quality', '0',  # Melhor qualidade
            '--no-playlist',
            '--output', str(temp_audio),
            url
        ]
        
        result = subprocess.run(yt_dlp_cmd, capture_output=True, text=True, check=True)
        logger.debug(f"yt-dlp output: {result.stdout}")
    
    def _find_downloaded_file(self, temp_dir: str) -> Path:
        """Encontra o arquivo baixado no diretório temporário"""
        temp_path = Path(temp_dir)
        
        # Procurar arquivo baixado
        for pattern in ["temp_audio.*", "*.wav", "*.mp3", "*.m4a"]:
            files = list(temp_path.glob(pattern))
            if files:
                downloaded_file = files[0]
                logger.debug(f"Arquivo baixado encontrado: {downloaded_file}")
                return downloaded_file
        
        raise RuntimeError("Arquivo de áudio baixado não encontrado")
    
    def _extract_and_optimize_segment(self, input_file: Path, output_file: Path,
                                    start_time: int, duration: int) -> None:
        """Extrai segmento e otimiza para CoquiTTS"""
        ffmpeg_cmd = [
            'ffmpeg',
            '-i', str(input_file),
            '-ss', str(start_time),  # Tempo inicial
            '-t', str(duration),     # Duração
            '-ar', '24000',          # 24kHz sample rate para CoquiTTS
            '-ac', '1',              # Mono
            '-c:a', 'pcm_f32le',     # Float32 PCM
            '-af', 'volume=0.8,highpass=f=80,lowpass=f=8000',  # Filtros de áudio
            '-y',  # Sobrescrever se existir
            str(output_file)
        ]
        
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, check=True)
        logger.debug(f"ffmpeg output: {result.stderr}")
    
    def extract_multiple_samples(self, url: str, segments: list) -> list:
        """
        Extrai múltiplos samples de um mesmo vídeo
        
        Args:
            url: URL do vídeo do YouTube
            segments: Lista de dicts com 'start', 'duration', 'name'
            
        Returns:
            Lista de Paths para os arquivos criados
        """
        video_id = self.extract_video_id(url)
        results = []
        
        logger.info(f"🎯 Extraindo {len(segments)} samples de: {video_id}")
        
        for i, segment in enumerate(segments, 1):
            try:
                start = segment['start']
                duration = segment.get('duration', 8)
                name = segment.get('name', f"{video_id}_segment_{i}")
                
                logger.info(f"📝 Segmento {i}/{len(segments)}: {name}")
                
                sample_file = self.extract_sample(url, start, duration, name)
                results.append(sample_file)
                
            except Exception as e:
                logger.error(f"❌ Erro no segmento {i}: {e}")
                continue
        
        logger.info(f"✅ {len(results)}/{len(segments)} samples extraídos com sucesso")
        return results
    
    def extract_speaker_voices(self, url: str, male_segments: list = None, 
                             female_segments: list = None) -> dict:
        """
        Extrai samples de vozes masculinas e femininas separadamente
        
        Args:
            url: URL do vídeo do YouTube
            male_segments: Lista de segmentos com voz masculina
            female_segments: Lista de segmentos com voz feminina
            
        Returns:
            Dict com {'male': [files], 'female': [files]}
        """
        results = {'male': [], 'female': []}
        
        if male_segments:
            logger.info("🗣️ Extraindo vozes masculinas...")
            for segment in male_segments:
                start_time = segment['start']
                default_name = f'voice_{start_time}s'
                segment['name'] = f"male_{segment.get('name', default_name)}"
            results['male'] = self.extract_multiple_samples(url, male_segments)
        
        if female_segments:
            logger.info("🗣️ Extraindo vozes femininas...")
            for segment in female_segments:
                start_time = segment['start']
                default_name = f'voice_{start_time}s'
                segment['name'] = f"female_{segment.get('name', default_name)}"
            results['female'] = self.extract_multiple_samples(url, female_segments)
        
        return results 