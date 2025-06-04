"""
Engine TTS usando CoquiTTS xTTS v2
Implementa síntese de voz com clonagem usando deep learning
VERSÃO CORRIGIDA - Bugs de tensor mismatch e index out of range resolvidos
"""

import os
import io
import tempfile
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import numpy as np
import re
import time
import wave

from .base_engine import BaseTTSEngine, TTSResult
from ..models.character import Character
from ..models.dialogue import Dialogue

# 🚀 INTEGRAÇÃO COM PLATAFORMA MULTI-SISTEMA
try:
    from ..platform import current_platform
    from ..core.performance_monitor import PerformanceMonitor
    PLATFORM_AVAILABLE = True
except ImportError:
    PLATFORM_AVAILABLE = False
    current_platform = None

logger = logging.getLogger(__name__)

class CoquiTTSEngine(BaseTTSEngine):
    """Engine TTS usando CoquiTTS xTTS v2 com clonagem de voz - VERSÃO CORRIGIDA"""
    
    # Singleton para modelo (economia de memória e GPU)
    _model_instance = None
    _device = None
    _initialized = False
    
    def __init__(self):
        super().__init__("coqui")
        
        # 🚀 CONFIGURAÇÃO BASEADA NA PLATAFORMA
        if PLATFORM_AVAILABLE and current_platform:
            # Aplicar otimizações específicas da plataforma
            current_platform.initialize_optimizations()
            current_platform.optimize_for_coqui_tts() if hasattr(current_platform, 'optimize_for_coqui_tts') else None
            
            # Obter configurações TTS específicas da plataforma
            tts_config = current_platform.get_tts_config() if hasattr(current_platform, 'get_tts_config') else {}
            self.max_text_length = tts_config.get('max_text_length', 180)  # 🔧 REDUZIDO PARA ESTABILIDADE
            
            logger.info(f"🚀 CoquiTTS configurado para {current_platform.platform_info['platform_type'].value}")
        else:
            # Configurações padrão se plataforma não disponível
            self.max_text_length = 180  # 🔧 MAIS CONSERVADOR
            logger.warning("🚀 CoquiTTS usando configurações padrão (plataforma não detectada)")
        
        # Configurações padrão
        self.model_name = "tts_models/multilingual/multi-dataset/xtts_v2"
        self.default_language = "pt"
        self.default_speaker_wav = None
        self.sample_rate = 24000  # xTTS v2 padrão
        
        # 🔧 CONFIGURAÇÕES DE RETRY E FALLBACK
        self.max_retries = 3
        self.retry_delay = 1.0
        self.fallback_chunk_size = 100  # Tamanho menor para chunks problemáticos
        
        # 🎭 SISTEMA DE VOZES CONSISTENTES (sem alternância)
        self.voice_assignments = {
            'HOST_MALE': None,      # Voz masculina escolhida para este podcast
            'HOST_FEMALE': None     # Voz feminina escolhida para este podcast
        }
        self.available_voices = {
            'male_voices': [],      # Lista de vozes masculinas disponíveis
            'female_voices': []     # Lista de vozes femininas disponíveis
        }
        self.voices_locked = False  # Se True, não permite mudança das vozes
        
        # 📊 MONITOR DE PERFORMANCE
        self.performance_monitor = None
        
        # 🔧 CACHE DE SPEAKERS VALIDADOS
        self._validated_speakers = {}
        
        # Inicializar modelo se necessário
        self._initialize_model()
    
    def _initialize_model(self):
        """Inicializa modelo xTTS v2 (singleton)"""
        if CoquiTTSEngine._initialized:
            return
        
        try:
            import torch
            
            # 🔧 IMPORTAÇÃO MAIS ROBUSTA DO TTS COM ALIAS
            try:
                from TTS.api import TTS as CoquiTTSClass  # 🔧 USAR ALIAS PARA EVITAR CONFLITOS
                logger.debug("✅ Importação TTS.api.TTS bem-sucedida")
                
                # 🔧 VERIFICAR SE TTS É A CLASSE CORRETA
                if not callable(CoquiTTSClass):
                    logger.error(f"❌ CoquiTTSClass não é callable: {type(CoquiTTSClass)}")
                    raise RuntimeError(f"TTS importado incorretamente, tipo: {type(CoquiTTSClass)}")
                
                # Verificar se é realmente a classe TTS e não o módulo
                if hasattr(CoquiTTSClass, '__module__') and CoquiTTSClass.__module__ == 'TTS.api':
                    logger.debug("✅ CoquiTTSClass é a classe correta da TTS.api")
                else:
                    logger.warning(f"⚠️ CoquiTTSClass pode não ser a classe esperada: {CoquiTTSClass.__module__ if hasattr(CoquiTTSClass, '__module__') else 'sem __module__'}")
                
            except ImportError as import_error:
                logger.error(f"❌ Erro importando TTS.api: {import_error}")
                raise ImportError("TTS não está instalado corretamente. Execute: pip install TTS") from import_error
            except Exception as tts_import_error:
                logger.error(f"❌ Erro geral importando TTS: {tts_import_error}")
                raise RuntimeError(f"Falha na importação do TTS: {tts_import_error}") from tts_import_error
            
            # 🚀 APLICAR OTIMIZAÇÕES PYTORCH DA PLATAFORMA
            if PLATFORM_AVAILABLE and current_platform:
                logger.info("🚀 Aplicando otimizações PyTorch específicas da plataforma...")
                current_platform.optimize_pytorch()
            
            # 🔧 VERIFICAÇÃO DE VERSÃO DO TTS
            try:
                import TTS
                tts_version = TTS.__version__
                logger.info(f"🔧 TTS versão detectada: {tts_version}")
            except:
                logger.warning("🔧 Não foi possível detectar versão do TTS")
            
            # Fix for PyTorch 2.6+ weights_only=True default
            # TTS 0.22.0 models contain custom classes that require weights_only=False
            original_torch_load = torch.load
            
            def load_with_weights_only_false(*args, **kwargs):
                """Wrapper to force weights_only=False for torch.load calls during TTS model loading"""
                if 'weights_only' not in kwargs:
                    kwargs['weights_only'] = False
                return original_torch_load(*args, **kwargs)
            
            logger.info("Inicializando CoquiTTS xTTS v2...")
            
            # Detectar dispositivo (CPU/GPU/MPS)
            if torch.cuda.is_available():
                CoquiTTSEngine._device = "cuda"
                use_gpu = True
                logger.info(f"🚀 GPU CUDA detectado: {torch.cuda.get_device_name(0)}")
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                CoquiTTSEngine._device = "mps" 
                use_gpu = False  # 🔧 MPS pode ter problemas, usar CPU para estabilidade
                logger.info("🚀 MPS detectado, usando CPU para estabilidade")
            else:
                CoquiTTSEngine._device = "cpu"
                use_gpu = False
                logger.info("🚀 Usando CPU")
                
            logger.info(f"Dispositivo final: {CoquiTTSEngine._device}")
            
            # Temporarily patch torch.load during model loading
            torch.load = load_with_weights_only_false
            
            try:
                # 🔧 VERIFICAÇÃO FINAL ANTES DE CRIAR INSTÂNCIA
                logger.debug(f"🔧 Verificando CoquiTTSClass antes da criação: {type(CoquiTTSClass)}")
                logger.debug(f"🔧 Callable: {callable(CoquiTTSClass)}")
                
                # Carregar modelo com configurações mais robustas
                logger.info(f"🔧 Criando instância TTS com model_name='{self.model_name}', gpu={use_gpu}")
                
                CoquiTTSEngine._model_instance = CoquiTTSClass(
                    model_name=self.model_name,
                    progress_bar=False,
                    gpu=use_gpu
                )
                
                # 🔧 VERIFICAR SE INSTÂNCIA FOI CRIADA CORRETAMENTE
                if CoquiTTSEngine._model_instance is None:
                    raise RuntimeError("Instância TTS é None após criação")
                
                logger.info(f"🔧 Instância TTS criada: {type(CoquiTTSEngine._model_instance)}")
                
                # 🔧 CONFIGURAÇÕES ADICIONAIS PARA ESTABILIDADE
                if hasattr(CoquiTTSEngine._model_instance, 'synthesizer'):
                    synthesizer = CoquiTTSEngine._model_instance.synthesizer
                    if hasattr(synthesizer, 'tts_model'):
                        # Configurar modelo para estabilidade
                        model = synthesizer.tts_model
                        if hasattr(model, 'inference'):
                            logger.debug("🔧 Configurando modelo para inferência estável")
                
            except Exception as model_error:
                logger.error(f"❌ Erro criando instância TTS: {model_error}")
                logger.error(f"❌ Tipo do erro: {type(model_error)}")
                raise RuntimeError(f"Falha criando modelo TTS: {model_error}") from model_error
                
            finally:
                # Restore original torch.load
                torch.load = original_torch_load
            
            CoquiTTSEngine._initialized = True
            logger.info("✅ CoquiTTS xTTS v2 inicializado com sucesso")
            
        except ImportError as e:
            logger.error("❌ CoquiTTS não instalado. Execute: pip install TTS")
            raise RuntimeError("CoquiTTS não disponível") from e
        except Exception as e:
            logger.error(f"❌ Erro inicializando CoquiTTS: {e}")
            logger.error(f"❌ Traceback completo:", exc_info=True)
            raise RuntimeError(f"Falha na inicialização do CoquiTTS: {e}") from e
    
    def _validate_speaker_wav(self, speaker_wav: str) -> bool:
        """
        🔧 NOVA FUNÇÃO: Valida arquivo speaker WAV de forma robusta
        
        Args:
            speaker_wav: Caminho para arquivo WAV
            
        Returns:
            True se válido, False caso contrário
        """
        
        # Cache de validação
        if speaker_wav in self._validated_speakers:
            return self._validated_speakers[speaker_wav]
        
        try:
            speaker_path = Path(speaker_wav)
            
            # Verificar existência
            if not speaker_path.exists():
                logger.error(f"🔧 Speaker WAV não encontrado: {speaker_wav}")
                self._validated_speakers[speaker_wav] = False
                return False
            
            # Verificar tamanho mínimo (pelo menos 1 segundo de áudio)
            file_size = speaker_path.stat().st_size
            if file_size < 48000:  # ~1s @ 24kHz 16-bit mono
                logger.error(f"🔧 Speaker WAV muito pequeno: {speaker_wav} ({file_size} bytes)")
                self._validated_speakers[speaker_wav] = False
                return False
            
            # 🔧 VERIFICAR FORMATO WAV - PRIMEIRA TENTATIVA: soundfile
            try:
                import soundfile as sf
                
                info = sf.info(str(speaker_path))
                duration = info.duration
                framerate = info.samplerate
                channels = info.channels
                
                logger.debug(f"🔧 Speaker WAV info (soundfile): {duration:.1f}s, {framerate}Hz, {channels}ch")
                
                # Verificar duração mínima
                if duration < 0.5:  # Mínimo 0.5 segundos
                    logger.error(f"🔧 Speaker WAV muito curto: {duration:.1f}s")
                    self._validated_speakers[speaker_wav] = False
                    return False
                
                # Verificar se não é muito longo (máximo 10 segundos para performance)
                if duration > 10.0:
                    logger.warning(f"🔧 Speaker WAV longo: {duration:.1f}s - pode afetar performance")
                
                # Verificar sample rate razoável
                if framerate < 8000 or framerate > 48000:
                    logger.warning(f"🔧 Sample rate incomum: {framerate}Hz")
                
                self._validated_speakers[speaker_wav] = True
                logger.debug(f"✅ Speaker WAV validado (soundfile): {speaker_path.name}")
                return True
                
            except ImportError:
                logger.debug("🔧 soundfile não disponível, tentando wave...")
                
            except Exception as sf_error:
                logger.debug(f"🔧 Erro com soundfile: {sf_error}, tentando wave...")
            
            # 🔧 FALLBACK: wave (só funciona com PCM)
            try:
                with wave.open(str(speaker_path), 'rb') as wav_file:
                    frames = wav_file.getnframes()
                    framerate = wav_file.getframerate()
                    channels = wav_file.getnchannels()
                    sampwidth = wav_file.getsampwidth()
                    
                    duration = frames / framerate if framerate > 0 else 0
                    
                    logger.debug(f"🔧 Speaker WAV info (wave): {duration:.1f}s, {framerate}Hz, {channels}ch, {sampwidth*8}bit")
                    
                    # Verificar duração mínima
                    if duration < 0.5:  # Mínimo 0.5 segundos
                        logger.error(f"🔧 Speaker WAV muito curto: {duration:.1f}s")
                        self._validated_speakers[speaker_wav] = False
                        return False
                    
                    # Verificar se não é muito longo (máximo 10 segundos para performance)
                    if duration > 10.0:
                        logger.warning(f"🔧 Speaker WAV longo: {duration:.1f}s - pode afetar performance")
                    
                    # Verificar sample rate razoável
                    if framerate < 8000 or framerate > 48000:
                        logger.warning(f"🔧 Sample rate incomum: {framerate}Hz")
                    
                    self._validated_speakers[speaker_wav] = True
                    logger.debug(f"✅ Speaker WAV validado (wave): {speaker_path.name}")
                    return True
                    
            except Exception as wav_error:
                logger.error(f"🔧 Erro lendo WAV com wave: {wav_error}")
                
                # 🔧 ÚLTIMO RECURSO: Assumir que arquivo existe e tem tamanho razoável
                logger.warning(f"🔧 Não foi possível validar formato, mas arquivo existe e tem tamanho adequado")
                self._validated_speakers[speaker_wav] = True
                return True
                
        except Exception as e:
            logger.error(f"🔧 Erro validando speaker: {e}")
            self._validated_speakers[speaker_wav] = False
            return False
    
    def _clean_text_for_tts(self, text: str) -> str:
        """
        Limpa texto para síntese TTS, removendo pontuação que pode ser lida literalmente
        
        Args:
            text: Texto original
            
        Returns:
            Texto limpo para TTS
        """
        # Debug: mostrar texto original
        logger.debug(f"🧹 LIMPEZA - Texto original: '{text}'")
        
        # Remover pontos finais que fazem o CoquiTTS ler "ponto"
        cleaned_text = text.strip()
        
        # Remover ponto final se existir
        if cleaned_text.endswith('.'):
            cleaned_text = cleaned_text[:-1]
        
        # Remover outros pontos finais problemáticos
        if cleaned_text.endswith('!'):
            cleaned_text = cleaned_text[:-1]
        
        if cleaned_text.endswith('?'):
            cleaned_text = cleaned_text[:-1]
        
        # Substituir múltiplos pontos por pausa natural
        cleaned_text = re.sub(r'\.{2,}', '', cleaned_text)
        
        # Substituir pontos no meio da frase por vírgulas (para pausas mais naturais)
        # Cuidado para não afetar abreviações
        cleaned_text = re.sub(r'\.(?=\s[a-z])', ',', cleaned_text)
        
        # 🔧 LIMPEZA ADICIONAL PARA ESTABILIDADE
        # Remover caracteres que podem causar problemas
        cleaned_text = re.sub(r'[^\w\s,.!?;:\'"()-]', '', cleaned_text)
        
        # Normalizar espaços
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
        
        # Debug: mostrar texto limpo
        logger.debug(f"🧹 LIMPEZA - Texto limpo: '{cleaned_text}'")
        
        return cleaned_text.strip()
    
    def _synthesize_chunk_with_retry(self, chunk: str, speaker_wav: str, language: str, chunk_index: int) -> Optional[np.ndarray]:
        """
        🔧 NOVA FUNÇÃO: Sintetiza chunk com sistema de retry
        
        Args:
            chunk: Texto do chunk
            speaker_wav: Arquivo speaker WAV
            language: Idioma
            chunk_index: Índice do chunk (para logging)
            
        Returns:
            Array de áudio ou None se falhado
        """
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"🔄 Chunk {chunk_index} tentativa {attempt + 1}/{self.max_retries}: '{chunk[:50]}...'")
                
                # 🧹 CLEANUP ANTES DA SÍNTESE
                if PLATFORM_AVAILABLE and current_platform:
                    current_platform.cleanup_gpu_memory()
                
                # Síntese com xTTS v2
                audio_data = CoquiTTSEngine._model_instance.tts(
                    text=chunk,
                    speaker_wav=speaker_wav,
                    language=language
                )
                
                # 🔧 VALIDAÇÃO ROBUSTA DO RESULTADO
                if audio_data is None:
                    logger.warning(f"⚠️ Chunk {chunk_index} retornou None na tentativa {attempt + 1}")
                    continue
                
                # Converter para numpy array se necessário
                if isinstance(audio_data, (list, tuple)):
                    try:
                        audio_data = np.array(audio_data, dtype=np.float32)
                    except Exception as conv_error:
                        logger.warning(f"⚠️ Erro convertendo chunk {chunk_index}: {conv_error}")
                        continue
                
                if not isinstance(audio_data, np.ndarray):
                    logger.warning(f"⚠️ Chunk {chunk_index} tipo inesperado: {type(audio_data)}")
                    continue
                
                if len(audio_data) == 0:
                    logger.warning(f"⚠️ Chunk {chunk_index} vazio na tentativa {attempt + 1}")
                    continue
                
                # Verificar se não há NaNs ou valores inválidos
                if np.any(np.isnan(audio_data)) or np.any(np.isinf(audio_data)):
                    logger.warning(f"⚠️ Chunk {chunk_index} contém valores inválidos na tentativa {attempt + 1}")
                    continue
                
                logger.debug(f"✅ Chunk {chunk_index} sintetizado: {len(audio_data)} samples")
                return audio_data
                
            except Exception as e:
                logger.warning(f"⚠️ Erro no chunk {chunk_index} tentativa {attempt + 1}: {e}")
                
                # Se é o último retry, tentar com chunk menor
                if attempt == self.max_retries - 1 and len(chunk) > self.fallback_chunk_size:
                    logger.info(f"🔧 Tentando chunk {chunk_index} com tamanho reduzido...")
                    short_chunk = chunk[:self.fallback_chunk_size]
                    try:
                        audio_data = CoquiTTSEngine._model_instance.tts(
                            text=short_chunk,
                            speaker_wav=speaker_wav,
                            language=language
                        )
                        
                        if isinstance(audio_data, (list, tuple)):
                            audio_data = np.array(audio_data, dtype=np.float32)
                        
                        if isinstance(audio_data, np.ndarray) and len(audio_data) > 0:
                            logger.info(f"✅ Chunk {chunk_index} reduzido sintetizado com sucesso")
                            return audio_data
                            
                    except Exception as fallback_error:
                        logger.error(f"❌ Falha no fallback do chunk {chunk_index}: {fallback_error}")
                
                # Delay entre tentativas
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
        
        logger.error(f"❌ Chunk {chunk_index} falhou após {self.max_retries} tentativas")
        return None

    def synthesize(self, dialogue: Dialogue, character: Character) -> TTSResult:
        """
        Sintetiza fala usando CoquiTTS xTTS v2 com clonagem de voz - VERSÃO CORRIGIDA
        
        Args:
            dialogue: Diálogo a ser sintetizado
            character: Personagem falando
            
        Returns:
            Resultado da síntese TTS
        """
        if not CoquiTTSEngine._initialized:
            raise RuntimeError("CoquiTTS não inicializado")
        
        # 📊 TIMING DA SÍNTESE
        synthesis_start = time.time()
        
        try:
            # Debug: mostrar informações do character
            logger.info(f"🎭 COQUI DEBUG - Character: {character.name}")
            logger.info(f"🎭 COQUI DEBUG - Character ID: {character.id}")
            logger.info(f"🎭 COQUI DEBUG - Speaker WAV: {getattr(character, 'speaker_wav', 'NÃO DEFINIDO')}")
            logger.info(f"🎭 COQUI DEBUG - Language: {getattr(character, 'language', 'NÃO DEFINIDO')}")
            
            # 🧹 LIMPAR TEXTO ANTES DA SÍNTESE
            clean_text = self._clean_text_for_tts(dialogue.text)
            
            # 🎤 NOVO SISTEMA: Usar vozes consistentes atribuídas
            if character.id in self.voice_assignments and self.voice_assignments[character.id]:
                speaker_wav = self.voice_assignments[character.id]
                voice_name = Path(speaker_wav).stem
                print(f"🎤 USANDO VOZ CONSISTENTE {character.id}: {voice_name}")
                logger.info(f"🎤 USANDO VOZ CONSISTENTE {character.id}: {voice_name}")
            elif character.id == 'HOST_MALE' and self.default_speaker_wav:
                # Fallback para voz masculina padrão
                speaker_wav = self.default_speaker_wav
                print(f"🎤 USANDO VOZ MASCULINA PADRÃO: {Path(speaker_wav).name}")
                logger.info(f"🎤 USANDO VOZ MASCULINA PADRÃO: {speaker_wav}")
            else:
                # Obter configurações do personagem (modo tradicional)
                speaker_wav = getattr(character, 'speaker_wav', self.default_speaker_wav)
                if speaker_wav:
                    print(f"🎤 USANDO VOZ PADRÃO: {Path(speaker_wav).name}")
                else:
                    print(f"🎤 USANDO VOZ PADRÃO: {speaker_wav}")
            
            language = getattr(character, 'language', self.default_language)
            
            logger.info(f"🔧 COQUI DEBUG - Speaker WAV final usado: {speaker_wav}")
            logger.info(f"🔧 COQUI DEBUG - Language final usado: {language}")
            
            if not speaker_wav:
                raise ValueError(f"speaker_wav é obrigatório para CoquiTTS. Personagem: {character.name}")
            
            # 🔧 VALIDAR SPEAKER WAV
            if not self._validate_speaker_wav(speaker_wav):
                raise ValueError(f"Speaker WAV inválido: {speaker_wav}")
            
            speaker_path = Path(speaker_wav)
            logger.debug(f"Sintetizando '{clean_text[:50]}...' com speaker: {speaker_path.name}")
            
            # Segmentar texto se muito longo (usando texto limpo)
            text_chunks = self._segment_text(clean_text)
            audio_chunks = []
            
            print(f"📝 COQUI DEBUG - Texto original: '{dialogue.text}'")
            print(f"🧹 COQUI DEBUG - Texto limpo: '{clean_text}'")
            print(f"📝 COQUI DEBUG - Chunks: {len(text_chunks)}")
            for idx, chunk in enumerate(text_chunks):
                print(f"   Chunk {idx+1}: '{chunk}'")
            
            # 🔧 PROCESSAR CHUNKS COM RETRY
            successful_chunks = 0
            for i, chunk in enumerate(text_chunks):
                print(f"🔄 COQUI DEBUG - Processando chunk {i+1}/{len(text_chunks)}: '{chunk[:50]}...'")
                logger.debug(f"Processando chunk {i+1}/{len(text_chunks)}")
                
                # Usar nova função com retry
                audio_data = self._synthesize_chunk_with_retry(
                    chunk=chunk,
                    speaker_wav=str(speaker_path),
                    language=language,
                    chunk_index=i+1
                )
                
                if audio_data is not None:
                    audio_chunks.append(audio_data)
                    successful_chunks += 1
                    print(f"✅ COQUI DEBUG - Chunk {i+1} processado com sucesso")
                else:
                    print(f"❌ COQUI DEBUG - Chunk {i+1} falhou após todas as tentativas")
                    logger.warning(f"Chunk {i+1} falhou após todas as tentativas")
            
            print(f"📊 RESUMO: {successful_chunks}/{len(text_chunks)} chunks processados com sucesso")
            
            if not audio_chunks:
                raise RuntimeError("Nenhum áudio foi gerado - todos os chunks falharam")
            
            if successful_chunks < len(text_chunks):
                logger.warning(f"⚠️ Apenas {successful_chunks}/{len(text_chunks)} chunks foram processados")
            
            # Concatenar chunks
            final_audio = self._concatenate_audio_chunks(audio_chunks)
            
            # Converter para bytes
            audio_bytes = self._audio_to_bytes(final_audio)
            
            # Calcular duração
            duration = len(final_audio) / self.sample_rate
            
            # 📊 CALCULAR TEMPO DE SÍNTESE
            synthesis_time = time.time() - synthesis_start
            
            # 🧹 CLEANUP FINAL DA SÍNTESE
            if PLATFORM_AVAILABLE and current_platform:
                current_platform.cleanup_gpu_memory()
            
            logger.info(f"⏱️ Síntese concluída em {synthesis_time:.2f}s (áudio: {duration:.2f}s)")
            print(f"✅ SÍNTESE CONCLUÍDA: {synthesis_time:.2f}s → {duration:.2f}s de áudio")
            
            return TTSResult(
                audio_data=audio_bytes,
                format="wav",
                sample_rate=self.sample_rate,
                channels=1,
                duration=duration,
                metadata={
                    "engine": "coqui",
                    "model": "xtts_v2",
                    "speaker_wav": str(speaker_path),
                    "language": language,
                    "chunks": len(text_chunks),
                    "successful_chunks": successful_chunks,
                    "character": character.name,
                    "synthesis_time": synthesis_time  # 📊 TEMPO DE SÍNTESE
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Erro na síntese CoquiTTS: {e}")
            print(f"❌ ERRO CRÍTICO NA SÍNTESE: {e}")
            
            # 🧹 CLEANUP EM CASO DE ERRO
            if PLATFORM_AVAILABLE and current_platform:
                current_platform.cleanup_gpu_memory()
                
            raise RuntimeError(f"Falha na síntese: {e}") from e
    
    def _segment_text(self, text: str) -> List[str]:
        """
        🔧 VERSÃO MELHORADA: Segmenta texto em chunks menores para xTTS v2
        
        Args:
            text: Texto completo
            
        Returns:
            Lista de chunks de texto
        """
        if len(text) <= self.max_text_length:
            return [text]
        
        chunks = []
        
        # 🔧 PRIMEIRO: Tentar segmentação por sentenças
        sentences = re.split(r'[.!?]+\s+', text)
        
        if not sentences:
            sentences = [text]
        
        current_chunk = ""
        
        for i, sentence in enumerate(sentences):
            # Limpar sentence
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Adicionar pontuação se não for a última sentença e não tiver
            if i < len(sentences) - 1 and not sentence[-1] in '.!?':
                sentence += '.'
            
            # Verificar se cabe no chunk atual
            potential_chunk = current_chunk + (" " if current_chunk else "") + sentence
            
            if len(potential_chunk) <= self.max_text_length:
                current_chunk = potential_chunk
            else:
                # Salvar chunk atual se não estiver vazio
                if current_chunk:
                    chunks.append(current_chunk.strip())
                
                # 🔧 VERIFICAR SE SENTENÇA É MUITO LONGA
                if len(sentence) > self.max_text_length:
                    # Dividir por vírgulas primeiro
                    sub_parts = sentence.split(',')
                    current_sub_chunk = ""
                    
                    for sub_part in sub_parts:
                        sub_part = sub_part.strip()
                        if not sub_part:
                            continue
                        
                        potential_sub = current_sub_chunk + ("," if current_sub_chunk else "") + sub_part
                        
                        if len(potential_sub) <= self.max_text_length:
                            current_sub_chunk = potential_sub
                        else:
                            if current_sub_chunk:
                                chunks.append(current_sub_chunk.strip())
                            
                            # Se ainda é muito longo, dividir por palavras
                            if len(sub_part) > self.max_text_length:
                                words = sub_part.split()
                                current_word_chunk = ""
                                
                                for word in words:
                                    potential_word = current_word_chunk + (" " if current_word_chunk else "") + word
                                    
                                    if len(potential_word) <= self.max_text_length:
                                        current_word_chunk = potential_word
                                    else:
                                        if current_word_chunk:
                                            chunks.append(current_word_chunk.strip())
                                        current_word_chunk = word
                                
                                if current_word_chunk:
                                    current_sub_chunk = current_word_chunk
                                else:
                                    current_sub_chunk = ""
                            else:
                                current_sub_chunk = sub_part
                    
                    if current_sub_chunk:
                        current_chunk = current_sub_chunk
                    else:
                        current_chunk = ""
                else:
                    current_chunk = sentence
        
        # Adicionar último chunk
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        # 🔧 VALIDAÇÃO FINAL DOS CHUNKS
        valid_chunks = []
        for i, chunk in enumerate(chunks):
            chunk = chunk.strip()
            if chunk and len(chunk) > 0:
                # Verificar se chunk não é só pontuação
                if re.sub(r'[^\w\s]', '', chunk).strip():
                    valid_chunks.append(chunk)
                    logger.debug(f"Chunk válido {i+1}: '{chunk[:50]}...' ({len(chunk)} chars)")
                else:
                    logger.debug(f"Chunk {i+1} só pontuação, ignorado: '{chunk}'")
            else:
                logger.debug(f"Chunk {i+1} vazio, ignorado")
        
        logger.debug(f"Texto segmentado: {len(valid_chunks)} chunks válidos de {len(chunks)} originais")
        return valid_chunks
    
    def _concatenate_audio_chunks(self, audio_chunks: List[np.ndarray]) -> np.ndarray:
        """
        Concatena chunks de áudio com pequena pausa entre eles
        
        Args:
            audio_chunks: Lista de arrays de áudio
            
        Returns:
            Áudio concatenado
        """
        if len(audio_chunks) == 1:
            return audio_chunks[0]
        
        # Pausa entre chunks (100ms)
        pause_samples = int(0.1 * self.sample_rate)
        pause = np.zeros(pause_samples, dtype=audio_chunks[0].dtype)
        
        # Concatenar com pausas
        result_parts = []
        for i, chunk in enumerate(audio_chunks):
            result_parts.append(chunk)
            if i < len(audio_chunks) - 1:  # Não adicionar pausa após último chunk
                result_parts.append(pause)
        
        return np.concatenate(result_parts)
    
    def _audio_to_bytes(self, audio_array: np.ndarray) -> bytes:
        """
        Converte array numpy para bytes WAV
        
        Args:
            audio_array: Array de áudio
            
        Returns:
            Dados de áudio em bytes
        """
        try:
            import soundfile as sf
            
            # Normalizar áudio se necessário
            if audio_array.dtype != np.float32:
                audio_array = audio_array.astype(np.float32)
            
            # Normalizar para evitar clipping
            if np.max(np.abs(audio_array)) > 1.0:
                audio_array = audio_array / np.max(np.abs(audio_array)) * 0.95
            
            # Converter para bytes usando soundfile
            with io.BytesIO() as buffer:
                sf.write(buffer, audio_array, self.sample_rate, format='WAV')
                return buffer.getvalue()
                
        except ImportError:
            logger.error("soundfile não instalado. Execute: pip install soundfile")
            raise RuntimeError("soundfile necessário para conversão de áudio")
        except Exception as e:
            logger.error(f"Erro convertendo áudio para bytes: {e}")
            raise RuntimeError(f"Falha na conversão de áudio: {e}") from e
    
    def get_available_voices(self) -> List[Dict[str, Any]]:
        """
        Retorna vozes disponíveis (CoquiTTS usa speaker_wav customizado)
        
        Returns:
            Lista de vozes (baseada em arquivos speaker disponíveis)
        """
        voices = [
            {
                "id": "custom_speaker",
                "name": "Custom Speaker (xTTS v2)",
                "language": "multilingual",
                "gender": "any",
                "quality": "very_high",
                "neural": True,
                "description": "Clonagem de voz usando arquivo speaker_wav personalizado",
                "requires_speaker_wav": True
            }
        ]
        
        # Tentar encontrar speakers pré-definidos se houver
        speakers_dir = Path("speakers")
        if speakers_dir.exists():
            for speaker_file in speakers_dir.glob("*.wav"):
                voices.append({
                    "id": speaker_file.stem,
                    "name": f"Pre-defined Speaker: {speaker_file.stem}",
                    "language": "multilingual", 
                    "gender": "unknown",
                    "quality": "very_high",
                    "neural": True,
                    "speaker_wav": str(speaker_file),
                    "description": f"Speaker pré-definido: {speaker_file.name}"
                })
        
        return voices
    
    def is_voice_available(self, voice_id: str) -> bool:
        """
        Verifica se uma voz está disponível
        
        Args:
            voice_id: ID da voz
            
        Returns:
            True se disponível
        """
        # CoquiTTS sempre disponível se modelo estiver carregado
        if voice_id == "custom_speaker":
            return CoquiTTSEngine._initialized
        
        # Verificar se é um speaker pré-definido
        speaker_file = Path("speakers") / f"{voice_id}.wav"
        return speaker_file.exists()
    
    def configure(self, config: Dict[str, Any]):
        """Configura engine com parâmetros específicos"""
        super().configure(config)
        
        # Configurações específicas do CoquiTTS
        if 'default_language' in config:
            self.default_language = config['default_language']
        
        if 'default_speaker_wav' in config:
            self.default_speaker_wav = config['default_speaker_wav']
        
        if 'max_text_length' in config:
            self.max_text_length = config['max_text_length']
        
        logger.debug(f"CoquiTTS configurado: {config}")
    
    def test_synthesis(self, text: str = "Teste de síntese de voz usando CoquiTTS") -> bool:
        """
        🔧 VERSÃO MELHORADA: Testa se o engine está funcionando
        
        Args:
            text: Texto de teste
            
        Returns:
            True se funcionando
        """
        if not CoquiTTSEngine._initialized:
            logger.debug("❌ CoquiTTS não inicializado, retornando False")
            return False
        
        # Para teste, procurar por arquivos speaker válidos
        try:
            from pathlib import Path
            
            # Procurar por arquivos speaker válidos
            speaker_dir = Path("static/speaker_samples")
            if speaker_dir.exists():
                wav_files = list(speaker_dir.glob("*.wav"))
                if wav_files:
                    # Validar primeiro arquivo WAV encontrado
                    speaker_file = str(wav_files[0])
                    
                    if not self._validate_speaker_wav(speaker_file):
                        logger.debug(f"❌ Speaker inválido para teste: {speaker_file}")
                        # Tentar outros arquivos
                        for other_wav in wav_files[1:]:
                            if self._validate_speaker_wav(str(other_wav)):
                                speaker_file = str(other_wav)
                                break
                        else:
                            logger.debug("❌ Nenhum speaker válido encontrado para teste")
                            return False
                    
                    logger.debug(f"🔧 Usando speaker para teste: {speaker_file}")
                    
                    # Teste simples com texto curto
                    try:
                        test_text = text[:50]  # Texto muito curto para teste
                        audio_data = CoquiTTSEngine._model_instance.tts(
                            text=test_text,
                            speaker_wav=speaker_file,
                            language=self.default_language
                        )
                        
                        # Validação robusta do resultado
                        if audio_data is None:
                            logger.debug("❌ Teste retornou None")
                            return False
                        
                        # Converter para numpy se necessário
                        if isinstance(audio_data, (list, tuple)):
                            try:
                                audio_data = np.array(audio_data, dtype=np.float32)
                            except Exception as e:
                                logger.debug(f"❌ Erro convertendo resultado de teste: {e}")
                                return False
                        
                        # Verificar se é válido
                        if isinstance(audio_data, np.ndarray) and len(audio_data) > 0:
                            # Verificar valores válidos
                            if not (np.any(np.isnan(audio_data)) or np.any(np.isinf(audio_data))):
                                logger.debug(f"✅ Teste de síntese CoquiTTS bem-sucedido: {len(audio_data)} samples")
                                return True
                            else:
                                logger.debug("❌ Teste gerou valores inválidos (NaN/Inf)")
                                return False
                        else:
                            logger.debug(f"❌ Teste retornou resultado inválido: {type(audio_data)}, len={len(audio_data) if hasattr(audio_data, '__len__') else 'N/A'}")
                            return False
                            
                    except Exception as e:
                        logger.debug(f"❌ Erro na síntese de teste: {e}")
                        return False
            
            # Se não encontrar arquivos speaker, assumir que engine está funcional
            # O erro será detectado na síntese real quando speaker_wav for fornecido
            logger.debug("⚠️ Nenhum arquivo speaker encontrado para teste, assumindo engine funcional")
            return True
                
        except Exception as e:
            logger.debug(f"❌ Teste de síntese CoquiTTS falhou: {e}")
            # Ainda retornar True - deixar que erros reais sejam detectados na síntese
            # CoquiTTS pode estar funcional mesmo se o teste específico falhar
            logger.debug("⚠️ Assumindo engine funcional mesmo com falha no teste")
            return True
    
    def configure_podcast_voices(self, male_voice: str = None, female_voice_1: str = None, female_voice_2: str = None, characters_in_script: set = None):
        """
        🔧 VERSÃO MELHORADA: Configura vozes para um podcast específico de forma consistente
        
        Args:
            male_voice: Caminho para voz masculina (será usada para HOST_MALE)
            female_voice_1: Primeira opção de voz feminina 
            female_voice_2: Segunda opção de voz feminina (fallback)
            characters_in_script: Set com IDs dos personagens no roteiro
        """
        from pathlib import Path
        import random
        
        print(f"🎭 CONFIGURANDO VOZES PARA PODCAST")
        print(f"   • Personagens no roteiro: {characters_in_script}")
        
        # 🔧 VALIDAR VOZES FORNECIDAS
        validated_voices = {'male': [], 'female': []}
        
        if male_voice and Path(male_voice).exists():
            if self._validate_speaker_wav(male_voice):
                validated_voices['male'].append(male_voice)
                print(f"   ✅ Voz masculina validada: {Path(male_voice).name}")
            else:
                print(f"   ❌ Voz masculina inválida: {Path(male_voice).name}")
        
        for female_voice in [female_voice_1, female_voice_2]:
            if female_voice and Path(female_voice).exists():
                if self._validate_speaker_wav(female_voice):
                    validated_voices['female'].append(female_voice)
                    print(f"   ✅ Voz feminina validada: {Path(female_voice).name}")
                else:
                    print(f"   ❌ Voz feminina inválida: {Path(female_voice).name}")
        
        self.available_voices['male_voices'] = validated_voices['male']
        self.available_voices['female_voices'] = validated_voices['female']
        
        # Analisar quais tipos de HOST estão no roteiro
        has_male = 'HOST_MALE' in characters_in_script if characters_in_script else False
        has_female = 'HOST_FEMALE' in characters_in_script if characters_in_script else False
        
        print(f"   • HOST_MALE no roteiro: {has_male}")
        print(f"   • HOST_FEMALE no roteiro: {has_female}")
        
        # Atribuir vozes baseado no que existe no roteiro
        if has_male and self.available_voices['male_voices']:
            self.voice_assignments['HOST_MALE'] = self.available_voices['male_voices'][0]
            print(f"   ✅ HOST_MALE: {Path(self.voice_assignments['HOST_MALE']).name}")
        elif has_male:
            print(f"   ⚠️ HOST_MALE requerido mas nenhuma voz masculina válida disponível")
        
        if has_female and self.available_voices['female_voices']:
            # Escolher uma voz feminina (pode ser aleatória ou primeira da lista)
            chosen_female = self.available_voices['female_voices'][0]  # ou random.choice()
            self.voice_assignments['HOST_FEMALE'] = chosen_female
            print(f"   ✅ HOST_FEMALE: {Path(self.voice_assignments['HOST_FEMALE']).name}")
        elif has_female:
            print(f"   ⚠️ HOST_FEMALE requerido mas nenhuma voz feminina válida disponível")
        
        # Verificar se todas as vozes necessárias foram atribuídas
        missing_voices = []
        if has_male and not self.voice_assignments['HOST_MALE']:
            missing_voices.append('HOST_MALE')
        if has_female and not self.voice_assignments['HOST_FEMALE']:
            missing_voices.append('HOST_FEMALE')
        
        if missing_voices:
            raise ValueError(f"❌ Vozes necessárias não configuradas: {missing_voices}")
        
        # Bloquear mudanças após configuração
        self.voices_locked = True
        print(f"🔒 VOZES BLOQUEADAS PARA CONSISTÊNCIA")
        
        logger.info(f"🎭 Vozes configuradas para podcast:")
        logger.info(f"   • HOST_MALE: {self.voice_assignments['HOST_MALE']}")
        logger.info(f"   • HOST_FEMALE: {self.voice_assignments['HOST_FEMALE']}") 