import os
import psutil
import gc
import logging
from typing import Dict, Any
from .base_platform import BasePlatform

logger = logging.getLogger(__name__)

class LinuxDockerPlatform(BasePlatform):
    """Otimizações específicas para Docker Linux"""
    
    def __init__(self):
        super().__init__()
        self.is_docker = self.platform_info['is_docker']
        self.container_limits = self._detect_container_limits()
        
    def optimize_pytorch(self):
        """Otimizações PyTorch para Docker Linux"""
        
        try:
            import torch
            
            # Configurar CUDA se disponível
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                
                # Configurações CUDA para containers
                os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:512'
                torch.backends.cudnn.benchmark = True
                torch.backends.cudnn.allow_tf32 = True
                
                gpu_count = torch.cuda.device_count()
                gpu_name = torch.cuda.get_device_name(0) if gpu_count > 0 else "Unknown"
                logger.info(f"🐳 PyTorch+CUDA: {gpu_count} GPUs ({gpu_name})")
                
            else:
                # CPU-only otimizado para containers
                available_cpus = self._get_container_cpu_limit()
                torch.set_num_threads(available_cpus)
                logger.info(f"🐳 PyTorch CPU-only: {available_cpus} threads")
            
            # Configurações gerais para containers
            torch.set_grad_enabled(False)  # Inferência apenas
            
            logger.info("✅ PyTorch otimizado para Docker Linux")
            
        except ImportError:
            logger.warning("PyTorch não instalado")
        except Exception as e:
            logger.error(f"Erro otimizando PyTorch: {e}")
    
    def cleanup_gpu_memory(self):
        """Cleanup específico para CUDA ou CPU"""
        
        try:
            import torch
            
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
                logger.debug("🧹 CUDA cache limpo")
            
            # Garbage collection normal
            gc.collect()
            
        except Exception as e:
            logger.debug(f"Erro no cleanup GPU: {e}")
            gc.collect()
    
    def get_optimal_workers(self) -> int:
        """Workers baseados em limites do container"""
        
        available_cpus = self._get_container_cpu_limit()
        memory_gb = self._get_container_memory_limit()
        
        try:
            import torch
            has_cuda = torch.cuda.is_available()
        except:
            has_cuda = False
        
        if has_cuda:
            # Com CUDA: pode usar mais workers pois GPU processa TTS
            if memory_gb >= 16:
                return min(6, max(2, available_cpus // 2))
            elif memory_gb >= 8:
                return min(4, max(2, available_cpus // 2))
            else:
                return min(3, max(1, available_cpus // 3))
        else:
            # CPU-only: workers baseados em CPU disponível
            if memory_gb >= 8:
                return min(8, max(2, available_cpus))
            elif memory_gb >= 4:
                return min(6, max(2, available_cpus // 2))
            else:
                return min(4, max(1, available_cpus // 3))
    
    def get_memory_threshold(self) -> float:
        """Threshold baseado em limites do container"""
        
        memory_gb = self._get_container_memory_limit()
        
        # Container: mais agressivo com memoria devido a limites
        if memory_gb < 2:  # Container muito pequeno
            return 0.50  # 50%
        elif memory_gb < 4:  # Container pequeno
            return 0.60  # 60%
        elif memory_gb < 8:  # Container médio
            return 0.70  # 70%
        elif memory_gb < 16:  # Container grande
            return 0.80  # 80%
        else:  # Container muito grande
            return 0.85  # 85%
    
    def get_batch_size(self) -> int:
        """Batch size baseado em recursos do container"""
        
        memory_gb = self._get_container_memory_limit()
        available_cpus = self._get_container_cpu_limit()
        
        try:
            import torch
            has_cuda = torch.cuda.is_available()
        except:
            has_cuda = False
        
        if has_cuda:
            # Com CUDA: batch size baseado em GPU memory
            if memory_gb >= 16:
                return 10
            elif memory_gb >= 8:
                return 8
            elif memory_gb >= 4:
                return 6
            else:
                return 4
        else:
            # CPU-only: batch size baseado em CPU e RAM
            if memory_gb >= 8 and available_cpus >= 8:
                return 12
            elif memory_gb >= 4 and available_cpus >= 4:
                return 8
            elif memory_gb >= 2:
                return 6
            else:
                return 4
    
    def configure_audio(self) -> Dict[str, Any]:
        """Configurações ALSA/PulseAudio para Linux"""
        
        return {
            'backend': 'alsa',
            'sample_rate': 24000,
            'channels': 1,
            'format': 'wav',
            'buffer_size': 1024,  # Maior buffer no container
            'device': 'default',
            'container_optimized': True,
            'platform_optimized': True
        }
    
    def _detect_container_limits(self) -> Dict[str, Any]:
        """Detecta limites específicos do container"""
        
        from .detector import PlatformDetector
        return PlatformDetector.get_container_limits()
    
    def _get_container_cpu_limit(self) -> int:
        """CPU limit do container ou sistema"""
        
        if self.container_limits.get('cpu_limit'):
            return self.container_limits['cpu_limit']
        else:
            return psutil.cpu_count()
    
    def _get_container_memory_limit(self) -> float:
        """Memory limit do container em GB"""
        
        if self.container_limits.get('memory_limit_gb'):
            return self.container_limits['memory_limit_gb']
        else:
            return psutil.virtual_memory().total / (1024**3)
    
    def get_tts_config(self) -> Dict[str, Any]:
        """Configurações específicas para TTS no Docker"""
        
        memory_gb = self._get_container_memory_limit()
        
        # Ajustar configurações baseado nos recursos do container
        if memory_gb >= 8:
            max_text_length = 250
        elif memory_gb >= 4:
            max_text_length = 200
        else:
            max_text_length = 150
        
        return {
            'max_text_length': max_text_length,
            'chunk_overlap': 5,
            'enable_cuda': True,
            'precision': 'float32',
            'memory_efficient': True,
            'container_optimized': True
        }
    
    def optimize_for_coqui_tts(self):
        """Otimizações específicas para CoquiTTS no Docker"""
        
        try:
            import torch
            
            if torch.cuda.is_available():
                # Configurações específicas para xTTS v2 no CUDA
                torch.cuda.empty_cache()
                
                # Configurar para uso eficiente em container
                os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:512'
                
                logger.info("🎤 CoquiTTS otimizado para CUDA")
            else:
                # CPU-only: otimizar threads
                cpu_limit = self._get_container_cpu_limit()
                torch.set_num_threads(cpu_limit)
                logger.info(f"🎤 CoquiTTS CPU-only ({cpu_limit} threads)")
                
        except Exception as e:
            logger.error(f"Erro otimizando CoquiTTS: {e}")
    
    def monitor_container_resources(self) -> Dict[str, Any]:
        """Monitora recursos específicos do container"""
        
        try:
            # Informações básicas
            memory = psutil.virtual_memory()
            
            status = {
                'container_limits': self.container_limits,
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': memory.percent,
                'memory_available_gb': memory.available / (1024**3),
                'memory_limit_gb': self._get_container_memory_limit(),
                'cpu_limit': self._get_container_cpu_limit(),
                'is_docker': self.is_docker
            }
            
            # Informações de GPU se CUDA disponível
            try:
                import torch
                if torch.cuda.is_available():
                    status['gpu_available'] = True
                    status['gpu_count'] = torch.cuda.device_count()
                    if torch.cuda.device_count() > 0:
                        status['gpu_memory_allocated'] = torch.cuda.memory_allocated() / (1024**3)
                        status['gpu_memory_reserved'] = torch.cuda.memory_reserved() / (1024**3)
                        status['gpu_name'] = torch.cuda.get_device_name(0)
                else:
                    status['gpu_available'] = False
            except:
                status['gpu_available'] = False
            
            # Calcular utilização vs limites
            if self.container_limits.get('memory_limit_gb'):
                used_gb = (memory.total - memory.available) / (1024**3)
                status['memory_utilization_percent'] = (used_gb / self.container_limits['memory_limit_gb']) * 100
            
            return status
            
        except Exception as e:
            logger.error(f"Erro monitorando container: {e}")
            return {'error': str(e)}
    
    def check_container_health(self) -> Dict[str, Any]:
        """Verifica saúde do container"""
        
        status = self.monitor_container_resources()
        health = {
            'healthy': True,
            'warnings': [],
            'errors': []
        }
        
        if 'error' in status:
            health['healthy'] = False
            health['errors'].append(f"Erro monitorando recursos: {status['error']}")
            return health
        
        # Verificar uso de memória
        if status.get('memory_utilization_percent', 0) > 90:
            health['errors'].append("Uso de memória crítico (>90%)")
            health['healthy'] = False
        elif status.get('memory_utilization_percent', 0) > 80:
            health['warnings'].append("Uso de memória alto (>80%)")
        
        # Verificar CPU
        if status.get('cpu_percent', 0) > 95:
            health['warnings'].append("Uso de CPU muito alto (>95%)")
        
        # Verificar disponibilidade de GPU se esperada
        if not status.get('gpu_available', False):
            health['warnings'].append("GPU não disponível (usando CPU-only)")
        
        return health
    
    def print_optimization_summary(self):
        """Imprime resumo das otimizações Docker"""
        
        print(f"\n🐳 OTIMIZAÇÕES DOCKER LINUX:")
        print(f"   • Container: {'Sim' if self.is_docker else 'Não'}")
        print(f"   • CPU Limit: {self._get_container_cpu_limit()} cores")
        print(f"   • Memory Limit: {self._get_container_memory_limit():.1f} GB")
        print(f"   • Workers: {self.get_optimal_workers()}")
        print(f"   • Batch Size: {self.get_batch_size()}")
        print(f"   • Memory Threshold: {self.get_memory_threshold():.1%}")
        
        try:
            import torch
            if torch.cuda.is_available():
                gpu_count = torch.cuda.device_count()
                gpu_name = torch.cuda.get_device_name(0) if gpu_count > 0 else "Unknown"
                print(f"   • GPU: {gpu_count}x {gpu_name} ✅")
            else:
                print(f"   • GPU: CPU-only")
        except:
            print(f"   • GPU: PyTorch não disponível")
        
        # Status atual
        status = self.monitor_container_resources()
        if 'error' not in status:
            print(f"   • CPU Atual: {status['cpu_percent']:.1f}%")
            print(f"   • Memory Atual: {status['memory_percent']:.1f}%")
            if status.get('gpu_available'):
                print(f"   • GPU Memory: {status.get('gpu_memory_allocated', 0):.1f} GB")
        
        print() 