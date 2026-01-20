"""
Deployment configuration classes.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from .base_config import BaseConfig, Environment, CloudProvider


@dataclass
class ResourceLimits(BaseConfig):
    """Resource limits configuration."""
    cpu: str = "1000m"
    memory: str = "2Gi"
    storage: str = "10Gi"
    max_instances: int = 10
    min_instances: int = 1
    
    def _validate_custom(self) -> List[str]:
        """Validate resource limits."""
        errors = []
        
        if self.max_instances < self.min_instances:
            errors.append("max_instances must be greater than or equal to min_instances")
        
        if self.min_instances < 1:
            errors.append("min_instances must be at least 1")
        
        if self.max_instances > 100:
            errors.append("max_instances cannot exceed 100")
        
        return errors


@dataclass
class NetworkConfig(BaseConfig):
    """Network configuration."""
    vpc_cidr: str = "10.0.0.0/16"
    public_subnets: List[str] = field(default_factory=lambda: ["10.0.1.0/24", "10.0.2.0/24"])
    private_subnets: List[str] = field(default_factory=lambda: ["10.0.10.0/24", "10.0.20.0/24"])
    enable_nat_gateway: bool = True
    enable_vpn_gateway: bool = False
    
    def _validate_custom(self) -> List[str]:
        """Validate network configuration."""
        errors = []
        
        if not self.vpc_cidr:
            errors.append("vpc_cidr is required")
        
        if not self.public_subnets:
            errors.append("At least one public subnet is required")
        
        return errors


@dataclass
class DeploymentConfig(BaseConfig):
    """Main deployment configuration."""
    
    # Basic deployment settings
    name: str = "pqc-secure-transfer"
    environment: Environment = Environment.DEVELOPMENT
    cloud_provider: CloudProvider = CloudProvider.AWS
    region: str = "us-west-2"
    
    # Resource configuration
    resource_limits: ResourceLimits = field(default_factory=ResourceLimits)
    network_config: NetworkConfig = field(default_factory=NetworkConfig)
    
    # Application settings
    image_repository: str = "pqc-secure-transfer"
    image_tag: str = "latest"
    port: int = 8765
    
    # Feature flags
    enable_autoscaling: bool = True
    enable_load_balancer: bool = True
    enable_ssl: bool = True
    
    # Environment-specific overrides
    custom_env_vars: Dict[str, str] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)
    
    def _validate_custom(self) -> List[str]:
        """Custom validation for deployment configuration."""
        errors = []
        
        # Validate name
        if not self.name or not self.name.replace('-', '').replace('_', '').isalnum():
            errors.append("name must be alphanumeric with hyphens or underscores only")
        
        # Validate port
        if not (1 <= self.port <= 65535):
            errors.append("port must be between 1 and 65535")
        
        # Validate image repository
        if not self.image_repository:
            errors.append("image_repository is required")
        
        # Validate resource limits
        if self.resource_limits:
            errors.extend(self.resource_limits.validate())
        
        # Validate network config
        if self.network_config:
            errors.extend(self.network_config.validate())
        
        # Environment-specific validations
        if self.environment == Environment.PRODUCTION:
            if not self.enable_ssl:
                errors.append("SSL must be enabled in production environment")
            
            if self.resource_limits.min_instances < 2:
                errors.append("Production environment must have at least 2 instances")
        
        return errors
    
    def get_full_image_name(self) -> str:
        """Get full Docker image name with tag."""
        return f"{self.image_repository}:{self.image_tag}"
    
    def get_resource_name(self, resource_type: str) -> str:
        """Generate resource name with environment prefix."""
        return f"{self.name}-{resource_type}-{self.environment.value}"
    
    def get_environment_tags(self) -> Dict[str, str]:
        """Get standard tags for resources."""
        standard_tags = {
            "Environment": self.environment.value,
            "Application": self.name,
            "CloudProvider": self.cloud_provider.value,
            "ManagedBy": "terraform"
        }
        
        # Merge with custom tags
        return {**standard_tags, **self.tags}
    
    @classmethod
    def for_environment(cls, environment: Environment, 
                       cloud_provider: CloudProvider = CloudProvider.AWS) -> 'DeploymentConfig':
        """Create environment-specific configuration with defaults."""
        
        config = cls(
            environment=environment,
            cloud_provider=cloud_provider
        )
        
        # Environment-specific defaults
        if environment == Environment.DEVELOPMENT:
            config.resource_limits = ResourceLimits(
                cpu="500m",
                memory="1Gi",
                max_instances=3,
                min_instances=1
            )
            config.enable_autoscaling = False
            
        elif environment == Environment.STAGING:
            config.resource_limits = ResourceLimits(
                cpu="1000m",
                memory="2Gi",
                max_instances=10,
                min_instances=2
            )
            config.region = "us-west-2"
            
        elif environment == Environment.PRODUCTION:
            config.resource_limits = ResourceLimits(
                cpu="2000m",
                memory="4Gi",
                max_instances=50,
                min_instances=3
            )
            config.region = "us-east-1"
            config.enable_ssl = True
        
        return config