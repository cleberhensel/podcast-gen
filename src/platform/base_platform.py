from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class BasePlatform(ABC):
    """Interface base para otimizações específicas de plataforma"""
    
    def __init__(self):
        from .detector import PlatformDetector
        self.platform_info = PlatformDetector.get_platform_info()
        self.is_optimized = False
        
        logger.info(f"🔧 Plataforma inicializada: {self.platform_info['platform_type'].value}")
    
    @abstractmethod
    def optimize_pytorch(self):
        """Otimizações específicas do PyTorch para esta plataforma"""
        pass
    
    @abstractmethod
    def cleanup_gpu_memory(self):
        """Limpeza de memória GPU específica da plataforma"""
        pass
    
    @abstractmethod
    def get_optimal_workers(self) -> int:
        """Número ideal de workers para esta plataforma"""
        pass
    
    @abstractmethod
    def get_memory_threshold(self) -> float:
        """Threshold de memória para cleanup agressivo (0.0-1.0)"""
        pass
    
    @abstractmethod
    def configure_audio(self) -> Dict[str, Any]:
        """Configurações de áudio específicas da plataforma"""
        pass
    
    @abstractmethod
    def get_batch_size(self) -> int:
        """Tamanho ideal de batch para processamento"""
        pass
    
    def get_performance_config(self) -> Dict[str, Any]:
        """Configuração de performance geral"""
        return {
            'max_workers': self.get_optimal_workers(),
            'memory_threshold': self.get_memory_threshold(),
            'batch_size': self.get_batch_size(),
            'platform_type': self.platform_info['platform_type'].value,
            'gpu_backend': self.platform_info['gpu_backend'].value,
            'audio_config': self.configure_audio(),
            'is_optimized': self.is_optimized
        }
    
    def initialize_optimizations(self):
        """Inicializa todas as otimizações da plataforma"""
        try:
            logger.info(f"🚀 Inicializando otimizações para {self.platform_info['platform_type'].value}...")
            
            # Aplicar otimizações PyTorch
            self.optimize_pytorch()
            
            # Configurar áudio
            audio_config = self.configure_audio()
            logger.debug(f"Áudio configurado: {audio_config}")
            
            self.is_optimized = True
            logger.info("✅ Otimizações aplicadas com sucesso!")
            
        except Exception as e:
            logger.error(f"❌ Erro aplicando otimizações: {e}")
            self.is_optimized = False
            raise
    
    def get_system_status(self) -> Dict[str, Any]:
        """Status atual do sistema"""
        try:
            import psutil
            
            status = {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'available_memory_gb': psutil.virtual_memory().available / (1024**3),
                'is_optimized': self.is_optimized
            }
            
            # Informações de GPU se disponível
            gpu_backend = self.platform_info['gpu_backend']
            if gpu_backend.value == 'mps':
                # MPS não tem APIs de monitoramento direto
                status['gpu_available'] = True
                status['gpu_type'] = 'Metal Performance Shaders'
            elif gpu_backend.value == 'cuda':
                try:
                    import torch
                    if torch.cuda.is_available():
                        status['gpu_available'] = True
                        status['gpu_memory_allocated'] = torch.cuda.memory_allocated() / (1024**3)
                        status['gpu_memory_reserved'] = torch.cuda.memory_reserved() / (1024**3)
                        status['gpu_type'] = 'NVIDIA CUDA'
                    else:
                        status['gpu_available'] = False
                except:
                    status['gpu_available'] = False
            else:
                status['gpu_available'] = False
                status['gpu_type'] = 'CPU-only'
            
            return status
            
        except Exception as e:
            logger.error(f"Erro obtendo status do sistema: {e}")
            return {'error': str(e)}
    
    def should_cleanup_memory(self) -> bool:
        """Determina se deve fazer cleanup baseado no threshold"""
        try:
            import psutil
            memory_percent = psutil.virtual_memory().percent / 100.0
            threshold = self.get_memory_threshold()
            
            return memory_percent > threshold
            
        except Exception:
            # Em caso de erro, sempre fazer cleanup
            return True
    
    def log_performance_summary(self):
        """Log resumo de performance atual"""
        try:
            status = self.get_system_status()
            config = self.get_performance_config()
            
            logger.info(f"📊 PERFORMANCE SUMMARY:")
            logger.info(f"   • Platform: {config['platform_type']}")
            logger.info(f"   • GPU: {config['gpu_backend']}")
            logger.info(f"   • Workers: {config['max_workers']}")
            logger.info(f"   • Batch Size: {config['batch_size']}")
            logger.info(f"   • Memory Threshold: {config['memory_threshold']:.1%}")
            logger.info(f"   • CPU Usage: {status.get('cpu_percent', 'N/A'):.1f}%")
            logger.info(f"   • Memory Usage: {status.get('memory_percent', 'N/A'):.1f}%")
            
            if status.get('gpu_available'):
                logger.info(f"   • GPU Type: {status.get('gpu_type', 'Unknown')}")
                if 'gpu_memory_allocated' in status:
                    logger.info(f"   • GPU Memory: {status['gpu_memory_allocated']:.1f}GB")
                    
        except Exception as e:
            logger.error(f"Erro no log de performance: {e}") 