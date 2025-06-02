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
    
    def combine_segments(self, 
                        segment_files: List[Path], 
                        output_file: Path,
                        format: str = "wav",
                        sample_rate: int = 22050,
                        channels: int = 1,
                        normalize: bool = True,
                        apply_compression: bool = True) -> Path:
        """Combina segmentos de áudio em arquivo final"""
        
        logger.info(f"Combinando {len(segment_files)} segmentos...")
        
        if not segment_files:
            raise ValueError("Nenhum segmento fornecido para combinação")
        
        # Verificar se todos os arquivos existem
        existing_files = [f for f in segment_files if f.exists()]
        if not existing_files:
            raise ValueError("Nenhum arquivo de segmento válido encontrado")
        
        if len(existing_files) != len(segment_files):
            logger.warning(f"Alguns segmentos não foram encontrados: {len(segment_files) - len(existing_files)} faltando")
        
        # Para um único arquivo, apenas copiar (com processamento opcional)
        if len(existing_files) == 1:
            return self._process_single_file(existing_files[0], output_file, format, normalize, apply_compression)
        
        # Múltiplos arquivos - usar ffmpeg se disponível, senão usar método simples
        if self._is_ffmpeg_available():
            return self._combine_with_ffmpeg(existing_files, output_file, format, sample_rate, channels, normalize, apply_compression)
        else:
            return self._combine_simple(existing_files, output_file, format)
    
    def _process_single_file(self, input_file: Path, output_file: Path, format: str, normalize: bool, apply_compression: bool) -> Path:
        """Processa um único arquivo"""
        
        if self._is_ffmpeg_available() and (normalize or apply_compression):
            # Usar ffmpeg para processamento
            return self._process_with_ffmpeg(input_file, output_file, format, normalize, apply_compression)
        else:
            # Cópia simples
            import shutil
            shutil.copy2(input_file, output_file)
            return output_file
    
    def _combine_with_ffmpeg(self, 
                           segment_files: List[Path], 
                           output_file: Path,
                           format: str,
                           sample_rate: int,
                           channels: int,
                           normalize: bool,
                           apply_compression: bool) -> Path:
        """Combina arquivos usando ffmpeg"""
        
        logger.info("Usando ffmpeg para combinação...")
        
        # Criar arquivo de lista temporário
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            list_file = f.name
            for segment_file in segment_files:
                f.write(f"file '{segment_file.absolute()}'\n")
        
        try:
            # Construir comando ffmpeg
            cmd = [
                'ffmpeg', '-y',  # Sobrescrever arquivo de saída
                '-f', 'concat',
                '-safe', '0',
                '-i', list_file,
                '-ar', str(sample_rate),
                '-ac', str(channels)
            ]
            
            # Adicionar filtros de áudio
            filters = []
            
            if normalize:
                filters.append('loudnorm')
            
            if apply_compression:
                filters.append('acompressor=threshold=0.1:ratio=3:attack=5:release=50')
            
            if self.remove_silence:
                filters.append('silenceremove=start_periods=1:start_duration=1:start_threshold=-60dB:detection=peak')
            
            if filters:
                cmd.extend(['-af', ','.join(filters)])
            
            # Adicionar arquivo de saída
            cmd.append(str(output_file))
            
            # Executar comando
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Erro no ffmpeg: {result.stderr}")
                # Fallback para método simples
                return self._combine_simple(segment_files, output_file, format)
            
            logger.info(f"Combinação concluída: {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"Erro usando ffmpeg: {e}")
            return self._combine_simple(segment_files, output_file, format)
        
        finally:
            # Limpar arquivo temporário
            try:
                os.unlink(list_file)
            except:
                pass
    
    def _combine_simple(self, segment_files: List[Path], output_file: Path, format: str) -> Path:
        """Combinação simples usando concatenação binária (apenas para WAV/AIFF)"""
        
        logger.info("Usando combinação simples...")
        
        # Para formatos que suportam concatenação simples
        if format.lower() in ['wav', 'aiff']:
            return self._combine_audio_files_simple(segment_files, output_file)
        else:
            # Para outros formatos, copiar primeiro arquivo
            import shutil
            shutil.copy2(segment_files[0], output_file)
            logger.warning(f"Formato {format} não suportado para combinação simples, usando apenas primeiro segmento")
            return output_file
    
    def _combine_audio_files_simple(self, segment_files: List[Path], output_file: Path) -> Path:
        """Combina arquivos de áudio através de concatenação simples"""
        
        try:
            with open(output_file, 'wb') as outfile:
                for i, segment_file in enumerate(segment_files):
                    with open(segment_file, 'rb') as infile:
                        if i == 0:
                            # Primeiro arquivo - copiar completo
                            outfile.write(infile.read())
                        else:
                            # Arquivos subsequentes - pular cabeçalho (primeiros 44 bytes para WAV)
                            infile.seek(44)
                            outfile.write(infile.read())
            
            logger.info(f"Combinação simples concluída: {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"Erro na combinação simples: {e}")
            # Como último recurso, copiar primeiro arquivo
            import shutil
            shutil.copy2(segment_files[0], output_file)
            return output_file
    
    def _process_with_ffmpeg(self, 
                           input_file: Path, 
                           output_file: Path,
                           format: str,
                           normalize: bool,
                           apply_compression: bool) -> Path:
        """Processa arquivo único com ffmpeg"""
        
        try:
            cmd = [
                'ffmpeg', '-y',
                '-i', str(input_file)
            ]
            
            # Adicionar filtros
            filters = []
            
            if normalize:
                filters.append('loudnorm')
            
            if apply_compression:
                filters.append('acompressor=threshold=0.1:ratio=3:attack=5:release=50')
            
            if filters:
                cmd.extend(['-af', ','.join(filters)])
            
            cmd.append(str(output_file))
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return output_file
            else:
                logger.error(f"Erro processando com ffmpeg: {result.stderr}")
                # Fallback - cópia simples
                import shutil
                shutil.copy2(input_file, output_file)
                return output_file
                
        except Exception as e:
            logger.error(f"Erro usando ffmpeg: {e}")
            import shutil
            shutil.copy2(input_file, output_file)
            return output_file
    
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