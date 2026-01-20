"""
Monitoring and observability configuration classes.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from .base_config import BaseConfig, Environment


@dataclass
class MetricsConfig(BaseConfig):
    """Metrics collection configuration."""
    enable_metrics: bool = True
    metrics_port: int = 9090
    scrape_interval_seconds: int = 15
    retention_days: int = 30
    
    # PQC-specific metrics
    enable_pqc_metrics: bool = True
    enable_transfer_metrics: bool = True
    enable_performance_metrics: bool = True
    
    def _validate_custom(self) -> List[str]:
        """Validate metrics configuration."""
        errors = []
        
        if not (1 <= self.metrics_port <= 65535):
            errors.append("metrics_port must be between 1 and 65535")
        
        if self.scrape_interval_seconds < 5:
            errors.append("scrape_interval_seconds must be at least 5")
        
        if self.retention_days < 1:
            errors.append("retention_days must be at least 1")
        
        return errors


@dataclass
class LoggingConfig(BaseConfig):
    """Logging configuration."""
    enable_logging: bool = True
    log_level: str = "INFO"
    log_format: str = "json"
    log_retention_days: int = 30
    
    # Structured logging
    enable_structured_logging: bool = True
    enable_correlation_ids: bool = True
    
    # Log aggregation
    enable_centralized_logging: bool = True
    log_aggregation_endpoint: Optional[str] = None
    
    def _validate_custom(self) -> List[str]:
        """Validate logging configuration."""
        errors = []
        
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level not in valid_log_levels:
            errors.append(f"log_level must be one of: {valid_log_levels}")
        
        valid_log_formats = ["json", "text"]
        if self.log_format not in valid_log_formats:
            errors.append(f"log_format must be one of: {valid_log_formats}")
        
        if self.log_retention_days < 1:
            errors.append("log_retention_days must be at least 1")
        
        return errors


@dataclass
class AlertingConfig(BaseConfig):
    """Alerting configuration."""
    enable_alerting: bool = True
    alert_manager_endpoint: Optional[str] = None
    
    # Alert channels
    email_alerts: List[str] = field(default_factory=list)
    slack_webhook: Optional[str] = None
    pagerduty_key: Optional[str] = None
    
    # Alert thresholds
    cpu_threshold_percent: float = 80.0
    memory_threshold_percent: float = 85.0
    disk_threshold_percent: float = 90.0
    error_rate_threshold_percent: float = 5.0
    
    # PQC-specific alerts
    pqc_key_exchange_failure_threshold: int = 5
    transfer_failure_threshold_percent: float = 10.0
    
    def _validate_custom(self) -> List[str]:
        """Validate alerting configuration."""
        errors = []
        
        # Validate threshold percentages
        thresholds = [
            ("cpu_threshold_percent", self.cpu_threshold_percent),
            ("memory_threshold_percent", self.memory_threshold_percent),
            ("disk_threshold_percent", self.disk_threshold_percent),
            ("error_rate_threshold_percent", self.error_rate_threshold_percent),
            ("transfer_failure_threshold_percent", self.transfer_failure_threshold_percent)
        ]
        
        for name, value in thresholds:
            if not (0 <= value <= 100):
                errors.append(f"{name} must be between 0 and 100")
        
        if self.pqc_key_exchange_failure_threshold < 1:
            errors.append("pqc_key_exchange_failure_threshold must be at least 1")
        
        # Validate email addresses
        for email in self.email_alerts:
            if "@" not in email:
                errors.append(f"Invalid email address: {email}")
        
        return errors


@dataclass
class TracingConfig(BaseConfig):
    """Distributed tracing configuration."""
    enable_tracing: bool = True
    tracing_endpoint: Optional[str] = None
    sampling_rate: float = 0.1
    
    # Trace retention
    trace_retention_days: int = 7
    
    def _validate_custom(self) -> List[str]:
        """Validate tracing configuration."""
        errors = []
        
        if not (0.0 <= self.sampling_rate <= 1.0):
            errors.append("sampling_rate must be between 0.0 and 1.0")
        
        if self.trace_retention_days < 1:
            errors.append("trace_retention_days must be at least 1")
        
        return errors


@dataclass
class HealthCheckConfig(BaseConfig):
    """Health check configuration."""
    enable_health_checks: bool = True
    health_check_path: str = "/health"
    readiness_check_path: str = "/ready"
    
    # Health check intervals
    health_check_interval_seconds: int = 30
    health_check_timeout_seconds: int = 5
    health_check_retries: int = 3
    
    def _validate_custom(self) -> List[str]:
        """Validate health check configuration."""
        errors = []
        
        if self.health_check_interval_seconds < 5:
            errors.append("health_check_interval_seconds must be at least 5")
        
        if self.health_check_timeout_seconds < 1:
            errors.append("health_check_timeout_seconds must be at least 1")
        
        if self.health_check_retries < 1:
            errors.append("health_check_retries must be at least 1")
        
        return errors


@dataclass
class MonitoringConfig(BaseConfig):
    """Main monitoring configuration."""
    
    # Core monitoring components
    metrics: MetricsConfig = field(default_factory=MetricsConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    alerting: AlertingConfig = field(default_factory=AlertingConfig)
    tracing: TracingConfig = field(default_factory=TracingConfig)
    health_checks: HealthCheckConfig = field(default_factory=HealthCheckConfig)
    
    # Dashboard configuration
    enable_dashboards: bool = True
    grafana_endpoint: Optional[str] = None
    
    # Monitoring stack
    monitoring_stack: str = "prometheus"  # prometheus, datadog, newrelic
    
    def _validate_custom(self) -> List[str]:
        """Custom validation for monitoring configuration."""
        errors = []
        
        # Validate sub-configurations
        errors.extend(self.metrics.validate())
        errors.extend(self.logging.validate())
        errors.extend(self.alerting.validate())
        errors.extend(self.tracing.validate())
        errors.extend(self.health_checks.validate())
        
        # Validate monitoring stack
        valid_stacks = ["prometheus", "datadog", "newrelic", "cloudwatch"]
        if self.monitoring_stack not in valid_stacks:
            errors.append(f"monitoring_stack must be one of: {valid_stacks}")
        
        return errors
    
    @classmethod
    def for_environment(cls, environment: Environment) -> 'MonitoringConfig':
        """Create environment-specific monitoring configuration."""
        
        config = cls()
        
        if environment == Environment.DEVELOPMENT:
            # Basic monitoring for development
            config.metrics.retention_days = 7
            config.logging.log_level = "DEBUG"
            config.logging.log_retention_days = 7
            config.alerting.enable_alerting = False
            config.tracing.sampling_rate = 1.0  # Trace everything in dev
            
        elif environment == Environment.STAGING:
            # Moderate monitoring for staging
            config.metrics.retention_days = 30
            config.logging.log_level = "INFO"
            config.logging.log_retention_days = 30
            config.alerting.enable_alerting = True
            config.tracing.sampling_rate = 0.5
            
        elif environment == Environment.PRODUCTION:
            # Comprehensive monitoring for production
            config.metrics.retention_days = 90
            config.logging.log_level = "INFO"
            config.logging.log_retention_days = 90
            config.alerting.enable_alerting = True
            config.tracing.sampling_rate = 0.1
            config.tracing.trace_retention_days = 30
            
            # Stricter thresholds for production
            config.alerting.cpu_threshold_percent = 70.0
            config.alerting.memory_threshold_percent = 75.0
            config.alerting.error_rate_threshold_percent = 1.0
        
        return config
    
    def get_prometheus_config(self) -> Dict[str, any]:
        """Get Prometheus-specific configuration."""
        return {
            "global": {
                "scrape_interval": f"{self.metrics.scrape_interval_seconds}s",
                "evaluation_interval": f"{self.metrics.scrape_interval_seconds}s"
            },
            "scrape_configs": [
                {
                    "job_name": "pqc-secure-transfer",
                    "static_configs": [
                        {"targets": [f"pqc-server:{self.metrics.metrics_port}"]}
                    ],
                    "metrics_path": "/metrics",
                    "scrape_interval": f"{self.metrics.scrape_interval_seconds}s"
                }
            ]
        }
    
    def get_grafana_dashboard_config(self) -> Dict[str, any]:
        """Get Grafana dashboard configuration."""
        return {
            "dashboard": {
                "title": "PQC Secure Transfer Monitoring",
                "panels": [
                    {
                        "title": "PQC Key Exchanges",
                        "type": "graph",
                        "targets": [
                            {"expr": "rate(pqc_key_exchanges_total[5m])"}
                        ]
                    },
                    {
                        "title": "File Transfer Throughput",
                        "type": "graph", 
                        "targets": [
                            {"expr": "pqc_encryption_throughput_mbps"}
                        ]
                    },
                    {
                        "title": "Active Transfers",
                        "type": "singlestat",
                        "targets": [
                            {"expr": "active_transfers"}
                        ]
                    }
                ]
            }
        }