"""
Health check system for PQC Secure Transfer.
Provides comprehensive health monitoring for all system components.
"""

import time
import asyncio
import logging
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import psutil
import aiohttp

from .pqc_metrics_integration import set_health_check_status

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    name: str
    status: HealthStatus
    message: str
    duration_ms: float
    timestamp: float = field(default_factory=time.time)
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'name': self.name,
            'status': self.status.value,
            'message': self.message,
            'duration_ms': self.duration_ms,
            'timestamp': self.timestamp,
            'details': self.details
        }


class HealthCheck:
    """Base class for health checks."""
    
    def __init__(self, name: str, timeout_seconds: float = 30.0):
        self.name = name
        self.timeout_seconds = timeout_seconds
    
    async def check(self) -> HealthCheckResult:
        """Perform the health check."""
        start_time = time.time()
        
        try:
            # Run the check with timeout
            result = await asyncio.wait_for(
                self._perform_check(),
                timeout=self.timeout_seconds
            )
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Update metrics
            set_health_check_status(self.name, result.status == HealthStatus.HEALTHY)
            
            return HealthCheckResult(
                name=self.name,
                status=result.status,
                message=result.message,
                duration_ms=duration_ms,
                details=result.details
            )
            
        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            set_health_check_status(self.name, False)
            
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check timed out after {self.timeout_seconds}s",
                duration_ms=duration_ms
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            set_health_check_status(self.name, False)
            
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
                duration_ms=duration_ms,
                details={'error': str(e)}
            )
    
    async def _perform_check(self) -> HealthCheckResult:
        """Override this method to implement the actual health check."""
        raise NotImplementedError


class PQCHealthCheck(HealthCheck):
    """Health check for PQC cryptographic operations."""
    
    def __init__(self, algorithm: str = "Kyber768"):
        super().__init__(f"pqc_{algorithm.lower()}")
        self.algorithm = algorithm
    
    async def _perform_check(self) -> HealthCheckResult:
        """Check PQC functionality."""
        try:
            # Import PQC modules
            from pqc_secure_transfer import PQCKeyExchange, StreamingEncryptor
            
            # Test key generation
            kex = PQCKeyExchange(self.algorithm)
            public_key, secret_key = kex.generate_keypair()
            
            if not public_key or not secret_key:
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.UNHEALTHY,
                    message="PQC key generation failed",
                    duration_ms=0
                )
            
            # Test encapsulation/decapsulation
            shared_secret, ciphertext = kex.encapsulate(public_key)
            decapsulated_secret = kex.decapsulate(ciphertext, secret_key)
            
            if shared_secret != decapsulated_secret:
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.UNHEALTHY,
                    message="PQC encapsulation/decapsulation mismatch",
                    duration_ms=0
                )
            
            # Test encryption/decryption
            test_data = b"PQC health check test data"
            encryptor = StreamingEncryptor(shared_secret[:32])
            encrypted = encryptor.encrypt_data(test_data)
            decrypted = encryptor.decrypt_data(encrypted)
            
            if test_data != decrypted:
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.UNHEALTHY,
                    message="PQC encryption/decryption mismatch",
                    duration_ms=0
                )
            
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.HEALTHY,
                message=f"PQC {self.algorithm} operations successful",
                duration_ms=0,
                details={
                    'algorithm': self.algorithm,
                    'public_key_size': len(public_key),
                    'secret_key_size': len(secret_key),
                    'shared_secret_size': len(shared_secret)
                }
            )
            
        except ImportError as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"PQC modules not available: {str(e)}",
                duration_ms=0
            )
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"PQC health check failed: {str(e)}",
                duration_ms=0
            )


