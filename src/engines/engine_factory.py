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
        self._default_engine = "coqui"
        self._engine_instances: Dict[str, BaseTTSEngine] = {}
        self._fallback_order = ["coqui", "piper"]
        
        # Auto-registrar engines disponíveis
        self._register_available_engines()
    
    def _register_available_engines(self):
        """Registra todos os engines TTS disponíveis no sistema"""
        
        # Registrar Piper TTS se disponível
        self._register_piper_if_available()
        
        # Registrar CoquiTTS se disponível
        self._register_coqui_if_available()
    
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
                
            else:
                logger.warning("Piper TTS encontrado mas sem modelos disponíveis")
                
        except ImportError:
            logger.debug("Módulo PiperTTS não encontrado")
        except Exception as e:
            logger.warning(f"Erro registrando Piper TTS: {e}")
    
    def _register_coqui_if_available(self):
        """Registra CoquiTTS se estiver disponível no sistema"""
        try:
            # Tentar importar CoquiTTSEngine
            from .coqui_tts import CoquiTTSEngine
            
            # Testar se CoquiTTS está funcional
            test_engine = CoquiTTSEngine()
            
            # CoquiTTS está funcional, registrar
            TTSEngineRegistry.register(
                "coqui",
                CoquiTTSEngine,
                platform="cross-platform",
                quality="very_high",
                speed="slow",
                offline=True,
                neural=True,
                voice_cloning=True,
                languages=["pt", "en", "es", "fr", "de", "it", "pl", "tr", "ru", "nl", "cs", "ar", "zh-cn", "ja", "hu", "ko"],
                description="Engine TTS neural com clonagem de voz usando xTTS v2",
                model_name="xtts_v2"
            )
            
            logger.info("CoquiTTS (xTTS v2) registrado com sucesso")
                
        except ImportError:
            logger.debug("Módulo CoquiTTS não encontrado")
        except Exception as e:
            logger.warning(f"Erro registrando CoquiTTS: {e}")
    
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
        Cria instância de engine TTS por nome
        
        Args:
            name: Nome do engine ('piper', 'coqui', etc.)
            config: Configurações específicas do engine
            
        Returns:
            Instância do engine configurado
            
        Raises:
            RuntimeError: Se o engine não puder ser criado
        """
        
        # Verificar se já existe instância (singleton)
        if name in self._engine_instances:
            logger.debug(f"Retornando instância existente do engine: {name}")
            return self._engine_instances[name]
        
        # Obter classe do engine
        engine_class = TTSEngineRegistry.get_engine_class(name)
        
        if not engine_class:
            # Engine não encontrado, tentar fallback
            logger.warning(f"Engine '{name}' não encontrado, tentando fallback")
            return self.create_engine_with_fallback(name, config)
        
        try:
            # Criar nova instância
            logger.info(f"Criando nova instância do engine: {name}")
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
            # Tentar fallback
            return self.create_engine_with_fallback(name, config)
    
    def create_engine_with_fallback(self, preferred_engine: str, config: Optional[Dict[str, Any]] = None) -> BaseTTSEngine:
        """
        Cria engine com fallback automático
        
        Args:
            preferred_engine: Engine preferido
            config: Configurações
            
        Returns:
            Engine funcional (preferido ou fallback)
            
        Raises:
            RuntimeError: Se nenhum engine funcionar
        """
        
        # Criar lista de engines para tentar
        engines_to_try = []
        
        # Adicionar engine preferido primeiro (se válido)
        if preferred_engine in TTSEngineRegistry.get_available_engines():
            engines_to_try.append(preferred_engine)
        
        # Adicionar engines da ordem de fallback
        for engine_name in self._fallback_order:
            if engine_name not in engines_to_try and engine_name in TTSEngineRegistry.get_available_engines():
                engines_to_try.append(engine_name)
        
        # Tentar criar engines em ordem
        last_error = None
        for engine_name in engines_to_try:
            try:
                logger.info(f"Tentando criar engine: {engine_name}")
                
                # Verificar se já existe instância
                if engine_name in self._engine_instances:
                    logger.info(f"Usando instância existente: {engine_name}")
                    return self._engine_instances[engine_name]
                
                # Criar nova instância diretamente
                engine_class = TTSEngineRegistry.get_engine_class(engine_name)
                engine = engine_class()
                
                # Aplicar configurações
                if config:
                    engine.configure(config)
                
                # Validar
                if self._validate_engine(engine):
                    self._engine_instances[engine_name] = engine
                    logger.info(f"Engine '{engine_name}' criado com sucesso")
                    return engine
                else:
                    logger.warning(f"Engine '{engine_name}' falhou na validação")
                    
            except Exception as e:
                logger.warning(f"Falha criando engine '{engine_name}': {e}")
                last_error = e
                continue
        
        # Se chegou aqui, nenhum engine funcionou
        available_engines = TTSEngineRegistry.get_available_engines()
        error_msg = f"Nenhum engine TTS funcional encontrado. Disponíveis: {available_engines}"
        if last_error:
            error_msg += f". Último erro: {last_error}"
        
        raise RuntimeError(error_msg)
    
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