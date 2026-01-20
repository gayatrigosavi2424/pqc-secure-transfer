"""
Custom metrics collection system for PQC Secure Transfer.
Provides Prometheus-compatible metrics for PQC operations, file transfers, and system health.
"""

import time
import threading
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from prometheus_client import Counter, Histogram, Gauge, Info, start_http_server
import psutil
import logging

logger = logging.getLogger(__name__)


@dataclass
class MetricLabels:
    """Standard labels for metrics."""
    environment: str = "dev"
    service: str = "pqc-secure-transfer"
    version: str = "1.0.0"
    algorithm: str = "Kyber768"
    
    def to_dict(self) -> Dict[str, str]:
        return {
            "environment": self.environment,
            "service": self.service,
            "version": self.version,
            "algorithm": self.algorithm
        }


class PQCMetrics:
    """PQC-specific metrics collector."""
    
    def __init__(self, labels: MetricLabels):
        self.labels = labels.to_dict()
        
        # PQC Key Exchange Metrics
        self.pqc_key_exchanges_total = Counter(
            'pqc_key_exchanges_total',
            'Total number of PQC key exchanges performed',
            ['algorithm', 'status', 'environment']
        )
        
        self.pqc_key_exchange_duration = Histogram(
            'pqc_key_exchange_duration_seconds',
            'Time taken for PQC key exchange operations',
            ['algorithm', 'operation', 'environment'],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
        )
        
        self.pqc_key_generation_duration = Histogram(
            'pqc_key_generation_duration_seconds',
            'Time taken for PQC key generation',
            ['algorithm', 'environment'],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
        )
        
        self.pqc_encapsulation_duration = Histogram(
            'pqc_encapsulation_duration_seconds',
            'Time taken for PQC encapsulation',
            ['algorithm', 'environment'],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5]
        )
        
        self.pqc_decapsulation_duration = Histogram(
            'pqc_decapsulation_duration_seconds',
            'Time taken for PQC decapsulation',
            ['algorithm', 'environment'],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5]
        )
        
        # PQC Key Management
        self.pqc_active_keys = Gauge(
            'pqc_active_keys',
            'Number of active PQC keys in memory',
            ['algorithm', 'key_type', 'environment']
        )
        
        self.pqc_key_rotations_total = Counter(
            'pqc_key_rotations_total',
            'Total number of key rotations performed',
            ['algorithm', 'rotation_type', 'environment']
        )
        
        # PQC Security Events
        self.pqc_security_events_total = Counter(
            'pqc_security_events_total',
            'Total number of PQC security events',
            ['event_type', 'severity', 'environment']
        )
    
    def record_key_exchange(self, algorithm: str, status: str, duration: float):
        """Record a PQC key exchange operation."""
        self.pqc_key_exchanges_total.labels(
            algorithm=algorithm,
            status=status,
            environment=self.labels['environment']
        ).inc()
        
        self.pqc_key_exchange_duration.labels(
            algorithm=algorithm,
            operation='full_exchange',
            environment=self.labels['environment']
        ).observe(duration)
    
    def record_key_generation(self, algorithm: str, duration: float):
        """Record PQC key generation timing."""
        self.pqc_key_generation_duration.labels(
            algorithm=algorithm,
            environment=self.labels['environment']
        ).observe(duration)
    
    def record_encapsulation(self, algorithm: str, duration: float):
        """Record PQC encapsulation timing."""
        self.pqc_encapsulation_duration.labels(
            algorithm=algorithm,
            environment=self.labels['environment']
        ).observe(duration)
    
    def record_decapsulation(self, algorithm: str, duration: float):
        """Record PQC decapsulation timing."""
        self.pqc_decapsulation_duration.labels(
            algorithm=algorithm,
            environment=self.labels['environment']
        ).observe(duration)
    
    def set_active_keys(self, algorithm: str, key_type: str, count: int):
        """Set the number of active keys."""
        self.pqc_active_keys.labels(
            algorithm=algorithm,
            key_type=key_type,
            environment=self.labels['environment']
        ).set(count)
    
    def record_key_rotation(self, algorithm: str, rotation_type: str):
        """Record a key rotation event."""
        self.pqc_key_rotations_total.labels(
            algorithm=algorithm,
            rotation_type=rotation_type,
            environment=self.labels['environment']
        ).inc()
    
    def record_security_event(self, event_type: str, severity: str):
        """Record a security event."""
        self.pqc_security_events_total.labels(
            event_type=event_type,
            severity=severity,
            environment=self.labels['environment']
        ).inc()


