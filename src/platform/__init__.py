from .detector import PlatformDetector, PlatformType, GPUBackend
from .base_platform import BasePlatform
from .macos_m4 import MacOSM4Platform
from .linux_docker import LinuxDockerPlatform
from .cpu_fallback import CPUFallbackPlatform

class PlatformFactory:
    """Factory para criar instância de plataforma adequada"""
    
    @staticmethod
    def create_platform() -> BasePlatform:
        """Cria plataforma baseada na detecção automática"""
        
        platform_type = PlatformDetector.detect_platform()
        
        if platform_type == PlatformType.MACOS_ARM64:
            return MacOSM4Platform()
        elif platform_type in [PlatformType.LINUX_X86_64, PlatformType.LINUX_ARM64]:
            return LinuxDockerPlatform()
        else:
            # Fallback universal
            return CPUFallbackPlatform()
    
    @staticmethod
    def get_platform_info():
        """Informações da plataforma atual"""
        return PlatformDetector.get_platform_info()

# Instância global da plataforma atual
current_platform = PlatformFactory.create_platform()

__all__ = [
    'PlatformDetector', 'PlatformType', 'GPUBackend',
    'BasePlatform', 'PlatformFactory', 'current_platform'
] 