import time
import psutil
import gc
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import threading
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Métricas de performance para um período"""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    segments_completed: int
    time_per_segment: float
    gpu_memory_gb: Optional[float] = None

class PerformanceMonitor:
    """Monitor de performance em tempo real com ETA e estatísticas"""
    
    def __init__(self, platform_adapter=None):
        self.platform = platform_adapter
        self.start_time = None
        self.total_segments = 0
        self.completed_segments = 0
        self.segment_times = []
        self.metrics_history = []
        self.monitoring_thread = None
        self._stop_monitoring = False
        
    def start_monitoring(self, total_segments: int):
        """Inicia monitoramento de performance"""
        
        self.start_time = time.time()
        self.total_segments = total_segments
        self.completed_segments = 0
        self.segment_times = []
        self.metrics_history = []
        self._stop_monitoring = False
        
        logger.info(f"📊 Iniciando monitoramento de performance para {total_segments} segmentos")
        
        # Iniciar thread de monitoramento contínuo
        self.monitoring_thread = threading.Thread(target=self._continuous_monitoring, daemon=True)
        self.monitoring_thread.start()
    
    def update_progress(self, current_segment: int, segment_duration: float = None):
        """Atualiza progresso e calcula ETA"""
        
        self.completed_segments = current_segment
        
        if segment_duration is not None:
            self.segment_times.append(segment_duration)
        
        # Capturar métricas atuais
        metrics = self._capture_metrics()
        self.metrics_history.append(metrics)
        
        # Calcular ETA
        eta_info = self._calculate_eta()
        
        # Log progress com informações detalhadas
        self._log_progress(eta_info, metrics)
        
        # Verificar se precisa de cleanup
        if self.platform and self.platform.should_cleanup_memory():
            logger.debug("🧹 Fazendo cleanup de memória baseado no threshold")
            self.platform.cleanup_gpu_memory()
    
    def stop_monitoring(self):
        """Para monitoramento e gera relatório final"""
        
        self._stop_monitoring = True
        
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=1.0)
        
        self._generate_final_report()
    
    def _continuous_monitoring(self):
        """Thread de monitoramento contínuo (a cada 30s)"""
        
        while not self._stop_monitoring:
            try:
                time.sleep(30)  # Monitor a cada 30 segundos
                
                if not self._stop_monitoring:
                    metrics = self._capture_metrics()
                    self.metrics_history.append(metrics)
                    
                    # Log periódico se processo está longo
                    if self._get_elapsed_time() > 300:  # > 5 minutos
                        self._log_periodic_status()
                        
            except Exception as e:
                logger.debug(f"Erro no monitoramento contínuo: {e}")
                break
    
    def _capture_metrics(self) -> PerformanceMetrics:
        """Captura métricas atuais do sistema"""
        
        try:
            memory = psutil.virtual_memory()
            
            metrics = PerformanceMetrics(
                timestamp=time.time(),
                cpu_percent=psutil.cpu_percent(interval=0.1),
                memory_percent=memory.percent,
                memory_used_gb=(memory.total - memory.available) / (1024**3),
                segments_completed=self.completed_segments,
                time_per_segment=self._get_average_segment_time()
            )
            
            # Adicionar métricas de GPU se disponível
            if self.platform:
                try:
                    status = self.platform.get_system_status()
                    if status.get('gpu_memory_allocated'):
                        metrics.gpu_memory_gb = status['gpu_memory_allocated']
                except:
                    pass
            
            return metrics
            
        except Exception as e:
            logger.debug(f"Erro capturando métricas: {e}")
            return PerformanceMetrics(
                timestamp=time.time(),
                cpu_percent=0,
                memory_percent=0,
                memory_used_gb=0,
                segments_completed=self.completed_segments,
                time_per_segment=0
            )
    
    def _calculate_eta(self) -> Dict[str, Any]:
        """Calcula ETA baseado em múltiplos métodos"""
        
        elapsed = self._get_elapsed_time()
        remaining_segments = self.total_segments - self.completed_segments
        
        eta_info = {
            'elapsed_time': elapsed,
            'remaining_segments': remaining_segments,
            'completion_percent': (self.completed_segments / self.total_segments) * 100 if self.total_segments > 0 else 0,
            'eta_seconds': 0,
            'eta_method': 'insufficient_data'
        }
        
        if self.completed_segments > 0:
            # Método 1: ETA baseado em tempo médio por segmento
            if self.segment_times and len(self.segment_times) >= 3:
                # Usar média dos últimos 5 segmentos para mais precisão
                recent_times = self.segment_times[-5:]
                avg_time = sum(recent_times) / len(recent_times)
                eta_info['eta_seconds'] = remaining_segments * avg_time
                eta_info['eta_method'] = 'segment_average'
            
            # Método 2: ETA baseado em progresso linear
            else:
                rate = self.completed_segments / elapsed
                if rate > 0:
                    eta_info['eta_seconds'] = remaining_segments / rate
                    eta_info['eta_method'] = 'linear_progress'
        
        return eta_info
    
    def _log_progress(self, eta_info: Dict[str, Any], metrics: PerformanceMetrics):
        """Log detalhado do progresso"""
        
        # Formatar tempo
        elapsed_str = self._format_duration(eta_info['elapsed_time'])
        eta_str = self._format_duration(eta_info['eta_seconds'])
        
        # Progress básico
        progress_msg = f"🔄 {self.completed_segments}/{self.total_segments} ({eta_info['completion_percent']:.1f}%)"
        
        # Informações de tempo
        time_msg = f"⏱️  Elapsed: {elapsed_str}"
        if eta_info['eta_seconds'] > 0:
            time_msg += f" | ETA: {eta_str}"
        
        # Informações de sistema
        system_msg = f"💻 CPU: {metrics.cpu_percent:.1f}% | RAM: {metrics.memory_percent:.1f}% ({metrics.memory_used_gb:.1f}GB)"
        
        if metrics.gpu_memory_gb:
            system_msg += f" | GPU: {metrics.gpu_memory_gb:.1f}GB"
        
        # Log tudo
        logger.info(progress_msg)
        logger.info(time_msg)
        logger.info(system_msg)
    
    def _log_periodic_status(self):
        """Log periódico para processos longos"""
        
        if not self.metrics_history:
            return
        
        # Calcular tendências
        recent_metrics = self.metrics_history[-3:] if len(self.metrics_history) >= 3 else self.metrics_history
        
        avg_cpu = sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m.memory_percent for m in recent_metrics) / len(recent_metrics)
        
        logger.info(f"📈 STATUS PERIÓDICO:")
        logger.info(f"   • CPU médio: {avg_cpu:.1f}%")
        logger.info(f"   • Memory médio: {avg_memory:.1f}%")
        logger.info(f"   • Segmentos/min: {self._get_segments_per_minute():.1f}")
        
        # Alertas se necessário
        if avg_memory > 85:
            logger.warning("⚠️  Uso de memória alto - considere cleanup")
        if avg_cpu > 90:
            logger.warning("⚠️  Uso de CPU muito alto")
    
    def _generate_final_report(self):
        """Gera relatório final de performance"""
        
        total_time = self._get_elapsed_time()
        
        logger.info("\n📊 RELATÓRIO FINAL DE PERFORMANCE:")
        logger.info(f"   • Total de segmentos: {self.total_segments}")
        logger.info(f"   • Segmentos processados: {self.completed_segments}")
        logger.info(f"   • Tempo total: {self._format_duration(total_time)}")
        
        if self.segment_times:
            avg_segment_time = sum(self.segment_times) / len(self.segment_times)
            logger.info(f"   • Tempo médio por segmento: {avg_segment_time:.2f}s")
            logger.info(f"   • Segmentos por minuto: {self._get_segments_per_minute():.1f}")
        
        if self.metrics_history:
            metrics = self.metrics_history[-1]  # Última métrica
            logger.info(f"   • CPU final: {metrics.cpu_percent:.1f}%")
            logger.info(f"   • Memory final: {metrics.memory_percent:.1f}%")
            if metrics.gpu_memory_gb:
                logger.info(f"   • GPU Memory final: {metrics.gpu_memory_gb:.1f}GB")
        
        # Estatísticas de performance
        if len(self.metrics_history) > 1:
            cpu_values = [m.cpu_percent for m in self.metrics_history]
            memory_values = [m.memory_percent for m in self.metrics_history]
            
            logger.info(f"   • CPU pico: {max(cpu_values):.1f}%")
            logger.info(f"   • Memory pico: {max(memory_values):.1f}%")
    
    def _get_elapsed_time(self) -> float:
        """Tempo decorrido desde o início"""
        if self.start_time:
            return time.time() - self.start_time
        return 0
    
    def _get_average_segment_time(self) -> float:
        """Tempo médio por segmento"""
        if self.segment_times:
            return sum(self.segment_times) / len(self.segment_times)
        return 0
    
    def _get_segments_per_minute(self) -> float:
        """Segmentos processados por minuto"""
        elapsed_minutes = self._get_elapsed_time() / 60
        if elapsed_minutes > 0:
            return self.completed_segments / elapsed_minutes
        return 0
    
    def _format_duration(self, seconds: float) -> str:
        """Formata duração em formato legível"""
        
        if seconds <= 0:
            return "0s"
        
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours}h{minutes:02d}m{secs:02d}s"
        elif minutes > 0:
            return f"{minutes}m{secs:02d}s"
        else:
            return f"{secs}s"
    
    def get_current_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas atuais"""
        
        eta_info = self._calculate_eta()
        metrics = self._capture_metrics() if not self.metrics_history else self.metrics_history[-1]
        
        return {
            'total_segments': self.total_segments,
            'completed_segments': self.completed_segments,
            'completion_percent': eta_info['completion_percent'],
            'elapsed_time': self._get_elapsed_time(),
            'eta_seconds': eta_info['eta_seconds'],
            'average_segment_time': self._get_average_segment_time(),
            'segments_per_minute': self._get_segments_per_minute(),
            'current_cpu_percent': metrics.cpu_percent,
            'current_memory_percent': metrics.memory_percent,
            'current_memory_gb': metrics.memory_used_gb
        } 