class FileTransferMetrics:
    """File transfer metrics collector."""
    
    def __init__(self, labels: MetricLabels):
        self.labels = labels.to_dict()
        
        # File Transfer Metrics
        self.file_transfers_total = Counter(
            'file_transfers_total',
            'Total number of file transfers',
            ['status', 'transfer_type', 'environment']
        )
        
        self.file_transfer_size_bytes = Histogram(
            'file_transfer_size_bytes',
            'Size of file transfers in bytes',
            ['transfer_type', 'environment'],
            buckets=[1024, 10240, 102400, 1048576, 10485760, 104857600, 1073741824, 10737418240, 107374182400]  # 1KB to 100GB
        )
        
        self.file_transfer_duration_seconds = Histogram(
            'file_transfer_duration_seconds',
            'Duration of file transfers in seconds',
            ['transfer_type', 'environment'],
            buckets=[1, 5, 10, 30, 60, 300, 600, 1800, 3600, 7200]  # 1s to 2h
        )
        
        self.file_transfer_throughput_mbps = Histogram(
            'file_transfer_throughput_mbps',
            'File transfer throughput in MB/s',
            ['transfer_type', 'environment'],
            buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000, 2000]
        )
        
        # Active Transfer Tracking
        self.active_transfers = Gauge(
            'active_transfers',
            'Number of active file transfers',
            ['transfer_type', 'environment']
        )
        
        self.transfer_queue_length = Gauge(
            'transfer_queue_length',
            'Number of transfers waiting in queue',
            ['priority', 'environment']
        )
        
        # Encryption Metrics
        self.encryption_throughput_mbps = Gauge(
            'encryption_throughput_mbps',
            'Current encryption throughput in MB/s',
            ['algorithm', 'environment']
        )
        
        self.decryption_throughput_mbps = Gauge(
            'decryption_throughput_mbps',
            'Current decryption throughput in MB/s',
            ['algorithm', 'environment']
        )
    
    def record_transfer_start(self, transfer_type: str):
        """Record the start of a file transfer."""
        self.active_transfers.labels(
            transfer_type=transfer_type,
            environment=self.labels['environment']
        ).inc()
    
    def record_transfer_complete(self, transfer_type: str, status: str, 
                               size_bytes: int, duration_seconds: float):
        """Record the completion of a file transfer."""
        self.active_transfers.labels(
            transfer_type=transfer_type,
            environment=self.labels['environment']
        ).dec()
        
        self.file_transfers_total.labels(
            status=status,
            transfer_type=transfer_type,
            environment=self.labels['environment']
        ).inc()
        
        self.file_transfer_size_bytes.labels(
            transfer_type=transfer_type,
            environment=self.labels['environment']
        ).observe(size_bytes)
        
        self.file_transfer_duration_seconds.labels(
            transfer_type=transfer_type,
            environment=self.labels['environment']
        ).observe(duration_seconds)
        
        # Calculate and record throughput
        if duration_seconds > 0:
            throughput_mbps = (size_bytes / (1024 * 1024)) / duration_seconds
            self.file_transfer_throughput_mbps.labels(
                transfer_type=transfer_type,
                environment=self.labels['environment']
            ).observe(throughput_mbps)
    
    def set_queue_length(self, priority: str, length: int):
        """Set the current queue length."""
        self.transfer_queue_length.labels(
            priority=priority,
            environment=self.labels['environment']
        ).set(length)
    
    def set_encryption_throughput(self, algorithm: str, throughput_mbps: float):
        """Set current encryption throughput."""
        self.encryption_throughput_mbps.labels(
            algorithm=algorithm,
            environment=self.labels['environment']
        ).set(throughput_mbps)
    
    def set_decryption_throughput(self, algorithm: str, throughput_mbps: float):
        """Set current decryption throughput."""
        self.decryption_throughput_mbps.labels(
            algorithm=algorithm,
            environment=self.labels['environment']
        ).set(throughput_mbps)


