"""
Integration module for PQC Secure Transfer metrics.
Provides decorators and context managers for automatic metrics collection.
"""

import time
import functools
from typing import Optional, Dict, Any, Callable
from contextlib import contextmanager
import logging

from .metrics import get_metrics_collector, MetricsCollector

logger = logging.getLogger(__name__)


class MetricsIntegration:
    """Integration class for automatic metrics collection in PQC operations."""
    
    def __init__(self):
        self._active_transfers: Dict[str, Dict[str, Any]] = {}
        self._transfer_counter = 0
    
    @property
    def metrics(self) -> Optional[MetricsCollector]:
        """Get the metrics collector instance."""
        return get_metrics_collector()
    
    def pqc_key_exchange_metrics(self, algorithm: str = "Kyber768"):
        """Decorator for PQC key exchange operations."""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                if not self.metrics:
                    return func(*args, **kwargs)
                
                start_time = time.time()
                status = "success"
                
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    status = "error"
                    logger.error(f"PQC key exchange failed: {e}")
                    raise
                finally:
                    duration = time.time() - start_time
                    self.metrics.get_pqc_metrics().record_key_exchange(
                        algorithm=algorithm,
                        status=status,
                        duration=duration
                    )
            
            return wrapper
        return decorator
    
    def pqc_key_generation_metrics(self, algorithm: str = "Kyber768"):
        """Decorator for PQC key generation operations."""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                if not self.metrics:
                    return func(*args, **kwargs)
                
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start_time
                    self.metrics.get_pqc_metrics().record_key_generation(
                        algorithm=algorithm,
                        duration=duration
                    )
            
            return wrapper
        return decorator
    
    def pqc_encapsulation_metrics(self, algorithm: str = "Kyber768"):
        """Decorator for PQC encapsulation operations."""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                if not self.metrics:
                    return func(*args, **kwargs)
                
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start_time
                    self.metrics.get_pqc_metrics().record_encapsulation(
                        algorithm=algorithm,
                        duration=duration
                    )
            
            return wrapper
        return decorator
    
    def pqc_decapsulation_metrics(self, algorithm: str = "Kyber768"):
        """Decorator for PQC decapsulation operations."""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                if not self.metrics:
                    return func(*args, **kwargs)
                
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start_time
                    self.metrics.get_pqc_metrics().record_decapsulation(
                        algorithm=algorithm,
                        duration=duration
                    )
            
            return wrapper
        return decorator
    
    @contextmanager
    def file_transfer_context(self, transfer_type: str = "upload", 
                            file_size: Optional[int] = None):
        """Context manager for file transfer operations."""
        if not self.metrics:
            yield
            return
        
        self._transfer_counter += 1
        transfer_id = f"transfer_{self._transfer_counter}"
        
        # Record transfer start
        start_time = time.time()
        self.metrics.get_transfer_metrics().record_transfer_start(transfer_type)
        
        # Store transfer info
        self._active_transfers[transfer_id] = {
            'type': transfer_type,
            'start_time': start_time,
            'size': file_size
        }
        
        status = "success"
        actual_size = file_size
        
        try:
            yield transfer_id
        except Exception as e:
            status = "error"
            logger.error(f"File transfer failed: {e}")
            raise
        finally:
            # Record transfer completion
            duration = time.time() - start_time
            
            if transfer_id in self._active_transfers:
                transfer_info = self._active_transfers.pop(transfer_id)
                actual_size = transfer_info.get('size', file_size or 0)
            
            self.metrics.get_transfer_metrics().record_transfer_complete(
                transfer_type=transfer_type,
                status=status,
                size_bytes=actual_size or 0,
                duration_seconds=duration
            )
    
    def update_transfer_size(self, transfer_id: str, size_bytes: int):
        """Update the size of an active transfer."""
        if transfer_id in self._active_transfers:
            self._active_transfers[transfer_id]['size'] = size_bytes
    
    def record_security_event(self, event_type: str, severity: str = "info"):
        """Record a security event."""
        if self.metrics:
            self.metrics.get_pqc_metrics().record_security_event(event_type, severity)
    
    def record_key_rotation(self, algorithm: str = "Kyber768", rotation_type: str = "scheduled"):
        """Record a key rotation event."""
        if self.metrics:
            self.metrics.get_pqc_metrics().record_key_rotation(algorithm, rotation_type)
    
    def update_active_keys(self, algorithm: str, key_type: str, count: int):
        """Update the count of active keys."""
        if self.metrics:
            self.metrics.get_pqc_metrics().set_active_keys(algorithm, key_type, count)
    
    def update_encryption_throughput(self, algorithm: str, throughput_mbps: float):
        """Update encryption throughput metric."""
        if self.metrics:
            self.metrics.get_transfer_metrics().set_encryption_throughput(algorithm, throughput_mbps)
    
    def update_decryption_throughput(self, algorithm: str, throughput_mbps: float):
        """Update decryption throughput metric."""
        if self.metrics:
            self.metrics.get_transfer_metrics().set_decryption_throughput(algorithm, throughput_mbps)
    
    def update_queue_length(self, priority: str, length: int):
        """Update transfer queue length."""
        if self.metrics:
            self.metrics.get_transfer_metrics().set_queue_length(priority, length)
    
    def set_health_check_status(self, check_name: str, is_healthy: bool):
        """Set health check status."""
        if self.metrics:
            self.metrics.get_system_metrics().set_health_check_status(check_name, is_healthy)
    
    def set_error_rate(self, service: str, error_rate: float):
        """Set service error rate."""
        if self.metrics:
            self.metrics.get_system_metrics().set_error_rate(service, error_rate)
    
    def update_connection_count(self, connection_type: str, count: int):
        """Update active connection count."""
        if self.metrics:
            self.metrics.get_system_metrics().set_active_connections(connection_type, count)


