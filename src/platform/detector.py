import platform
import os
import psutil
from typing import Dict, Any, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class PlatformType(Enum):
    MACOS_ARM64 = "macos_arm64"
    LINUX_X86_64 = "linux_x86_64"
    LINUX_ARM64 = "linux_arm64"
    WINDOWS_X86_64 = "windows_x86_64"
    UNKNOWN = "unknown"

class GPUBackend(Enum):
    MPS = "mps"          # Metal Performance Shaders (macOS)
    CUDA = "cuda"        # NVIDIA CUDA
    CPU = "cpu"          # CPU-only fallback

class PlatformDetector:
    """Detecção automática de plataforma e capabilities"""
    
    @staticmethod
    def detect_platform() -> PlatformType:
        """Detecta plataforma atual"""
        
        system = platform.system().lower()
        machine = platform.machine().lower()
        
        logger.debug(f"Detectando plataforma: {system} {machine}")
        
        if system == "darwin":
            if machine in ["arm64", "aarch64"] or "arm" in machine:
                return PlatformType.MACOS_ARM64
        elif system == "linux":
            if machine in ["x86_64", "amd64"]:
                return PlatformType.LINUX_X86_64
            elif machine in ["arm64", "aarch64"] or "arm" in machine:
                return PlatformType.LINUX_ARM64
        elif system == "windows":
            if machine in ["x86_64", "amd64"]:
                return PlatformType.WINDOWS_X86_64
        
        logger.warning(f"Plataforma não reconhecida: {system} {machine}")
        return PlatformType.UNKNOWN
    
    @staticmethod
    def detect_gpu_backend() -> GPUBackend:
        """Detecta backend GPU disponível"""
        
        try:
            import torch
            
            # Verificar MPS (Metal - macOS apenas)
            if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                logger.info("GPU backend detectado: Metal Performance Shaders (MPS)")
                return GPUBackend.MPS
            
            # Verificar CUDA
            elif torch.cuda.is_available():
                gpu_count = torch.cuda.device_count()
                gpu_name = torch.cuda.get_device_name(0) if gpu_count > 0 else "Unknown"
                logger.info(f"GPU backend detectado: CUDA ({gpu_count} GPUs: {gpu_name})")
                return GPUBackend.CUDA
            
            # Fallback CPU
            else:
                logger.info("GPU backend: CPU-only (sem aceleração GPU)")
                return GPUBackend.CPU
                
        except ImportError:
            logger.warning("PyTorch não disponível, usando CPU-only")
            return GPUBackend.CPU
        except Exception as e:
            logger.error(f"Erro detectando GPU: {e}")
            return GPUBackend.CPU
    
    @staticmethod
    def get_platform_info() -> Dict[str, Any]:
        """Informações completas da plataforma"""
        
        platform_type = PlatformDetector.detect_platform()
        gpu_backend = PlatformDetector.detect_gpu_backend()
        
        info = {
            'platform_type': platform_type,
            'gpu_backend': gpu_backend,
            'system': platform.system(),
            'machine': platform.machine(),
            'python_version': platform.python_version(),
            'cpu_count': psutil.cpu_count(),
            'memory_gb': round(psutil.virtual_memory().total / (1024**3), 1),
            'is_docker': PlatformDetector.is_docker_environment(),
        }
        
        # Adicionar PyTorch info se disponível
        try:
            import torch
            info['pytorch_version'] = torch.__version__
            
            # Informações específicas de GPU
            if gpu_backend == GPUBackend.MPS:
                info['gpu_info'] = {
                    'type': 'Metal Performance Shaders',
                    'unified_memory': True
                }
            elif gpu_backend == GPUBackend.CUDA:
                if torch.cuda.device_count() > 0:
                    info['gpu_info'] = {
                        'type': 'NVIDIA CUDA',
                        'device_count': torch.cuda.device_count(),
                        'device_name': torch.cuda.get_device_name(0),
                        'memory_gb': round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 1),
                        'unified_memory': False
                    }
                else:
                    info['gpu_info'] = {'type': 'CUDA available but no devices'}
            else:
                info['gpu_info'] = {'type': 'CPU-only', 'unified_memory': False}
                
        except ImportError:
            info['pytorch_version'] = 'Not installed'
            info['gpu_info'] = {'type': 'PyTorch not available'}
        
        return info
    
    @staticmethod
    def is_docker_environment() -> bool:
        """Detecta se está rodando em Docker"""
        return (
            os.path.exists('/.dockerenv') or 
            os.path.exists('/proc/1/cgroup') and 
            any('docker' in line for line in open('/proc/1/cgroup', 'r').readlines())
        )
    
    @staticmethod
    def get_container_limits() -> Dict[str, Any]:
        """Detecta limites de CPU e memória do container"""
        
        limits = {
            'cpu_limit': None,
            'memory_limit_gb': None,
            'is_limited': False
        }
        
        if not PlatformDetector.is_docker_environment():
            return limits
        
        try:
            # CPU limits (cgroup v1)
            try:
                with open('/sys/fs/cgroup/cpu/cpu.cfs_quota_us', 'r') as f:
                    quota = int(f.read().strip())
                
                with open('/sys/fs/cgroup/cpu/cpu.cfs_period_us', 'r') as f:
                    period = int(f.read().strip())
                
                if quota > 0:
                    limits['cpu_limit'] = max(1, quota // period)
                    limits['is_limited'] = True
            except:
                pass
            
            # Memory limits (cgroup v1)
            try:
                with open('/sys/fs/cgroup/memory/memory.limit_in_bytes', 'r') as f:
                    limit_bytes = int(f.read().strip())
                
                # Se limit é muito alto, não é um limite real
                physical_memory = psutil.virtual_memory().total
                if limit_bytes < physical_memory:
                    limits['memory_limit_gb'] = round(limit_bytes / (1024**3), 1)
                    limits['is_limited'] = True
            except:
                pass
                
        except Exception as e:
            logger.debug(f"Erro detectando limites do container: {e}")
        
        return limits
    
    @staticmethod
    def print_platform_summary():
        """Imprime resumo da plataforma detectada"""
        
        info = PlatformDetector.get_platform_info()
        
        print(f"\n🔍 DETECÇÃO DE PLATAFORMA:")
        print(f"   • Sistema: {info['system']} {info['machine']}")
        print(f"   • Tipo: {info['platform_type'].value}")
        print(f"   • CPU: {info['cpu_count']} cores")
        print(f"   • RAM: {info['memory_gb']} GB")
        print(f"   • Docker: {'Sim' if info['is_docker'] else 'Não'}")
        print(f"   • GPU: {info['gpu_backend'].value.upper()}")
        print(f"   • PyTorch: {info['pytorch_version']}")
        
        if info['gpu_info']['type'] != 'CPU-only':
            gpu_info = info['gpu_info']
            print(f"   • GPU Info: {gpu_info['type']}")
            if 'device_name' in gpu_info:
                print(f"     - Device: {gpu_info['device_name']}")
                print(f"     - VRAM: {gpu_info['memory_gb']} GB")
        
        if info['is_docker']:
            limits = PlatformDetector.get_container_limits()
            if limits['is_limited']:
                print(f"   • Container Limits:")
                if limits['cpu_limit']:
                    print(f"     - CPU: {limits['cpu_limit']} cores")
                if limits['memory_limit_gb']:
                    print(f"     - RAM: {limits['memory_limit_gb']} GB")
        
        print() 