class SystemHealthMetrics:
    """System health and resource metrics collector."""
    
    def __init__(self, labels: MetricLabels):
        self.labels = labels.to_dict()
        
        # System Resource Metrics
        self.cpu_usage_percent = Gauge(
            'cpu_usage_percent',
            'CPU usage percentage',
            ['cpu', 'environment']
        )
        
        self.memory_usage_bytes = Gauge(
            'memory_usage_bytes',
            'Memory usage in bytes',
            ['type', 'environment']
        )
        
        self.disk_usage_bytes = Gauge(
            'disk_usage_bytes',
            'Disk usage in bytes',
            ['device', 'type', 'environment']
        )
        
        self.network_bytes_total = Counter(
            'network_bytes_total',
            'Total network bytes transferred',
            ['interface', 'direction', 'environment']
        )
        
        # Application Health
        self.service_uptime_seconds = Gauge(
            'service_uptime_seconds',
            'Service uptime in seconds',
            ['service', 'environment']
        )
        
        self.health_check_status = Gauge(
            'health_check_status',
            'Health check status (1=healthy, 0=unhealthy)',
            ['check_name', 'environment']
        )
        
        self.error_rate_percent = Gauge(
            'error_rate_percent',
            'Error rate percentage',
            ['service', 'environment']
        )
        
        # Connection Metrics
        self.active_connections = Gauge(
            'active_connections',
            'Number of active connections',
            ['type', 'environment']
        )
        
        self.connection_pool_size = Gauge(
            'connection_pool_size',
            'Connection pool size',
            ['pool_name', 'status', 'environment']
        )
        
        self._start_time = time.time()
        self._last_network_stats = {}
    
    def update_system_metrics(self):
        """Update system resource metrics."""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1, percpu=True)
            for i, cpu_usage in enumerate(cpu_percent):
                self.cpu_usage_percent.labels(
                    cpu=f"cpu{i}",
                    environment=self.labels['environment']
                ).set(cpu_usage)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            self.memory_usage_bytes.labels(
                type='used',
                environment=self.labels['environment']
            ).set(memory.used)
            
            self.memory_usage_bytes.labels(
                type='available',
                environment=self.labels['environment']
            ).set(memory.available)
            
            self.memory_usage_bytes.labels(
                type='total',
                environment=self.labels['environment']
            ).set(memory.total)
            
            # Disk metrics
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    device = partition.device.replace('/', '_').replace('\\', '_')
                    
                    self.disk_usage_bytes.labels(
                        device=device,
                        type='used',
                        environment=self.labels['environment']
                    ).set(usage.used)
                    
                    self.disk_usage_bytes.labels(
                        device=device,
                        type='free',
                        environment=self.labels['environment']
                    ).set(usage.free)
                    
                    self.disk_usage_bytes.labels(
                        device=device,
                        type='total',
                        environment=self.labels['environment']
                    ).set(usage.total)
                except (PermissionError, OSError):
                    continue
            
            # Network metrics
            network_stats = psutil.net_io_counters(pernic=True)
            for interface, stats in network_stats.items():
                if interface in self._last_network_stats:
                    last_stats = self._last_network_stats[interface]
                    
                    bytes_sent_delta = stats.bytes_sent - last_stats.bytes_sent
                    bytes_recv_delta = stats.bytes_recv - last_stats.bytes_recv
                    
                    self.network_bytes_total.labels(
                        interface=interface,
                        direction='sent',
                        environment=self.labels['environment']
                    )._value._value = stats.bytes_sent
                    
                    self.network_bytes_total.labels(
                        interface=interface,
                        direction='received',
                        environment=self.labels['environment']
                    )._value._value = stats.bytes_recv
                
                self._last_network_stats[interface] = stats
            
            # Service uptime
            uptime = time.time() - self._start_time
            self.service_uptime_seconds.labels(
                service=self.labels['service'],
                environment=self.labels['environment']
            ).set(uptime)
            
        except Exception as e:
            logger.error(f"Error updating system metrics: {e}")
    
    def set_health_check_status(self, check_name: str, is_healthy: bool):
        """Set health check status."""
        self.health_check_status.labels(
            check_name=check_name,
            environment=self.labels['environment']
        ).set(1 if is_healthy else 0)
    
    def set_error_rate(self, service: str, error_rate: float):
        """Set error rate percentage."""
        self.error_rate_percent.labels(
            service=service,
            environment=self.labels['environment']
        ).set(error_rate)
    
    def set_active_connections(self, connection_type: str, count: int):
        """Set number of active connections."""
        self.active_connections.labels(
            type=connection_type,
            environment=self.labels['environment']
        ).set(count)
    
    def set_connection_pool_size(self, pool_name: str, status: str, size: int):
        """Set connection pool size."""
        self.connection_pool_size.labels(
            pool_name=pool_name,
            status=status,
            environment=self.labels['environment']
        ).set(size)


