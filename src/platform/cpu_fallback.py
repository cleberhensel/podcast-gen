import psutil
import gc
import logging
from typing import Dict, Any
from .base_platform import BasePlatform

logger = logging.getLogger(__name__)

class CPUFallbackPlatform(BasePlatform):
    """Implementação fallback para CPU-only em plataformas não reconhecidas"""
    
    def __init__(self):
        super().__init__()
        logger.warning("🔧 Usando plataforma fallback CPU-only")
        
    def optimize_pytorch(self):
        """Otimizações básicas CPU-only"""
        
        try:
            import torch
            
            # Configurações conservadoras para CPU
            cpu_count = psutil.cpu_count()
            torch.set_num_threads(min(cpu_count, 8))
            torch.set_grad_enabled(False)  # Inferência apenas
            
            logger.info(f"🔧 PyTorch CPU-only: {torch.get_num_threads()} threads")
            
        except ImportError:
            logger.warning("PyTorch não disponível")
        except Exception as e:
            logger.error(f"Erro otimizando PyTorch: {e}")
    
    def cleanup_gpu_memory(self):
        """Cleanup básico (apenas garbage collection)"""
        gc.collect()
    
    def get_optimal_workers(self) -> int:
        """Workers conservadores para CPU-only"""
        
        cpu_count = psutil.cpu_count()
        memory_gb = self.platform_info['memory_gb']
        
        # Conservador para plataformas desconhecidas
        if memory_gb >= 16:
            return min(4, max(2, cpu_count // 2))
        elif memory_gb >= 8:
            return min(3, max(2, cpu_count // 3))
        else:
            return min(2, max(1, cpu_count // 4))
    
    def get_memory_threshold(self) -> float:
        """Threshold conservador"""
        
        memory_gb = self.platform_info['memory_gb']
        
        # Conservador para plataformas desconhecidas
        if memory_gb < 4:
            return 0.50  # 50%
        elif memory_gb < 8:
            return 0.60  # 60%
        else:
            return 0.70  # 70%
    
    def get_batch_size(self) -> int:
        """Batch size conservador"""
        
        memory_gb = self.platform_info['memory_gb']
        
        # Batches pequenos para plataformas desconhecidas
        if memory_gb >= 16:
            return 6
        elif memory_gb >= 8:
            return 4
        else:
            return 3
    
    def configure_audio(self) -> Dict[str, Any]:
        """Configurações básicas de áudio"""
        
        return {
            'backend': 'default',
            'sample_rate': 24000,
            'channels': 1,
            'format': 'wav',
            'buffer_size': 2048,  # Buffer maior para compatibilidade
            'device': 'default',
            'fallback_mode': True
        } 