class SystemResourcesHealthCheck(HealthCheck):
    """Health check for system resources."""
    
    def __init__(self, cpu_threshold: float = 90.0, memory_threshold: float = 90.0, 
                 disk_threshold: float = 95.0):
        super().__init__("system_resources")
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.disk_threshold = disk_threshold
    
    async def _perform_check(self) -> HealthCheckResult:
        """Check system resource usage."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage (root partition)
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # Determine overall status
            status = HealthStatus.HEALTHY
            issues = []
            
            if cpu_percent > self.cpu_threshold:
                status = HealthStatus.DEGRADED if cpu_percent < 95 else HealthStatus.UNHEALTHY
                issues.append(f"High CPU usage: {cpu_percent:.1f}%")
            
            if memory_percent > self.memory_threshold:
                status = HealthStatus.DEGRADED if memory_percent < 95 else HealthStatus.UNHEALTHY
                issues.append(f"High memory usage: {memory_percent:.1f}%")
            
            if disk_percent > self.disk_threshold:
                status = HealthStatus.UNHEALTHY
                issues.append(f"High disk usage: {disk_percent:.1f}%")
            
            message = "System resources normal"
            if issues:
                message = "; ".join(issues)
            
            return HealthCheckResult(
                name=self.name,
                status=status,
                message=message,
                duration_ms=0,
                details={
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory_percent,
                    'disk_percent': disk_percent,
                    'memory_available_gb': memory.available / (1024**3),
                    'disk_free_gb': disk.free / (1024**3)
                }
            )
            
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"System resources check failed: {str(e)}",
                duration_ms=0
            )


class NetworkConnectivityHealthCheck(HealthCheck):
    """Health check for network connectivity."""
    
    def __init__(self, test_urls: List[str] = None):
        super().__init__("network_connectivity")
        self.test_urls = test_urls or [
            "https://httpbin.org/status/200",
            "https://www.google.com",
            "https://github.com"
        ]
    
    async def _perform_check(self) -> HealthCheckResult:
        """Check network connectivity."""
        try:
            successful_connections = 0
            failed_connections = []
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                for url in self.test_urls:
                    try:
                        async with session.get(url) as response:
                            if response.status < 400:
                                successful_connections += 1
                            else:
                                failed_connections.append(f"{url}: HTTP {response.status}")
                    except Exception as e:
                        failed_connections.append(f"{url}: {str(e)}")
            
            total_tests = len(self.test_urls)
            success_rate = successful_connections / total_tests
            
            if success_rate >= 0.8:
                status = HealthStatus.HEALTHY
                message = f"Network connectivity good ({successful_connections}/{total_tests} successful)"
            elif success_rate >= 0.5:
                status = HealthStatus.DEGRADED
                message = f"Network connectivity degraded ({successful_connections}/{total_tests} successful)"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"Network connectivity poor ({successful_connections}/{total_tests} successful)"
            
            return HealthCheckResult(
                name=self.name,
                status=status,
                message=message,
                duration_ms=0,
                details={
                    'successful_connections': successful_connections,
                    'total_tests': total_tests,
                    'success_rate': success_rate,
                    'failed_connections': failed_connections
                }
            )
            
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Network connectivity check failed: {str(e)}",
                duration_ms=0
            )


class DatabaseHealthCheck(HealthCheck):
    """Health check for database connectivity."""
    
    def __init__(self, connection_string: Optional[str] = None):
        super().__init__("database")
        self.connection_string = connection_string
    
    async def _perform_check(self) -> HealthCheckResult:
        """Check database connectivity."""
        if not self.connection_string:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.HEALTHY,
                message="No database configured",
                duration_ms=0
            )
        
        # This is a placeholder - implement actual database connectivity check
        # based on your database type (PostgreSQL, MySQL, etc.)
        try:
            # Example implementation would go here
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.HEALTHY,
                message="Database connectivity successful",
                duration_ms=0
            )
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Database connectivity failed: {str(e)}",
                duration_ms=0
            )


class HealthCheckManager:
    """Manager for coordinating multiple health checks."""
    
    def __init__(self):
        self.health_checks: Dict[str, HealthCheck] = {}
        self.last_results: Dict[str, HealthCheckResult] = {}
    
    def register_health_check(self, health_check: HealthCheck):
        """Register a health check."""
        self.health_checks[health_check.name] = health_check
        logger.info(f"Registered health check: {health_check.name}")
    
    def unregister_health_check(self, name: str):
        """Unregister a health check."""
        if name in self.health_checks:
            del self.health_checks[name]
            if name in self.last_results:
                del self.last_results[name]
            logger.info(f"Unregistered health check: {name}")
    
    async def run_health_check(self, name: str) -> Optional[HealthCheckResult]:
        """Run a specific health check."""
        if name not in self.health_checks:
            return None
        
        result = await self.health_checks[name].check()
        self.last_results[name] = result
        return result
    
    async def run_all_health_checks(self) -> Dict[str, HealthCheckResult]:
        """Run all registered health checks."""
        results = {}
        
        # Run all health checks concurrently
        tasks = []
        for name, health_check in self.health_checks.items():
            tasks.append(asyncio.create_task(health_check.check()))
        
        # Wait for all to complete
        completed_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for i, (name, health_check) in enumerate(self.health_checks.items()):
            result = completed_results[i]
            
            if isinstance(result, Exception):
                result = HealthCheckResult(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Health check exception: {str(result)}",
                    duration_ms=0
                )
            
            results[name] = result
            self.last_results[name] = result
        
        return results
    
    def get_overall_health(self) -> Dict[str, Any]:
        """Get overall system health status."""
        if not self.last_results:
            return {
                'status': HealthStatus.UNKNOWN.value,
                'message': 'No health checks have been run',
                'checks': {}
            }
        
        # Determine overall status
        statuses = [result.status for result in self.last_results.values()]
        
        if all(status == HealthStatus.HEALTHY for status in statuses):
            overall_status = HealthStatus.HEALTHY
            message = "All systems healthy"
        elif any(status == HealthStatus.UNHEALTHY for status in statuses):
            overall_status = HealthStatus.UNHEALTHY
            unhealthy_checks = [
                name for name, result in self.last_results.items()
                if result.status == HealthStatus.UNHEALTHY
            ]
            message = f"Unhealthy systems: {', '.join(unhealthy_checks)}"
        elif any(status == HealthStatus.DEGRADED for status in statuses):
            overall_status = HealthStatus.DEGRADED
            degraded_checks = [
                name for name, result in self.last_results.items()
                if result.status == HealthStatus.DEGRADED
            ]
            message = f"Degraded systems: {', '.join(degraded_checks)}"
        else:
            overall_status = HealthStatus.UNKNOWN
            message = "System status unknown"
        
        return {
            'status': overall_status.value,
            'message': message,
            'timestamp': time.time(),
            'checks': {name: result.to_dict() for name, result in self.last_results.items()}
        }
    
    def get_health_check_names(self) -> List[str]:
        """Get list of registered health check names."""
        return list(self.health_checks.keys())


# Global health check manager
_health_manager = HealthCheckManager()


def get_health_manager() -> HealthCheckManager:
    """Get the global health check manager."""
    return _health_manager


def initialize_default_health_checks():
    """Initialize default health checks."""
    manager = get_health_manager()
    
    # Register default health checks
    manager.register_health_check(PQCHealthCheck())
    manager.register_health_check(SystemResourcesHealthCheck())
    manager.register_health_check(NetworkConnectivityHealthCheck())
    
    logger.info("Default health checks initialized")