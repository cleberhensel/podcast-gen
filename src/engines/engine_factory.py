"""
Factory para Engines TTS
Implementa Factory Pattern para criação e gerenciamento de engines
"""

from typing import Dict, Type, List, Optional, Any
import logging
from abc import ABC, abstractmethod

from .base_engine import BaseTTSEngine
from .macos_tts import MacOSTTSEngine

logger = logging.getLogger(__name__)

class TTSEngineRegistry:
    """Registry para engines TTS disponíveis"""
    
    _engines: Dict[str, Type[BaseTTSEngine]] = {}
    _engine_info: Dict[str, Dict[str, Any]] = {}
    
    @classmethod
    def register(cls, name: str, engine_class: Type[BaseTTSEngine], **metadata):
        """
        Registra um engine TTS
        
        Args:
            name: Nome único do engine
            engine_class: Classe do engine
            metadata: Metadados adicionais (plataforma, qualidade, etc.)
        """
        cls._engines[name] = engine_class
        cls._engine_info[name] = {
            'class': engine_class.__name__,
            'module': engine_class.__module__,
            **metadata
        }
        logger.debug(f"Engine '{name}' registrado: {engine_class.__name__}")
    
    @classmethod
    def get_engine_class(cls, name: str) -> Optional[Type[BaseTTSEngine]]:
        """Retorna classe do engine pelo nome"""
        return cls._engines.get(name)
    
    @classmethod
    def get_available_engines(cls) -> List[str]:
        """Retorna lista de engines disponíveis"""
        return list(cls._engines.keys())
    
    @classmethod
    def get_engine_info(cls, name: str) -> Optional[Dict[str, Any]]:
        """Retorna informações sobre um engine"""
        return cls._engine_info.get(name)
    
    @classmethod
    def get_all_engines_info(cls) -> Dict[str, Dict[str, Any]]:
        """Retorna informações de todos os engines"""
        return cls._engine_info.copy()

