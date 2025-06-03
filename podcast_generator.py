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
            'engines': {'default': 'coqui'},  # Changed from 'piper' to 'coqui'
            'audio': {'format': 'wav', 'sample_rate': 24000},  # CoquiTTS XTTS v2 uses 24kHz
            'output': {'default_directory': 'output/final'}
        }
    
    # Configurar CoquiTTS como padrão e Piper como fallback
    if 'coqui' not in config['engines']:
        config['engines']['coqui'] = {
            'enabled': True,
            'model_name': 'tts_models/multilingual/multi-dataset/xtts_v2',
            'default_language': 'pt'
        }
    
    # Manter configuração do Piper para fallback
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
    parser.add_argument('--engine', choices=['piper', 'coqui'], default='coqui', help='Engine TTS a usar')
    parser.add_argument('--language', default='pt', help='Idioma para síntese (usado pelo CoquiTTS)')
    
    # 🎭 INTERFACE SIMPLIFICADA: Apenas 2 parâmetros opcionais
    parser.add_argument('--male-wav', help='Arquivo de voz masculina (para HOST_MALE)')
    parser.add_argument('--female-wav', help='Arquivo de voz feminina (para HOST_FEMALE)')
    
    # DEPRECATED: Manter compatibilidade por enquanto
    parser.add_argument('--speaker-wav', help='Arquivo de áudio de referência (DEPRECATED - use --male-wav ou --female-wav)')
    
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
        
        # Configurar engine TTS usando parâmetro
        engine_name = args.engine
        logger.info(f"🔧 Configurando engine TTS: {engine_name}")
        
        # Configurações específicas do engine
        engine_config = {}
        if engine_name == 'coqui':
            engine_config['language'] = args.language
        
        engine = tts_factory.create_engine(engine_name, engine_config)
        if not engine:
            logger.error(f"Falha ao criar engine: {engine_name}")
            sys.exit(1)
        
        # 🎭 CONFIGURAR VOZES PARA COQUI (SISTEMA SIMPLIFICADO)
        if engine_name == 'coqui':
            # Primeiro, fazer o parse do roteiro para analisar personagens
            logger.info("📊 Analisando personagens no roteiro...")
            temp_parser = ScriptParser()
            temp_podcast = temp_parser.parse_file(script_path)
            characters_in_script = set(temp_podcast.characters.keys())
            print(f"📊 PERSONAGENS ENCONTRADOS: {characters_in_script}")
            
            # 🎯 NOVA LÓGICA SIMPLIFICADA: Auto-detectar vozes disponíveis
            male_voice = args.male_wav
            female_voice = args.female_wav
            
            # Compatibilidade com --speaker-wav (DEPRECATED)
            if args.speaker_wav and not male_voice and not female_voice:
                print(f"⚠️  AVISO: --speaker-wav está DEPRECATED. Use --male-wav ou --female-wav")
                # Aplicar para ambos se roteiro tem ambos
                if 'HOST_MALE' in characters_in_script and 'HOST_FEMALE' in characters_in_script:
                    male_voice = args.speaker_wav
                    female_voice = args.speaker_wav
                    print(f"   • Aplicando {args.speaker_wav} para HOST_MALE e HOST_FEMALE")
                elif 'HOST_MALE' in characters_in_script:
                    male_voice = args.speaker_wav
                    print(f"   • Aplicando {args.speaker_wav} para HOST_MALE")
                elif 'HOST_FEMALE' in characters_in_script:
                    female_voice = args.speaker_wav
                    print(f"   • Aplicando {args.speaker_wav} para HOST_FEMALE")
            
            # 🔍 AUTO-DETECTAR VOZES DISPONÍVEIS se não fornecidas
            if not male_voice or not female_voice:
                print(f"🔍 DETECTANDO VOZES DISPONÍVEIS...")
                speakers_dir = Path("static/speaker_samples")
                
                if speakers_dir.exists():
                    available_speakers = list(speakers_dir.glob("*.wav"))
                    print(f"   • Encontrados {len(available_speakers)} speakers: {[s.name for s in available_speakers]}")
                    
                    # Mapear speakers conhecidos por nome
                    speaker_mapping = {
                        'rafael': 'masculino',
                        'marcela': 'feminino', 
                        'ana': 'feminino'
                    }
                    
                    # Auto-escolher se não fornecidos
                    if not male_voice and 'HOST_MALE' in characters_in_script:
                        for speaker in available_speakers:
                            for name, gender in speaker_mapping.items():
                                if name.lower() in speaker.stem.lower() and gender == 'masculino':
                                    male_voice = str(speaker)
                                    print(f"   ✅ AUTO-DETECTADO masculino: {speaker.name}")
                                    break
                            if male_voice:
                                break
                        
                        # Fallback: usar primeiro disponível
                        if not male_voice and available_speakers:
                            male_voice = str(available_speakers[0])
                            print(f"   ⚡ FALLBACK masculino: {available_speakers[0].name}")
                    
                    if not female_voice and 'HOST_FEMALE' in characters_in_script:
                        for speaker in available_speakers:
                            for name, gender in speaker_mapping.items():
                                if name.lower() in speaker.stem.lower() and gender == 'feminino':
                                    female_voice = str(speaker)
                                    print(f"   ✅ AUTO-DETECTADO feminino: {speaker.name}")
                                    break
                            if female_voice:
                                break
                        
                        # Fallback: usar segundo disponível ou primeiro se só tem um
                        if not female_voice and available_speakers:
                            female_voice = str(available_speakers[1] if len(available_speakers) > 1 else available_speakers[0])
                            print(f"   ⚡ FALLBACK feminino: {Path(female_voice).name}")
            
            # 🎭 CONFIGURAR VOZES NO ENGINE
            print(f"🎭 CONFIGURANDO SISTEMA DE VOZES CONSISTENTES:")
            print(f"   • Voz masculina: {Path(male_voice).name if male_voice else 'NÃO FORNECIDA'}")
            print(f"   • Voz feminina: {Path(female_voice).name if female_voice else 'NÃO FORNECIDA'}")
            
            try:
                engine.configure_podcast_voices(
                    male_voice=male_voice,
                    female_voice_1=female_voice,
                    female_voice_2=None,  # Não precisamos mais da segunda opção
                    characters_in_script=characters_in_script
                )
                print(f"✅ SISTEMA DE VOZES CONSISTENTES CONFIGURADO!")
            except Exception as e:
                logger.error(f"Erro configurando vozes: {e}")
                sys.exit(1)
        
        # Parse do roteiro (não precisa fazer novamente se já foi feito)
        if engine_name == 'coqui':
            # Usar o parse que já foi feito
            podcast = temp_podcast
        else:
            logger.info("📊 Analisando roteiro...")
            parser = ScriptParser()
            podcast = parser.parse_file(script_path)
        
        # Informações do podcast
        logger.info(f"  • Título: {podcast.metadata.title}")
        logger.info(f"  • Diálogos: {len(podcast.dialogues)}")
        logger.info(f"  • Personagens: {len(podcast.get_unique_characters())}")
        
        # Criar gerador com config E engine configurado
        generator = PodcastGenerator(config)
        
        # IMPORTANTE: Substituir o engine do generator pelo engine configurado
        print(f"🔧 SUBSTITUINDO ENGINE NO GENERATOR")
        print(f"   • Engine antigo: {generator.engine.name}")
        generator.engine = engine  # Usar o engine que configuramos com speaker_wav
        print(f"   • Engine novo: {generator.engine.name}")
        
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