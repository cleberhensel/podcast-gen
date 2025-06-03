#!/usr/bin/env python3
"""
Gerador de Podcast TTS - Versão Docker
Adaptado para funcionar em container com interface web
"""

import argparse
import sys
import os
from pathlib import Path
import yaml
import logging
from typing import Optional

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from src.core.podcast_generator import PodcastGenerator
from src.core.script_parser import ScriptParser
from src.engines.engine_factory import tts_factory

def setup_logging():
    """Configurar logging para container"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

def load_config():
    """Carregar configurações adaptadas para Docker"""
    config_path = Path(__file__).parent / "config" / "settings.yaml"
    
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    else:
        # Configuração mínima se arquivo não existir
        config = {
            'engines': {'default': 'piper'},  # Usar Piper como padrão
            'audio': {'format': 'wav', 'sample_rate': 22050},  # Piper usa 22kHz
            'output': {'default_directory': 'output/final'}
        }
    
    # Configurar Piper TTS para Docker
    if 'piper' not in config['engines']:
        config['engines']['piper'] = {
            'enabled': True,
            'models_path': '/home/podcast/.local/share/piper-tts',
            'fallback_to_macos': False  # Desabilitar macOS no Docker
        }
    
    return config

def main():
    parser = argparse.ArgumentParser(description='Gerador de Podcast TTS - Docker')
    parser.add_argument('script_file', help='Arquivo de roteiro (.txt)')
    parser.add_argument('--output-dir', default='output/final', help='Diretório de saída')
    parser.add_argument('--job-id', help='ID do job para nomenclatura')
    parser.add_argument('--format', choices=['wav', 'mp3'], default='mp3', help='Formato de saída')
    
    args = parser.parse_args()
    
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Carregar configurações
        config = load_config()
        
        # Verificar arquivo de entrada
        script_path = Path(args.script_file)
        if not script_path.exists():
            logger.error(f"Arquivo não encontrado: {script_path}")
            sys.exit(1)
        
        # Criar diretórios de saída
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"🎙️ Iniciando geração de podcast...")
        logger.info(f"📄 Roteiro: {script_path}")
        logger.info(f"📁 Saída: {output_dir}")
        
        # Configurar engine TTS
        engine_name = 'piper'  # Forçar sempre Piper TTS
        logger.info(f"🔧 Configurando engine TTS: {engine_name}")
        
        engine = tts_factory.create_engine(engine_name)
        if not engine:
            logger.error(f"Falha ao criar engine: {engine_name}")
            sys.exit(1)
        
        # Parse do roteiro
        logger.info("📊 Analisando roteiro...")
        parser = ScriptParser()
        podcast = parser.parse_file(script_path)
        
        # Informações do podcast
        logger.info(f"  • Título: {podcast.metadata.title}")
        logger.info(f"  • Diálogos: {len(podcast.dialogues)}")
        logger.info(f"  • Personagens: {len(podcast.get_unique_characters())}")
        
        # Criar gerador com config
        generator = PodcastGenerator(config)
        
        # Nome do arquivo de saída
        if args.job_id:
            output_name = f"{args.job_id}_podcast"
        else:
            output_name = script_path.stem + "_podcast"
        
        # Gerar podcast
        logger.info("🚀 Iniciando geração de áudio...")
        
        # Gerar WAV primeiro
        wav_path = output_dir / f"{output_name}.wav"
        result = generator.generate_podcast(podcast, str(wav_path))
        
        if not result or not wav_path.exists():
            logger.error("Falha na geração do podcast")
            sys.exit(1)
        
        logger.info(f"✅ WAV gerado: {wav_path}")
        
        # Converter para MP3 se necessário
        if args.format == 'mp3':
            mp3_path = output_dir / f"{output_name}.mp3"
            
            import subprocess
            cmd = [
                'ffmpeg', '-y', '-i', str(wav_path),
                '-codec:a', 'libmp3lame', '-b:a', '192k',
                str(mp3_path)
            ]
            
            logger.info("🎵 Gerando versão MP3...")
            result = subprocess.run(cmd, capture_output=True, check=True)
            
            if mp3_path.exists():
                logger.info(f"✅ MP3 gerado: {mp3_path}")
                # Remover WAV para economizar espaço
                wav_path.unlink()
            else:
                logger.error("Falha na conversão para MP3")
                sys.exit(1)
        
        logger.info("🎉 Podcast gerado com sucesso!")
        
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 