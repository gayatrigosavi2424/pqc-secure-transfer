"""
Configuration manager for loading and managing configurations with environment overrides.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Type, TypeVar, List

from .base_config import (
    BaseConfig, Environment, CloudProvider, ConfigValidationError,
    validate_environment_variable, load_config_file, merge_configs
)
from .deployment_config import DeploymentConfig
from .security_config import SecurityConfig
from .monitoring_config import MonitoringConfig

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseConfig)


class ConfigManager:
    """
    Configuration manager that handles loading, validation, and environment-specific overrides.
    """
    
    def __init__(self, config_dir: str = "config"):
        """
        Initialize configuration manager.
        
        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = Path(config_dir)
        self.environment = self._detect_environment()
        self.cloud_provider = self._detect_cloud_provider()
        
        logger.info(f"ConfigManager initialized for {self.environment.value} environment on {self.cloud_provider.value}")
    
    def _detect_environment(self) -> Environment:
        """Detect current environment from environment variables."""
        env_name = validate_environment_variable("ENVIRONMENT", required=False, default="dev")
        
        try:
            return Environment(env_name.lower())
        except ValueError:
            logger.warning(f"Invalid environment '{env_name}', defaulting to development")
            return Environment.DEVELOPMENT
    
    def _detect_cloud_provider(self) -> CloudProvider:
        """Detect cloud provider from environment variables."""
        provider_name = validate_environment_variable("CLOUD_PROVIDER", required=False, default="aws")
        
        try:
            return CloudProvider(provider_name.lower())
        except ValueError:
            logger.warning(f"Invalid cloud provider '{provider_name}', defaulting to AWS")
            return CloudProvider.AWS
    
    def load_deployment_config(self, config_name: Optional[str] = None) -> DeploymentConfig:
        """
        Load deployment configuration with environment-specific overrides.
        
        Args:
            config_name: Optional specific configuration name
            
        Returns:
            Validated deployment configuration
        """
        return self._load_config(
            DeploymentConfig,
            config_name or "deployment",
            DeploymentConfig.for_environment(self.environment, self.cloud_provider)
        )
    
    def load_security_config(self, config_name: Optional[str] = None) -> SecurityConfig:
        """
        Load security configuration with environment-specific overrides.
        
        Args:
            config_name: Optional specific configuration name
            
        Returns:
            Validated security configuration
        """
        return self._load_config(
            SecurityConfig,
            config_name or "security",
            SecurityConfig.for_environment(self.environment)
        )
    
    def load_monitoring_config(self, config_name: Optional[str] = None) -> MonitoringConfig:
        """
        Load monitoring configuration with environment-specific overrides.
        
        Args:
            config_name: Optional specific configuration name
            
        Returns:
            Validated monitoring configuration
        """
        return self._load_config(
            MonitoringConfig,
            config_name or "monitoring",
            MonitoringConfig.for_environment(self.environment)
        )
    
    def _load_config(self, config_class: Type[T], config_name: str, default_config: T) -> T:
        """
        Load configuration with environment-specific overrides.
        
        Args:
            config_class: Configuration class type
            config_name: Base configuration name
            default_config: Default configuration instance
            
        Returns:
            Loaded and validated configuration
        """
        # Start with default configuration
        config_data = default_config.to_dict()
        
        # Load base configuration file if it exists
        base_config_path = self.config_dir / f"{config_name}.yaml"
        if base_config_path.exists():
            logger.info(f"Loading base configuration from {base_config_path}")
            base_config_data = load_config_file(str(base_config_path))
            config_data = merge_configs(config_data, base_config_data)
        
        # Load environment-specific overrides
        env_config_path = self.config_dir / "environments" / f"{self.environment.value}.yaml"
        if env_config_path.exists():
            logger.info(f"Loading environment configuration from {env_config_path}")
            env_config_data = load_config_file(str(env_config_path))
            
            # Only merge the relevant section for this config type
            config_section = env_config_data.get(config_name, {})
            if config_section:
                config_data = merge_configs(config_data, config_section)
        
        # Load cloud provider-specific overrides
        cloud_config_path = self.config_dir / "cloud" / f"{self.cloud_provider.value}.yaml"
        if cloud_config_path.exists():
            logger.info(f"Loading cloud provider configuration from {cloud_config_path}")
            cloud_config_data = load_config_file(str(cloud_config_path))
            
            # Only merge the relevant section for this config type
            config_section = cloud_config_data.get(config_name, {})
            if config_section:
                config_data = merge_configs(config_data, config_section)
        
        # Apply environment variable overrides
        config_data = self._apply_env_var_overrides(config_data, config_name)
        
        # Create configuration instance
        try:
            config = config_class.from_dict(config_data)
        except Exception as e:
            raise ConfigValidationError([f"Failed to create {config_class.__name__}: {str(e)}"])
        
        # Validate configuration
        validation_errors = config.validate()
        if validation_errors:
            raise ConfigValidationError(validation_errors)
        
        logger.info(f"Successfully loaded and validated {config_class.__name__}")
        return config
    
    def _apply_env_var_overrides(self, config_data: Dict[str, Any], config_name: str) -> Dict[str, Any]:
        """
        Apply environment variable overrides to configuration data.
        
        Args:
            config_data: Configuration data dictionary
            config_name: Configuration name for env var prefix
            
        Returns:
            Configuration data with environment variable overrides applied
        """
        env_prefix = f"{config_name.upper()}_"
        
        for env_var, value in os.environ.items():
            if env_var.startswith(env_prefix):
                # Convert environment variable name to config key path
                config_key = env_var[len(env_prefix):].lower()
                
                # Handle nested keys (e.g., DEPLOYMENT_RESOURCE_LIMITS_CPU)
                key_parts = config_key.split('_')
                
                # Navigate to the correct nested dictionary
                current_dict = config_data
                for part in key_parts[:-1]:
                    if part not in current_dict:
                        current_dict[part] = {}
                    current_dict = current_dict[part]
                
                # Set the value, converting types as needed
                final_key = key_parts[-1]
                current_dict[final_key] = self._convert_env_var_value(value)
                
                logger.debug(f"Applied environment override: {env_var} = {value}")
        
        return config_data
    
    def _convert_env_var_value(self, value: str) -> Any:
        """
        Convert environment variable string value to appropriate type.
        
        Args:
            value: Environment variable string value
            
        Returns:
            Converted value
        """
        # Handle boolean values
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # Handle integer values
        if value.isdigit():
            return int(value)
        
        # Handle float values
        try:
            if '.' in value:
                return float(value)
        except ValueError:
            pass
        
        # Return as string
        return value
    
    def save_config(self, config: BaseConfig, config_name: str, 
                   environment_specific: bool = False) -> None:
        """
        Save configuration to file.
        
        Args:
            config: Configuration instance to save
            config_name: Configuration name
            environment_specific: Whether to save as environment-specific config
        """
        if environment_specific:
            config_path = self.config_dir / "environments" / f"{self.environment.value}.yaml"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Load existing environment config if it exists
            existing_config = {}
            if config_path.exists():
                existing_config = load_config_file(str(config_path))
            
            # Update the specific section
            existing_config[config_name] = config.to_dict()
            
            # Save updated config
            import yaml
            with open(config_path, 'w') as f:
                yaml.dump(existing_config, f, default_flow_style=False)
        else:
            config_path = self.config_dir / f"{config_name}.yaml"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_path, 'w') as f:
                f.write(config.to_yaml())
        
        logger.info(f"Saved {config.__class__.__name__} to {config_path}")
    
    def validate_all_configs(self) -> Dict[str, List[str]]:
        """
        Validate all configuration types and return any errors.
        
        Returns:
            Dictionary mapping config type to list of validation errors
        """
        validation_results = {}
        
        config_types = [
            ("deployment", self.load_deployment_config),
            ("security", self.load_security_config),
            ("monitoring", self.load_monitoring_config)
        ]
        
        for config_name, loader_func in config_types:
            try:
                config = loader_func()
                validation_errors = config.validate()
                validation_results[config_name] = validation_errors
            except ConfigValidationError as e:
                validation_results[config_name] = e.errors
            except Exception as e:
                validation_results[config_name] = [f"Failed to load config: {str(e)}"]
        
        return validation_results
    
    def get_environment_info(self) -> Dict[str, str]:
        """Get current environment information."""
        return {
            "environment": self.environment.value,
            "cloud_provider": self.cloud_provider.value,
            "config_dir": str(self.config_dir)
        }