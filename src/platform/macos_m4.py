import os
import psutil
import gc
import logging
from typing import Dict, Any
from .base_platform import BasePlatform

logger = logging.getLogger(__name__)

class MacOSM4Platform(BasePlatform):
    """Otimizações específicas para MacBook Pro M4 (Apple Silicon)"""
    
    def __init__(self):
        super().__init__()
        self.unified_memory = True
        self.efficiency_cores = True
        
    def optimize_pytorch(self):
        """Otimizações PyTorch para Apple Silicon + MPS"""
        
        try:
            import torch
            
            # Configurar MPS se disponível
            if torch.backends.mps.is_available():
                torch.mps.empty_cache()
                
                # Configurações específicas para Metal
                os.environ['PYTORCH_MPS_HIGH_WATERMARK_RATIO'] = '0.0'
                logger.info("🍎 MPS configurado com low watermark")
            else:
                logger.warning("🍎 MPS não disponível, usando CPU")
            
            # Otimizações para ARM64 - menos threads para efficiency cores
            optimal_threads = min(8, max(4, psutil.cpu_count() // 2))
            torch.set_num_threads(optimal_threads)
            logger.info(f"🍎 Threads PyTorch: {optimal_threads} (otimizado para ARM64)")
            
            # Memory management para memória unificada
            torch.backends.cudnn.benchmark = False  # MPS não usa cuDNN
            
            # Configurações específicas para Apple Silicon
            if hasattr(torch.backends, 'mps'):
                # Tentar otimizações específicas de MPS
                try:
                    # Configurar para uso eficiente de memória
                    os.environ['PYTORCH_MPS_PREFER_METAL'] = '1'
                except:
                    pass
            
            logger.info("✅ PyTorch otimizado para Apple Silicon M4")
            
        except ImportError:
            logger.warning("PyTorch não instalado")
        except Exception as e:
            logger.error(f"Erro otimizando PyTorch: {e}")
    
    def cleanup_gpu_memory(self):
        """Cleanup específico para MPS"""
        
        try:
            import torch
            
            if torch.backends.mps.is_available():
                torch.mps.empty_cache()
                torch.mps.synchronize()
                logger.debug("🧹 MPS cache limpo")
            
            # Garbage collection agressivo para memória unificada
            gc.collect()
            
        except Exception as e:
            logger.debug(f"Erro no cleanup MPS: {e}")
            # Fallback para garbage collection básico
            gc.collect()
    
    def get_optimal_workers(self) -> int:
        """Workers otimizados para Apple Silicon"""
        
        cpu_count = psutil.cpu_count()
        memory_gb = self.platform_info['memory_gb']
        
        try:
            import torch
            has_mps = torch.backends.mps.is_available()
        except:
            has_mps = False
        
        if has_mps:
            # Com MPS: menos workers devido a GPU compartilhada e memória unificada
            if memory_gb >= 64:  # M4 Max
                return min(4, max(2, cpu_count // 3))
            elif memory_gb >= 32:  # M4 Pro
                return min(3, max(2, cpu_count // 4))
            else:  # M4 base
                return min(2, max(1, cpu_count // 4))
        else:
            # CPU-only: mais workers para compensar
            if memory_gb >= 32:
                return min(6, max(2, cpu_count // 2))
            else:
                return min(4, max(2, cpu_count // 3))
    
    def get_memory_threshold(self) -> float:
        """Threshold para memória unificada"""
        
        memory_gb = self.platform_info['memory_gb']
        
        # Memória unificada: mais conservador pois GPU e CPU compartilham
        if memory_gb < 16:  # M4 base
            return 0.60  # 60%
        elif memory_gb < 32:  # M4 Pro
            return 0.70  # 70%
        elif memory_gb < 64:  # M4 Pro high-end
            return 0.75  # 75%
        else:  # M4 Max
            return 0.80  # 80%
    
    def get_batch_size(self) -> int:
        """Batch size otimizado para memória unificada"""
        
        memory_gb = self.platform_info['memory_gb']
        
        try:
            import torch
            has_mps = torch.backends.mps.is_available()
        except:
            has_mps = False
        
        if has_mps:
            # Com MPS: batches menores devido a compartilhamento de memória
            if memory_gb >= 64:  # M4 Max
                return 8
            elif memory_gb >= 32:  # M4 Pro
                return 6
            else:  # M4 base
                return 4
        else:
            # CPU-only: pode usar batches maiores
            if memory_gb >= 32:
                return 10
            else:
                return 7
    
    def configure_audio(self) -> Dict[str, Any]:
        """Configurações Core Audio para macOS"""
        
        return {
            'backend': 'coreaudio',
            'sample_rate': 24000,
            'channels': 1,
            'format': 'wav',
            'buffer_size': 512,  # Menor latência no macOS
            'device': 'default',
            'unified_memory': True,
            'platform_optimized': True
        }
    
    def get_tts_config(self) -> Dict[str, Any]:
        """Configurações específicas para TTS no Apple Silicon"""
        
        return {
            'max_text_length': 200,  # Mais conservador para MPS
            'chunk_overlap': 10,
            'enable_mps': True,
            'precision': 'float32',  # MPS ainda tem limitações com float16
            'memory_efficient': True,
            'use_unified_memory': True
        }
    
    def optimize_for_coqui_tts(self):
        """Otimizações específicas para CoquiTTS no Apple Silicon"""
        
        try:
            import torch
            
            if torch.backends.mps.is_available():
                # Configurações específicas para xTTS v2 no MPS
                os.environ['PYTORCH_MPS_HIGH_WATERMARK_RATIO'] = '0.0'
                
                # Forçar sincronização após cada operação para evitar memory leaks
                torch.mps.empty_cache()
                
                logger.info("🎤 CoquiTTS otimizado para MPS")
            else:
                logger.info("🎤 CoquiTTS usando CPU (MPS não disponível)")
                
        except Exception as e:
            logger.error(f"Erro otimizando CoquiTTS: {e}")
    
    def monitor_unified_memory(self) -> Dict[str, float]:
        """Monitora uso de memória unificada"""
        
        try:
            memory = psutil.virtual_memory()
            
            status = {
                'total_gb': memory.total / (1024**3),
                'available_gb': memory.available / (1024**3),
                'used_percent': memory.percent,
                'unified_memory': True
            }
            
            # Tentar obter informações específicas do GPU se MPS disponível
            try:
                import torch
                if torch.backends.mps.is_available():
                    # MPS não tem APIs diretas de memória, estimar baseado em uso total
                    status['estimated_gpu_usage_gb'] = (memory.used * 0.3) / (1024**3)  # Estimativa
                    status['mps_available'] = True
                else:
                    status['mps_available'] = False
            except:
                status['mps_available'] = False
            
            return status
            
        except Exception as e:
            logger.error(f"Erro monitorando memória: {e}")
            return {'error': str(e)}
    
    def print_optimization_summary(self):
        """Imprime resumo das otimizações Apple Silicon"""
        
        print(f"\n🍎 OTIMIZAÇÕES APPLE SILICON M4:")
        print(f"   • Memória Unificada: {self.platform_info['memory_gb']} GB")
        print(f"   • Workers Otimizados: {self.get_optimal_workers()}")
        print(f"   • Batch Size: {self.get_batch_size()}")
        print(f"   • Memory Threshold: {self.get_memory_threshold():.1%}")
        
        try:
            import torch
            if torch.backends.mps.is_available():
                print(f"   • GPU: Metal Performance Shaders ✅")
            else:
                print(f"   • GPU: CPU-only (MPS não disponível)")
        except:
            print(f"   • GPU: PyTorch não disponível")
        
        memory_status = self.monitor_unified_memory()
        if 'error' not in memory_status:
            print(f"   • Memória Disponível: {memory_status['available_gb']:.1f} GB")
            print(f"   • Uso Atual: {memory_status['used_percent']:.1f}%")
        
        print() 