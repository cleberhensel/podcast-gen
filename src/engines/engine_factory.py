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
        self._default_engine = "piper"  # Apenas Piper
        self._engine_instances: Dict[str, BaseTTSEngine] = {}
        self._fallback_order = ["piper"]  # Apenas Piper
        
        # Auto-registrar apenas Piper TTS
        self._register_piper_only()
    
    def _register_piper_only(self):
        """Registra APENAS Piper TTS - remove outros engines"""
        
        # Limpar registry primeiro
        TTSEngineRegistry._engines.clear()
        TTSEngineRegistry._engine_info.clear()
        
        # Registrar apenas Piper TTS
        self._register_piper_if_available()
    
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
                
                # Atualizar ordem de fallback (Piper primeiro)
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
        Cria instância de engine TTS - FORÇAR SEMPRE PIPER TTS
        
        Args:
            name: Nome do engine (ignorado - sempre usa Piper)
            config: Configurações específicas do engine
            
        Returns:
            Instância do engine Piper configurado
            
        Raises:
            RuntimeError: Se Piper TTS não puder ser criado
        """
        
        # FORÇAR SEMPRE PIPER TTS - ignorar parâmetro name
        engine_name = "piper"
        
        # Verificar se já existe instância (singleton)
        if engine_name in self._engine_instances:
            logger.debug(f"Retornando instância existente do Piper TTS")
            return self._engine_instances[engine_name]
        
        try:
            # Tentar importar PiperTTSEngine diretamente
            from .piper_tts import PiperTTSEngine
            
            # Criar nova instância
            logger.info(f"Criando nova instância do Piper TTS")
            engine = PiperTTSEngine()
            
            # Aplicar configurações
            if config:
                engine.configure(config)
            
            # Validar engine
            if not self._validate_engine(engine):
                raise RuntimeError(f"Piper TTS falhou na validação")
            
            # Cache da instância
            self._engine_instances[engine_name] = engine
            
            logger.info(f"Piper TTS criado e validado com sucesso")
            return engine
            
        except Exception as e:
            logger.error(f"Erro criando Piper TTS: {e}")
            raise RuntimeError(f"Falha ao criar Piper TTS: {e}")
    
    def create_engine_with_fallback(self, preferred_engine: str, config: Optional[Dict[str, Any]] = None) -> BaseTTSEngine:
        """
        Cria engine - SEMPRE retorna Piper TTS
        
        Args:
            preferred_engine: Ignorado (sempre usa Piper)
            config: Configurações
            
        Returns:
            Engine Piper TTS
        """
        
        # Sempre usar Piper TTS, ignorar preferred_engine
        logger.info(f"Criando Piper TTS (ignorando engine solicitado: {preferred_engine})")
        return self.create_engine("piper", config)
    
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