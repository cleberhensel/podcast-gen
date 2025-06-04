#!/usr/bin/env python3
"""
CLI para Sistema de Extração de Samples de Áudio
Interface de linha de comando para extrair e processar samples
"""

import argparse
import sys
import logging
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)

from .youtube_extractor import YouTubeSampleExtractor
from .audio_processor import AudioSampleProcessor

def main():
    parser = argparse.ArgumentParser(
        description="Sistema de Extração de Samples de Áudio para TTS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:

YouTube:
  # Extrair 8 segundos a partir do minuto 1:30
  python -m src.extractors.cli youtube "https://youtu.be/ABC123" --start 90 --duration 8 --name "speaker_male"
  
  # Extrair múltiplos segmentos
  python -m src.extractors.cli youtube "https://youtu.be/ABC123" --segments "[{start:30,duration:8,name:'male_voice'},{start:120,duration:10,name:'female_voice'}]"

Processamento:
  # Otimizar arquivo existente
  python -m src.extractors.cli process audio.wav --optimize
  
  # Processar lote de arquivos
  python -m src.extractors.cli process ./input_dir/ --batch --optimize

Análise:
  # Listar samples
  python -m src.extractors.cli list
  
  # Estatísticas
  python -m src.extractors.cli stats
        """
    )
    
    # Subcomandos
    subparsers = parser.add_subparsers(dest='command', help='Comandos disponíveis')
    
    # YouTube extractor
    youtube_parser = subparsers.add_parser('youtube', help='Extrair samples do YouTube')
    youtube_parser.add_argument('url', help='URL do vídeo do YouTube')
    youtube_parser.add_argument('--start', '-s', type=int, default=0, 
                               help='Segundo inicial (padrão: 0)')
    youtube_parser.add_argument('--duration', '-d', type=int, default=8,
                               help='Duração em segundos (padrão: 8)')
    youtube_parser.add_argument('--name', '-n', type=str,
                               help='Nome do arquivo de saída (sem extensão)')
    youtube_parser.add_argument('--segments', type=str,
                               help='JSON com múltiplos segmentos a extrair')
    youtube_parser.add_argument('--output-dir', type=str, default="static/speaker_samples",
                               help='Diretório de saída')
    
    # Processador de áudio
    process_parser = subparsers.add_parser('process', help='Processar arquivos de áudio')
    process_parser.add_argument('input', help='Arquivo ou diretório de entrada')
    process_parser.add_argument('--name', '-n', type=str,
                               help='Nome do arquivo de saída (sem extensão)')
    process_parser.add_argument('--optimize', action='store_true',
                               help='Otimizar para CoquiTTS')
    process_parser.add_argument('--batch', action='store_true',
                               help='Processar diretório em lote')
    process_parser.add_argument('--pattern', type=str, default="*.wav",
                               help='Padrão de arquivos para lote (padrão: *.wav)')
    process_parser.add_argument('--segments', type=str,
                               help='JSON com segmentos para dividir arquivo')
    process_parser.add_argument('--output-dir', type=str, default="static/speaker_samples",
                               help='Diretório de saída')
    
    # Listagem
    list_parser = subparsers.add_parser('list', help='Listar samples disponíveis')
    list_parser.add_argument('--dir', type=str, default="static/speaker_samples",
                            help='Diretório para listar')
    
    # Estatísticas
    stats_parser = subparsers.add_parser('stats', help='Mostrar estatísticas dos samples')
    stats_parser.add_argument('--dir', type=str, default="static/speaker_samples",
                             help='Diretório para analisar')
    
    # Limpeza
    clean_parser = subparsers.add_parser('clean', help='Limpar samples inadequados')
    clean_parser.add_argument('--min-duration', type=float, default=3.0,
                             help='Duração mínima em segundos')
    clean_parser.add_argument('--max-duration', type=float, default=60.0,
                             help='Duração máxima em segundos')
    clean_parser.add_argument('--dir', type=str, default="static/speaker_samples",
                             help='Diretório para limpar')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'youtube':
            handle_youtube_command(args)
        elif args.command == 'process':
            handle_process_command(args)
        elif args.command == 'list':
            handle_list_command(args)
        elif args.command == 'stats':
            handle_stats_command(args)
        elif args.command == 'clean':
            handle_clean_command(args)
    except Exception as e:
        print(f"❌ Erro: {e}")
        sys.exit(1)

def handle_youtube_command(args):
    """Manipula comando de extração do YouTube"""
    extractor = YouTubeSampleExtractor(args.output_dir)
    
    if not extractor.check_dependencies():
        sys.exit(1)
    
    if args.segments:
        # Múltiplos segmentos
        import json
        segments = json.loads(args.segments)
        results = extractor.extract_multiple_samples(args.url, segments)
        print(f"\n🎉 {len(results)} samples extraídos com sucesso!")
        for result in results:
            print(f"  📁 {result}")
    else:
        # Segmento único
        result = extractor.extract_sample(
            args.url, args.start, args.duration, args.name
        )
        print(f"\n🎉 Sample extraído: {result}")
        print(f"\n💡 Para usar no CoquiTTS:")
        print(f"   --male-wav {result}")

def handle_process_command(args):
    """Manipula comando de processamento"""
    processor = AudioSampleProcessor(args.output_dir)
    
    if not processor.check_dependencies():
        sys.exit(1)
    
    input_path = Path(args.input)
    
    if args.batch:
        # Processamento em lote
        results = processor.batch_process(
            input_path, args.pattern, args.optimize
        )
        print(f"\n🎉 {len(results)} arquivos processados!")
    elif args.segments:
        # Segmentação
        import json
        segments = json.loads(args.segments)
        results = processor.segment_audio(input_path, segments, args.optimize)
        print(f"\n🎉 {len(results)} segmentos criados!")
    else:
        # Arquivo único
        result = processor.process_file(input_path, args.name, args.optimize)
        print(f"\n🎉 Arquivo processado: {result}")

def handle_list_command(args):
    """Manipula comando de listagem"""
    processor = AudioSampleProcessor(args.dir)
    processor.list_samples()

def handle_stats_command(args):
    """Manipula comando de estatísticas"""
    processor = AudioSampleProcessor(args.dir)
    stats = processor.analyze_samples()
    
    if stats['count'] == 0:
        print("📁 Nenhum sample encontrado")
    else:
        print(f"\n📊 RESUMO DOS SAMPLES:")
        print(f"   📁 Total: {stats['count']} arquivos")
        print(f"   📏 Tamanho: {stats['total_size_mb']:.1f} MB")
        print(f"   ⏱️ Duração total: {stats['total_duration_min']:.1f} min")
        print(f"   📊 Duração média: {stats['avg_duration']:.1f}s")

def handle_clean_command(args):
    """Manipula comando de limpeza"""
    processor = AudioSampleProcessor(args.dir)
    processor.clean_samples(args.min_duration, args.max_duration)

if __name__ == "__main__":
    main() 