class TTSEngineFactory:
    """
    Factory para criação de engines TTS
    
    Implementa Strategy Pattern + Factory Pattern para alternância suave
    entre diferentes tecnologias TTS
    """
    
    def __init__(self):
        self._default_engine = "coqui"  # Coqui como padrão por ter melhor qualidade
        self._engine_instances: Dict[str, BaseTTSEngine] = {}
        self._fallback_order = ["coqui", "piper", "macos"]  # Coqui primeiro, depois Piper, depois macOS
        
        # Auto-registrar engines padrão
        self._register_default_engines()
    
    def _register_default_engines(self):
        """Registra engines padrão do sistema"""
        
        # macOS TTS - Sempre disponível no macOS
        TTSEngineRegistry.register(
            "macos", 
            MacOSTTSEngine,
            platform="macOS",
            quality="high",
            speed="fast",
            offline=True,
            languages=["pt-BR", "en-US", "es-ES"],
            description="Engine TTS nativo do macOS usando comando 'say'"
        )
        
        # Coqui TTS XTTS - Tentar registrar se disponível
        self._register_coqui_if_available()
        
        # Piper TTS - Tentar registrar se disponível
        self._register_piper_if_available()
    
    def _register_coqui_if_available(self):
        """Registra Coqui TTS XTTS se estiver disponível no sistema"""
        try:
            # Tentar importar CoquiTTSEngine
            from .coqui_tts import CoquiTTSEngine
            
            # Testar se Coqui TTS está funcional
            test_engine = CoquiTTSEngine()
            
            if test_engine._coqui_available and test_engine._model_loaded:
                # Coqui TTS está funcional, registrar
                TTSEngineRegistry.register(
                    "coqui",
                    CoquiTTSEngine,
                    platform="cross-platform",
                    quality="excellent", 
                    speed="medium",
                    offline=True,
                    neural=True,
                    voice_cloning=True,
                    multilingual=True,
                    languages=["pt-BR", "en-US", "es-ES", "fr-FR", "de-DE", "it-IT", "pl-PL", "tr-TR", "ru-RU", "nl-NL", "cs-CZ", "ar-AR", "zh-CN", "ja-JP", "hu-HU", "ko-KR"],
                    description="Engine TTS neural avançado usando Coqui XTTS v2 com clonagem de voz",
                    model_name=test_engine._model_name,
                    speakers_count=len(test_engine._available_speakers),
                    features=["voice_cloning", "multilingual", "high_quality", "neural"]
                )
                
                logger.info(f"Coqui TTS XTTS registrado com {len(test_engine._available_speakers)} speakers")
                
                # Atualizar ordem de fallback (Coqui primeiro por ter melhor qualidade)
                if "coqui" not in self._fallback_order:
                    self._fallback_order.insert(0, "coqui")  # Coqui primeiro
                    
            else:
                logger.warning("Coqui TTS encontrado mas modelo não carregado")
                
        except ImportError:
            logger.debug("Módulo CoquiTTS não encontrado")
        except Exception as e:
            logger.warning(f"Erro registrando Coqui TTS: {e}")
    
    def _register_piper_if_available(self):
        """Registra Piper TTS se estiver disponível no sistema"""
        try:
            # Tentar importar PiperTTSEngine
            from .piper_tts import PiperTTSEngine
            
            # Testar se Piper está funcional
            test_engine = PiperTTSEngine()
            
            if len(test_engine._available_models) > 0:
                # Piper está funcional, registrar
                TTSEngineRegistry.register(
                    "piper",
                    PiperTTSEngine,
                    platform="cross-platform",
                    quality="very_high",
                    speed="medium",
                    offline=True,
                    neural=True,
                    languages=["pt-BR", "en-US", "es-ES", "fr-FR", "de-DE"],
                    description="Engine TTS neural usando Piper (ONNX)",
                    model_count=len(test_engine._available_models),
                    models_path=str(test_engine._models_path) if test_engine._models_path else None
                )
                
                logger.info(f"Piper TTS registrado com {len(test_engine._available_models)} modelos")
                
                # Atualizar ordem de fallback (Piper primeiro se neural)
                if "piper" not in self._fallback_order:
                    self._fallback_order.insert(0, "piper")  # Piper primeiro
                    
            else:
                logger.warning("Piper TTS encontrado mas sem modelos disponíveis")
                
        except ImportError:
            logger.debug("Módulo PiperTTS não encontrado")
        except Exception as e:
            logger.warning(f"Erro registrando Piper TTS: {e}")
    
    def register_engine(self, name: str, engine_class: Type[BaseTTSEngine], **metadata):
        """
        Registra um novo engine
        
        Args:
            name: Nome único do engine
            engine_class: Classe que implementa BaseTTSEngine
            metadata: Metadados sobre o engine
        """
        TTSEngineRegistry.register(name, engine_class, **metadata)
        
        # Atualizar ordem de fallback se necessário
        if name not in self._fallback_order:
            self._fallback_order.append(name)
    
    def create_engine(self, name: str, config: Optional[Dict[str, Any]] = None) -> BaseTTSEngine:
        """
        Cria instância de engine TTS
        
        Args:
            name: Nome do engine
            config: Configurações específicas do engine
            
        Returns:
            Instância do engine configurado
            
        Raises:
            ValueError: Se engine não estiver registrado
            RuntimeError: Se engine não puder ser criado
        """
        
        # Verificar se engine está registrado
        engine_class = TTSEngineRegistry.get_engine_class(name)
        if not engine_class:
            available = TTSEngineRegistry.get_available_engines()
            raise ValueError(f"Engine '{name}' não registrado. Disponíveis: {available}")
        
        # Verificar se já existe instância (singleton por engine)
        if name in self._engine_instances:
            logger.debug(f"Retornando instância existente do engine '{name}'")
            return self._engine_instances[name]
        
        try:
            # Criar nova instância
            logger.info(f"Criando nova instância do engine '{name}'")
            engine = engine_class()
            
            # Aplicar configurações
            if config:
                engine.configure(config)
            
            # Validar engine
            if not self._validate_engine(engine):
                raise RuntimeError(f"Engine '{name}' falhou na validação")
            
            # Cache da instância
            self._engine_instances[name] = engine
            
            logger.info(f"Engine '{name}' criado e validado com sucesso")
            return engine
            
        except Exception as e:
            logger.error(f"Erro criando engine '{name}': {e}")
            raise RuntimeError(f"Falha ao criar engine '{name}': {e}")
    
    def create_engine_with_fallback(self, preferred_engine: str, config: Optional[Dict[str, Any]] = None) -> BaseTTSEngine:
        """
        Cria engine com fallback automático
        
        Args:
            preferred_engine: Engine preferido
            config: Configurações
            
        Returns:
            Engine funcional (pode ser fallback)
        """
        
        # Determinar ordem de tentativa
        try_order = [preferred_engine] + [e for e in self._fallback_order if e != preferred_engine]
        
        last_error = None
        
        for engine_name in try_order:
            try:
                logger.info(f"Tentando criar engine: {engine_name}")
                engine = self.create_engine(engine_name, config)
                
                if engine_name != preferred_engine:
                    logger.warning(f"Usando engine fallback '{engine_name}' (preferido era '{preferred_engine}')")
                
                return engine
                
            except Exception as e:
                logger.warning(f"Engine '{engine_name}' falhou: {e}")
                last_error = e
                continue
        
        # Se chegou aqui, nenhum engine funcionou
        raise RuntimeError(f"Nenhum engine TTS funcional encontrado. Último erro: {last_error}")
    
    def _validate_engine(self, engine: BaseTTSEngine) -> bool:
        """
        Valida se engine está funcionando
        
        Args:
            engine: Engine a validar
            
        Returns:
            True se engine está funcional
        """
        try:
            # Teste básico de síntese
            return engine.test_synthesis("Teste")
        except Exception as e:
            logger.error(f"Falha na validação do engine {engine.name}: {e}")
            return False
    
    def get_available_engines(self) -> List[str]:
        """Retorna engines disponíveis"""
        return TTSEngineRegistry.get_available_engines()
    
    def get_engine_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Retorna informações sobre um engine"""
        return TTSEngineRegistry.get_engine_info(name)
    
    def set_default_engine(self, name: str):
        """Define engine padrão"""
        if name not in TTSEngineRegistry.get_available_engines():
            raise ValueError(f"Engine '{name}' não está registrado")
        self._default_engine = name
    
    def get_default_engine(self) -> str:
        """Retorna engine padrão"""
        return self._default_engine
    
    def clear_instances(self):
        """Limpa cache de instâncias (útil para testes)"""
        self._engine_instances.clear()
    
    def get_system_compatibility_report(self) -> Dict[str, Any]:
        """
        Gera relatório de compatibilidade do sistema
        
        Returns:
            Relatório com status de cada engine
        """
        report = {
            'platform': 'macOS',  # Detectar automaticamente se necessário
            'engines': {},
            'recommended': None,
            'fallback_order': self._fallback_order.copy()
        }
        
        for engine_name in TTSEngineRegistry.get_available_engines():
            try:
                engine = self.create_engine(engine_name)
                
                report['engines'][engine_name] = {
                    'available': True,
                    'status': 'functional',
                    'voice_count': len(engine.get_available_voices()),
                    'info': TTSEngineRegistry.get_engine_info(engine_name)
                }
                
                # Determinar recomendado
                if not report['recommended']:
                    report['recommended'] = engine_name
                    
            except Exception as e:
                report['engines'][engine_name] = {
                    'available': False,
                    'status': 'error',
                    'error': str(e),
                    'info': TTSEngineRegistry.get_engine_info(engine_name)
                }
        
        return report

# Instância global do factory (singleton)
tts_factory = TTSEngineFactory() 