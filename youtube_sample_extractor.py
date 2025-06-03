#!/usr/bin/env python3
"""
YouTube Audio Sample Extractor para CoquiTTS
Baixa áudio do YouTube e extrai samples WAV em formato otimizado

Uso:
    python youtube_sample_extractor.py "https://youtu.be/VIDEO_ID" --start 30 --duration 8 --name "speaker_name"
"""

import argparse
import subprocess
import tempfile
import re
import sys
from pathlib import Path

class YouTubeSampleExtractor:
    """Extrator de samples de áudio do YouTube"""
    
    def __init__(self, output_dir="static/speaker_samples"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def check_dependencies(self):
        """Verifica se as dependências estão disponíveis"""
        print("🔍 Verificando dependências...")
        
        # Verificar yt-dlp
        try:
            result = subprocess.run(['yt-dlp', '--version'], 
                                  capture_output=True, text=True, check=True)
            print(f"  ✅ yt-dlp: {result.stdout.strip()}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("  ❌ yt-dlp não encontrado!")
            print("     Instale com: pip install yt-dlp")
            return False
            
        # Verificar ffmpeg
        try:
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True, check=True)
            version_line = result.stdout.split('\n')[0]
            print(f"  ✅ ffmpeg: {version_line}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("  ❌ ffmpeg não encontrado!")
            return False
            
        return True
    
    def extract_video_id(self, url):
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
    
    def download_audio_segment(self, url, start_time, duration, output_name=None):
        """Baixa segmento específico do áudio do YouTube"""
        
        # Extrair ID do vídeo
        video_id = self.extract_video_id(url)
        
        # Nome de saída automático se não fornecido
        if not output_name:
            output_name = f"youtube_{video_id}_{start_time}s"
        
        output_file = self.output_dir / f"{output_name}.wav"
        
        print(f"🎯 Processando: {url}")
        print(f"📹 ID do vídeo: {video_id}")
        print(f"⏰ Início: {start_time}s, Duração: {duration}s")
        print(f"💾 Saída: {output_file}")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_audio = Path(temp_dir) / f"temp_audio.%(ext)s"
            
            try:
                # Passo 1: Baixar áudio com yt-dlp
                print("\n📥 Baixando áudio...")
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
                
                # Encontrar arquivo baixado
                downloaded_file = None
                for file in Path(temp_dir).glob("temp_audio.*"):
                    downloaded_file = file
                    break
                
                if not downloaded_file or not downloaded_file.exists():
                    raise RuntimeError("Falha ao baixar áudio")
                
                print(f"  ✅ Áudio baixado: {downloaded_file}")
                
                # Passo 2: Extrair segmento e converter para formato CoquiTTS
                print(f"\n✂️ Extraindo segmento ({start_time}s - {start_time + duration}s)...")
                
                ffmpeg_cmd = [
                    'ffmpeg',
                    '-i', str(downloaded_file),
                    '-ss', str(start_time),
                    '-t', str(duration),
                    '-ar', '24000',  # 24kHz sample rate para CoquiTTS
                    '-ac', '1',      # Mono
                    '-c:a', 'pcm_f32le',  # Float32 PCM
                    '-af', 'volume=0.8',  # Reduzir volume um pouco
                    '-y',  # Sobrescrever se existir
                    str(output_file)
                ]
                
                result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, check=True)
                
                if not output_file.exists():
                    raise RuntimeError("Falha ao criar arquivo de saída")
                
                # Verificar qualidade do arquivo criado
                file_size = output_file.stat().st_size
                duration_actual = self.get_audio_duration(output_file)
                
                print(f"  ✅ Sample extraído com sucesso!")
                print(f"  📏 Tamanho: {file_size / 1024:.1f} KB")
                print(f"  ⏱️ Duração: {duration_actual:.1f}s")
                
                # Validar para CoquiTTS
                self.validate_for_coqui(output_file)
                
                return output_file
                
            except subprocess.CalledProcessError as e:
                print(f"❌ Erro de comando: {e}")
                if e.stderr:
                    print(f"   stderr: {e.stderr}")
                raise
            except Exception as e:
                print(f"❌ Erro: {e}")
                raise
    
    def get_audio_duration(self, audio_file):
        """Obtém duração do arquivo de áudio"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                str(audio_file)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            import json
            data = json.loads(result.stdout)
            return float(data['format']['duration'])
        except:
            return 0.0
    
    def validate_for_coqui(self, wav_file):
        """Valida se o WAV está adequado para CoquiTTS"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_streams',
                str(wav_file)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            import json
            data = json.loads(result.stdout)
            stream = data['streams'][0]
            
            sample_rate = int(stream['sample_rate'])
            channels = int(stream['channels'])
            codec = stream['codec_name']
            
            print(f"\n🔍 Validação CoquiTTS:")
            print(f"  📊 Sample Rate: {sample_rate}Hz {'✅' if sample_rate == 24000 else '⚠️'}")
            print(f"  🔊 Canais: {channels} {'✅' if channels == 1 else '⚠️'}")
            print(f"  🎵 Codec: {codec}")
            
            if sample_rate == 24000 and channels == 1:
                print("  ✅ Formato ideal para CoquiTTS!")
                return True
            else:
                print("  ⚠️ Formato não ideal mas pode funcionar")
                return False
                
        except Exception as e:
            print(f"  ❌ Erro na validação: {e}")
            return False
    
    def list_samples(self):
        """Lista samples disponíveis"""
        samples = list(self.output_dir.glob("*.wav"))
        
        if not samples:
            print("📁 Nenhum sample encontrado em speaker_samples/")
            return
        
        print(f"📁 Samples disponíveis em {self.output_dir}:")
        for sample in sorted(samples):
            size = sample.stat().st_size / 1024
            duration = self.get_audio_duration(sample)
            print(f"  🎵 {sample.name} ({size:.1f}KB, {duration:.1f}s)")

def main():
    parser = argparse.ArgumentParser(
        description="Extrator de samples de áudio do YouTube para CoquiTTS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Extrair 8 segundos a partir do minuto 1:30
  python youtube_sample_extractor.py "https://youtu.be/ABC123" --start 90 --duration 8 --name "speaker_male"
  
  # Extrair 10 segundos do início
  python youtube_sample_extractor.py "https://youtu.be/ABC123" --duration 10
  
  # Listar samples existentes
  python youtube_sample_extractor.py --list
        """
    )
    
    parser.add_argument('url', nargs='?', help='URL do vídeo do YouTube')
    parser.add_argument('--start', '-s', type=int, default=0, 
                       help='Segundo inicial (padrão: 0)')
    parser.add_argument('--duration', '-d', type=int, default=8,
                       help='Duração em segundos (padrão: 8)')
    parser.add_argument('--name', '-n', type=str,
                       help='Nome do arquivo de saída (sem extensão)')
    parser.add_argument('--list', '-l', action='store_true',
                       help='Listar samples existentes')
    
    args = parser.parse_args()
    
    extractor = YouTubeSampleExtractor()
    
    # Verificar dependências
    if not extractor.check_dependencies():
        sys.exit(1)
    
    if args.list:
        extractor.list_samples()
        return
    
    if not args.url:
        parser.print_help()
        print("\n❌ URL do YouTube é obrigatória (use --list para ver samples existentes)")
        sys.exit(1)
    
    try:
        output_file = extractor.download_audio_segment(
            args.url, args.start, args.duration, args.name
        )
        print(f"\n🎉 Sample criado com sucesso: {output_file}")
        print(f"\n💡 Para usar no CoquiTTS:")
        print(f"   --speaker-wav {output_file}")
        
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 