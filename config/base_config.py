"""
Base configuration classes and validation logic.
"""

import os
import json
import yaml
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class Environment(Enum):
    """Supported deployment environments."""
    DEVELOPMENT = "dev"
    STAGING = "staging"
    PRODUCTION = "prod"


class CloudProvider(Enum):
    """Supported cloud providers."""
    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"


@dataclass
class BaseConfig(ABC):
    """Base configuration class with validation and serialization."""
    
    def validate(self) -> List[str]:
        """
        Validate configuration and return list of validation errors.
        
        Returns:
            List of validation error messages. Empty list if valid.
        """
        errors = []
        errors.extend(self._validate_required_fields())
        errors.extend(self._validate_custom())
        return errors
    
    def _validate_required_fields(self) -> List[str]:
        """Validate that all required fields are present and not None."""
        errors = []
        # For now, skip automatic required field validation
        # This can be implemented per-config class as needed
        return errors
    
    @abstractmethod
    def _validate_custom(self) -> List[str]:
        """Custom validation logic specific to each config class."""
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        result = {}
        for field_name, field_def in self.__dataclass_fields__.items():
            value = getattr(self, field_name)
            if isinstance(value, Enum):
                result[field_name] = value.value
            elif isinstance(value, BaseConfig):
                result[field_name] = value.to_dict()
            else:
                result[field_name] = value
        return result
    
    def to_json(self) -> str:
        """Convert configuration to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    def to_yaml(self) -> str:
        """Convert configuration to YAML string."""
        return yaml.dump(self.to_dict(), default_flow_style=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseConfig':
        """Create configuration instance from dictionary."""
        processed_data = {}
        
        for field_name, value in data.items():
            if hasattr(cls, '__dataclass_fields__') and field_name in cls.__dataclass_fields__:
                field_def = cls.__dataclass_fields__[field_name]
                field_type = field_def.type
                
                # Handle enum fields
                if (hasattr(field_type, '__bases__') and 
                    any(base.__name__ == 'Enum' for base in field_type.__bases__)):
                    if isinstance(value, str):
                        processed_data[field_name] = field_type(value)
                    else:
                        processed_data[field_name] = value
                # Handle nested BaseConfig objects
                elif (hasattr(field_type, '__bases__') and 
                      any(base.__name__ == 'BaseConfig' for base in field_type.__bases__)):
                    if isinstance(value, dict):
                        processed_data[field_name] = field_type.from_dict(value)
                    else:
                        processed_data[field_name] = value
                else:
                    processed_data[field_name] = value
            else:
                processed_data[field_name] = value
        
        return cls(**processed_data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'BaseConfig':
        """Create configuration instance from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    @classmethod
    def from_yaml(cls, yaml_str: str) -> 'BaseConfig':
        """Create configuration instance from YAML string."""
        data = yaml.safe_load(yaml_str)
        return cls.from_dict(data)


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    
    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__(f"Configuration validation failed: {', '.join(errors)}")


def validate_environment_variable(var_name: str, required: bool = True, 
                                default: Optional[str] = None) -> Optional[str]:
    """
    Validate and retrieve environment variable.
    
    Args:
        var_name: Name of environment variable
        required: Whether the variable is required
        default: Default value if variable is not set
        
    Returns:
        Environment variable value or default
        
    Raises:
        ConfigValidationError: If required variable is missing
    """
    value = os.getenv(var_name, default)
    
    if required and value is None:
        raise ConfigValidationError([f"Required environment variable '{var_name}' is not set"])
    
    return value


def load_config_file(file_path: str) -> Dict[str, Any]:
    """
    Load configuration from file (JSON or YAML).
    
    Args:
        file_path: Path to configuration file
        
    Returns:
        Configuration data as dictionary
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ConfigValidationError: If file format is invalid
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Configuration file not found: {file_path}")
    
    try:
        with open(file_path, 'r') as f:
            if file_path.endswith('.json'):
                return json.load(f)
            elif file_path.endswith(('.yaml', '.yml')):
                return yaml.safe_load(f)
            else:
                raise ConfigValidationError([f"Unsupported file format: {file_path}"])
    except (json.JSONDecodeError, yaml.YAMLError) as e:
        raise ConfigValidationError([f"Invalid file format in {file_path}: {str(e)}"])


def merge_configs(base_config: Dict[str, Any], 
                 override_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge two configuration dictionaries with override taking precedence.
    
    Args:
        base_config: Base configuration dictionary
        override_config: Override configuration dictionary
        
    Returns:
        Merged configuration dictionary
    """
    result = base_config.copy()
    
    for key, value in override_config.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value
    
    return result