# Global metrics integration instance
_metrics_integration = MetricsIntegration()


def get_metrics_integration() -> MetricsIntegration:
    """Get the global metrics integration instance."""
    return _metrics_integration


# Convenience decorators using the global instance
def pqc_key_exchange_metrics(algorithm: str = "Kyber768"):
    """Decorator for PQC key exchange operations."""
    return _metrics_integration.pqc_key_exchange_metrics(algorithm)


def pqc_key_generation_metrics(algorithm: str = "Kyber768"):
    """Decorator for PQC key generation operations."""
    return _metrics_integration.pqc_key_generation_metrics(algorithm)


def pqc_encapsulation_metrics(algorithm: str = "Kyber768"):
    """Decorator for PQC encapsulation operations."""
    return _metrics_integration.pqc_encapsulation_metrics(algorithm)


def pqc_decapsulation_metrics(algorithm: str = "Kyber768"):
    """Decorator for PQC decapsulation operations."""
    return _metrics_integration.pqc_decapsulation_metrics(algorithm)


def file_transfer_context(transfer_type: str = "upload", file_size: Optional[int] = None):
    """Context manager for file transfer operations."""
    return _metrics_integration.file_transfer_context(transfer_type, file_size)


# Convenience functions
def record_security_event(event_type: str, severity: str = "info"):
    """Record a security event."""
    _metrics_integration.record_security_event(event_type, severity)


def record_key_rotation(algorithm: str = "Kyber768", rotation_type: str = "scheduled"):
    """Record a key rotation event."""
    _metrics_integration.record_key_rotation(algorithm, rotation_type)


def update_active_keys(algorithm: str, key_type: str, count: int):
    """Update the count of active keys."""
    _metrics_integration.update_active_keys(algorithm, key_type, count)


def update_encryption_throughput(algorithm: str, throughput_mbps: float):
    """Update encryption throughput metric."""
    _metrics_integration.update_encryption_throughput(algorithm, throughput_mbps)


def update_decryption_throughput(algorithm: str, throughput_mbps: float):
    """Update decryption throughput metric."""
    _metrics_integration.update_decryption_throughput(algorithm, throughput_mbps)


def set_health_check_status(check_name: str, is_healthy: bool):
    """Set health check status."""
    _metrics_integration.set_health_check_status(check_name, is_healthy)


def set_error_rate(service: str, error_rate: float):
    """Set service error rate."""
    _metrics_integration.set_error_rate(service, error_rate)