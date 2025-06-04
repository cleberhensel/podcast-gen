"""
Processador de Áudio para Podcast TTS
Combina segmentos e aplica pós-processamento
"""

import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import subprocess
import tempfile
import numpy as np
import wave
import struct

logger = logging.getLogger(__name__)

class AudioProcessor:
    """Processador de áudio para podcasts"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # Configurações de processamento
        self.normalize_volume = self.config.get('processing', {}).get('normalize_volume', True)
        self.apply_compression = self.config.get('processing', {}).get('apply_compression', True)
        self.fade_duration = self.config.get('processing', {}).get('fade_duration', 0.2)
        self.inter_segment_pause = self.config.get('processing', {}).get('inter_segment_pause', 0.8)
        self.remove_silence = self.config.get('processing', {}).get('remove_silence', True)
        
        # Configurações padrão
        self.default_sample_rate = self.config.get('audio', {}).get('sample_rate', 24000)
        self.default_channels = self.config.get('audio', {}).get('channels', 1)
        self.default_format = self.config.get('audio', {}).get('format', 'wav')
        
        # Configurações de streaming
        self.streaming_enabled = self.config.get('audio', {}).get('streaming', True)
        self.buffer_size = self.config.get('audio', {}).get('buffer_size', 8192)
    
    def combine_segments(self, segment_files: List[Path], output_file: Path, **kwargs) -> Path:
        """Combina segmentos de áudio em arquivo final"""
        
        if self.streaming_enabled:
            return self._combine_segments_streaming(segment_files, output_file, **kwargs)
        else:
            return self._combine_segments_memory(segment_files, output_file, **kwargs)
    
    def _combine_segments_streaming(self, segment_files: List[Path], output_file: Path, **kwargs) -> Path:
        """Combina segmentos usando streaming (baixo uso de memória)"""
        
        format_type = kwargs.get('format', self.default_format)
        sample_rate = kwargs.get('sample_rate', self.default_sample_rate)
        channels = kwargs.get('channels', self.default_channels)
        normalize = kwargs.get('normalize', False)
        apply_compression = kwargs.get('apply_compression', False)
        
        logger.info(f"🔄 Combinando {len(segment_files)} segmentos via streaming...")
        
        # Filtrar apenas arquivos existentes
        valid_segments = [f for f in segment_files if f and f.exists()]
        if not valid_segments:
            raise ValueError("Nenhum segmento válido encontrado")
        
        try:
            # Criar arquivo de saída WAV
            output_wav = output_file.with_suffix('.wav')
            
            # Combinar segmentos incrementalmente
            total_frames = 0
            
            with wave.open(str(output_wav), 'wb') as output_wave:
                # Configurar parâmetros baseado no primeiro arquivo
                first_segment = valid_segments[0]
                with wave.open(str(first_segment), 'rb') as first_wave:
                    output_wave.setnchannels(first_wave.getnchannels())
                    output_wave.setsampwidth(first_wave.getsampwidth())
                    output_wave.setframerate(first_wave.getframerate())
                
                # Processar cada segmento
                for i, segment_file in enumerate(valid_segments):
                    logger.debug(f"Processando segmento {i+1}/{len(valid_segments)}: {segment_file.name}")
                    
                    try:
                        with wave.open(str(segment_file), 'rb') as segment_wave:
                            # Ler e escrever em chunks para economia de memória
                            while True:
                                frames = segment_wave.readframes(self.buffer_size)
                                if not frames:
                                    break
                                
                                output_wave.writeframes(frames)
                                total_frames += len(frames) // (segment_wave.getnchannels() * segment_wave.getsampwidth())
                    
                    except Exception as e:
                        logger.warning(f"Erro processando segmento {segment_file}: {e}")
                        continue
            
            logger.info(f"✅ Arquivo WAV combinado: {output_wav} ({total_frames} frames)")
            
            # Aplicar pós-processamento se necessário
            if normalize or apply_compression:
                self._apply_postprocessing(output_wav, normalize, apply_compression)
            
            # Converter para formato final se necessário
            if format_type.lower() == 'mp3':
                mp3_file = self._convert_to_mp3(output_wav)
                if mp3_file:
                    return mp3_file
            
            return output_wav
            
        except Exception as e:
            logger.error(f"Erro combinando segmentos: {e}")
            raise
    
    def _combine_segments_memory(self, segment_files: List[Path], output_file: Path, **kwargs) -> Path:
        """Combina segmentos carregando tudo na memória (método original)"""
        
        logger.info(f"🔄 Combinando {len(segment_files)} segmentos em memória...")
        
        format_type = kwargs.get('format', self.default_format)
        sample_rate = kwargs.get('sample_rate', self.default_sample_rate)
        channels = kwargs.get('channels', self.default_channels)
        normalize = kwargs.get('normalize', False)
        apply_compression = kwargs.get('apply_compression', False)
        
        # Filtrar apenas arquivos existentes
        valid_segments = [f for f in segment_files if f and f.exists()]
        if not valid_segments:
            raise ValueError("Nenhum segmento válido encontrado")
        
        try:
            # Carregar todos os segmentos
            audio_data = []
            
            for segment_file in valid_segments:
                logger.debug(f"Carregando: {segment_file}")
                
                try:
                    # Tentar diferentes métodos de carregamento
                    segment_audio = self._load_audio_file(segment_file)
                    if segment_audio is not None and len(segment_audio) > 0:
                        audio_data.append(segment_audio)
                    else:
                        logger.warning(f"Segmento vazio ou inválido: {segment_file}")
                        
                except Exception as e:
                    logger.warning(f"Erro carregando {segment_file}: {e}")
                    continue
            
            if not audio_data:
                raise ValueError("Nenhum áudio válido foi carregado")
            
            # Concatenar arrays
            logger.info("Concatenando áudio...")
            combined_audio = np.concatenate(audio_data)
            
            # Aplicar pós-processamento
            if normalize:
                combined_audio = self._normalize_audio(combined_audio)
            
            if apply_compression:
                combined_audio = self._apply_compression(combined_audio)
            
            # Salvar arquivo final
            output_wav = output_file.with_suffix('.wav')
            self._save_audio(combined_audio, output_wav, sample_rate, channels)
            
            logger.info(f"✅ Arquivo combinado salvo: {output_wav}")
            
            # Converter para MP3 se necessário
            if format_type.lower() == 'mp3':
                mp3_file = self._convert_to_mp3(output_wav)
                if mp3_file:
                    return mp3_file
            
            return output_wav
            
        except Exception as e:
            logger.error(f"Erro combinando segmentos: {e}")
            raise
    
    def _load_audio_file(self, file_path: Path) -> Optional[np.ndarray]:
        """Carrega arquivo de áudio"""
        
        try:
            import soundfile as sf
            
            audio_data, sample_rate = sf.read(str(file_path))
            logger.debug(f"Carregado via soundfile: {len(audio_data)} samples @ {sample_rate}Hz")
            return audio_data.astype(np.float32)
            
        except ImportError:
            logger.debug("soundfile não disponível, tentando wave...")
            
        except Exception as e:
            logger.debug(f"Erro com soundfile: {e}, tentando wave...")
        
        # Fallback para wave
        try:
            with wave.open(str(file_path), 'rb') as wave_file:
                frames = wave_file.readframes(wave_file.getnframes())
                sample_width = wave_file.getsampwidth()
                
                if sample_width == 1:
                    audio_array = np.frombuffer(frames, dtype=np.uint8)
                    audio_array = (audio_array - 128) / 128.0
                elif sample_width == 2:
                    audio_array = np.frombuffer(frames, dtype=np.int16)
                    audio_array = audio_array / 32768.0
                elif sample_width == 4:
                    audio_array = np.frombuffer(frames, dtype=np.int32)
                    audio_array = audio_array / 2147483648.0
                else:
                    raise ValueError(f"Sample width não suportado: {sample_width}")
                
                logger.debug(f"Carregado via wave: {len(audio_array)} samples")
                return audio_array.astype(np.float32)
                
        except Exception as e:
            logger.error(f"Erro carregando {file_path}: {e}")
            return None
    
    def _save_audio(self, audio_data: np.ndarray, output_file: Path, sample_rate: int, channels: int):
        """Salva array de áudio em arquivo WAV"""
        
        try:
            import soundfile as sf
            sf.write(str(output_file), audio_data, sample_rate)
            
        except ImportError:
            # Fallback para wave
            audio_int16 = (audio_data * 32767).astype(np.int16)
            
            with wave.open(str(output_file), 'wb') as wave_file:
                wave_file.setnchannels(channels)
                wave_file.setsampwidth(2)  # 16-bit
                wave_file.setframerate(sample_rate)
                wave_file.writeframes(audio_int16.tobytes())
    
    def _apply_postprocessing(self, audio_file: Path, normalize: bool, apply_compression: bool):
        """Aplica pós-processamento ao arquivo de áudio"""
        
        if normalize:
            logger.debug("Aplicando normalização...")
            # Implementar normalização in-place se necessário
        
        if apply_compression:
            logger.debug("Aplicando compressão...")
            # Implementar compressão in-place se necessário
    
    def _normalize_audio(self, audio_data: np.ndarray) -> np.ndarray:
        """Normaliza áudio"""
        max_val = np.max(np.abs(audio_data))
        if max_val > 0:
            return audio_data / max_val
        return audio_data
    
    def _apply_compression(self, audio_data: np.ndarray) -> np.ndarray:
        """Aplica compressão dinâmica simples"""
        # Compressão simples: reduzir picos acima de threshold
        threshold = 0.8
        ratio = 0.3
        
        compressed = audio_data.copy()
        mask = np.abs(compressed) > threshold
        compressed[mask] = np.sign(compressed[mask]) * (threshold + (np.abs(compressed[mask]) - threshold) * ratio)
        
        return compressed
    
    def _convert_to_mp3(self, wav_file: Path) -> Optional[Path]:
        """Converte WAV para MP3"""
        
        try:
            import subprocess
            
            mp3_file = wav_file.with_suffix('.mp3')
            
            cmd = [
                'ffmpeg',
                '-i', str(wav_file),
                '-codec:a', 'libmp3lame',
                '-b:a', '192k',
                '-y',
                str(mp3_file)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            if mp3_file.exists():
                logger.info(f"✅ MP3 gerado: {mp3_file}")
                return mp3_file
            
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.warning(f"Erro convertendo para MP3: {e}")
        
        return None
    
    def get_audio_info(self, file_path: Path) -> Dict[str, Any]:
        """Obtém informações de arquivo de áudio"""
        
        try:
            import soundfile as sf
            
            info = sf.info(str(file_path))
            
            return {
                'duration': info.duration,
                'sample_rate': info.samplerate,
                'channels': info.channels,
                'format': info.format,
                'subtype': info.subtype
            }
            
        except ImportError:
            # Fallback para wave
            try:
                with wave.open(str(file_path), 'rb') as wave_file:
                    frames = wave_file.getnframes()
                    sample_rate = wave_file.getframerate()
                    duration = frames / sample_rate
                    
                    return {
                        'duration': duration,
                        'sample_rate': sample_rate,
                        'channels': wave_file.getnchannels(),
                        'format': 'WAV',
                        'subtype': f"{wave_file.getsampwidth() * 8}-bit"
                    }
            except Exception as e:
                logger.error(f"Erro obtendo info de {file_path}: {e}")
                return {}
    
    def _is_ffmpeg_available(self) -> bool:
        """Verifica se ffmpeg está disponível"""
        try:
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False
        except Exception:
            return False
    
    def add_background_music(self, 
                           audio_file: Path, 
                           music_file: Path, 
                           output_file: Path,
                           music_volume: float = 0.1) -> Path:
        """Adiciona música de fundo ao áudio"""
        
        if not self._is_ffmpeg_available():
            logger.warning("ffmpeg não disponível, pulando música de fundo")
            import shutil
            shutil.copy2(audio_file, output_file)
            return output_file
        
        try:
            cmd = [
                'ffmpeg', '-y',
                '-i', str(audio_file),
                '-i', str(music_file),
                '-filter_complex', f'[1:a]volume={music_volume}[bg];[0:a][bg]amix=inputs=2:duration=first',
                str(output_file)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Música de fundo adicionada: {output_file}")
                return output_file
            else:
                logger.error(f"Erro adicionando música de fundo: {result.stderr}")
                import shutil
                shutil.copy2(audio_file, output_file)
                return output_file
                
        except Exception as e:
            logger.error(f"Erro adicionando música de fundo: {e}")
            import shutil
            shutil.copy2(audio_file, output_file)
            return output_file
    
    def convert_format(self, input_file: Path, output_file: Path, target_format: str) -> Path:
        """Converte arquivo para formato especificado"""
        
        if not self._is_ffmpeg_available():
            logger.warning("ffmpeg não disponível, mantendo formato original")
            import shutil
            shutil.copy2(input_file, output_file)
            return output_file
        
        try:
            cmd = [
                'ffmpeg', '-y',
                '-i', str(input_file),
                str(output_file)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Formato convertido: {output_file}")
                return output_file
            else:
                logger.error(f"Erro convertendo formato: {result.stderr}")
                import shutil
                shutil.copy2(input_file, output_file)
                return output_file
                
        except Exception as e:
            logger.error(f"Erro convertendo formato: {e}")
            import shutil
            shutil.copy2(input_file, output_file)
            return output_file 