class MetricsCollector:
    """Main metrics collector that coordinates all metric types."""
    
    def __init__(self, labels: MetricLabels, metrics_port: int = 9090):
        self.labels = labels
        self.metrics_port = metrics_port
        
        # Initialize metric collectors
        self.pqc_metrics = PQCMetrics(labels)
        self.transfer_metrics = FileTransferMetrics(labels)
        self.system_metrics = SystemHealthMetrics(labels)
        
        # Service info
        self.service_info = Info(
            'pqc_service_info',
            'Information about the PQC Secure Transfer service'
        )
        self.service_info.info({
            'version': labels.version,
            'environment': labels.environment,
            'pqc_algorithm': labels.algorithm,
            'service': labels.service
        })
        
        # Background thread for system metrics
        self._metrics_thread = None
        self._stop_event = threading.Event()
        
    def start_metrics_server(self):
        """Start the Prometheus metrics HTTP server."""
        try:
            start_http_server(self.metrics_port)
            logger.info(f"Metrics server started on port {self.metrics_port}")
            
            # Start background metrics collection
            self._start_background_collection()
            
        except Exception as e:
            logger.error(f"Failed to start metrics server: {e}")
            raise
    
    def _start_background_collection(self):
        """Start background thread for periodic metrics collection."""
        def collect_metrics():
            while not self._stop_event.is_set():
                try:
                    self.system_metrics.update_system_metrics()
                except Exception as e:
                    logger.error(f"Error in background metrics collection: {e}")
                
                # Wait 30 seconds or until stop event
                self._stop_event.wait(30)
        
        self._metrics_thread = threading.Thread(target=collect_metrics, daemon=True)
        self._metrics_thread.start()
        logger.info("Background metrics collection started")
    
    def stop_metrics_collection(self):
        """Stop background metrics collection."""
        if self._stop_event:
            self._stop_event.set()
        
        if self._metrics_thread and self._metrics_thread.is_alive():
            self._metrics_thread.join(timeout=5)
            logger.info("Background metrics collection stopped")
    
    def get_pqc_metrics(self) -> PQCMetrics:
        """Get PQC metrics collector."""
        return self.pqc_metrics
    
    def get_transfer_metrics(self) -> FileTransferMetrics:
        """Get file transfer metrics collector."""
        return self.transfer_metrics
    
    def get_system_metrics(self) -> SystemHealthMetrics:
        """Get system health metrics collector."""
        return self.system_metrics


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def initialize_metrics(environment: str = "dev", service_version: str = "1.0.0", 
                      pqc_algorithm: str = "Kyber768", metrics_port: int = 9090) -> MetricsCollector:
    """Initialize the global metrics collector."""
    global _metrics_collector
    
    labels = MetricLabels(
        environment=environment,
        version=service_version,
        algorithm=pqc_algorithm
    )
    
    _metrics_collector = MetricsCollector(labels, metrics_port)
    _metrics_collector.start_metrics_server()
    
    return _metrics_collector


def get_metrics_collector() -> Optional[MetricsCollector]:
    """Get the global metrics collector instance."""
    return _metrics_collector


def shutdown_metrics():
    """Shutdown the metrics collection system."""
    global _metrics_collector
    if _metrics_collector:
        _metrics_collector.stop_metrics_collection()
        _metrics_collector = None