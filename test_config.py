#!/usr/bin/env python3
"""
Test script for configuration management system.
"""

import os
import sys
from pathlib import Path

# Add config directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from config import ConfigManager, Environment, CloudProvider


def test_config_loading():
    """Test configuration loading and validation."""
    print("Testing Configuration Management System")
    print("=" * 50)
    
    # Test different environments
    environments = [Environment.DEVELOPMENT, Environment.STAGING, Environment.PRODUCTION]
    
    for env in environments:
        print(f"\nTesting {env.value} environment:")
        
        # Set environment variables
        os.environ["ENVIRONMENT"] = env.value
        os.environ["CLOUD_PROVIDER"] = "aws"
        
        try:
            # Initialize config manager
            config_manager = ConfigManager()
            
            # Load all configuration types
            deployment_config = config_manager.load_deployment_config()
            security_config = config_manager.load_security_config()
            monitoring_config = config_manager.load_monitoring_config()
            
            print(f"  ✓ Deployment config loaded successfully")
            print(f"    - Instances: {deployment_config.resource_limits.min_instances}-{deployment_config.resource_limits.max_instances}")
            print(f"    - Auto-scaling: {deployment_config.enable_autoscaling}")
            print(f"    - SSL: {deployment_config.enable_ssl}")
            
            print(f"  ✓ Security config loaded successfully")
            print(f"    - PQC Algorithm: {security_config.encryption.pqc_algorithm}")
            print(f"    - Key rotation: {security_config.key_management.key_rotation_days} days")
            print(f"    - MFA: {security_config.access_control.enable_mfa}")
            
            print(f"  ✓ Monitoring config loaded successfully")
            print(f"    - Log level: {monitoring_config.logging.log_level}")
            print(f"    - Alerting: {monitoring_config.alerting.enable_alerting}")
            print(f"    - Retention: {monitoring_config.metrics.retention_days} days")
            
        except Exception as e:
            print(f"  ✗ Error loading configuration: {e}")
    
    # Test validation
    print(f"\nTesting configuration validation:")
    try:
        config_manager = ConfigManager()
        validation_results = config_manager.validate_all_configs()
        
        for config_type, errors in validation_results.items():
            if errors:
                print(f"  ✗ {config_type}: {len(errors)} validation errors")
                for error in errors:
                    print(f"    - {error}")
            else:
                print(f"  ✓ {config_type}: validation passed")
    
    except Exception as e:
        print(f"  ✗ Validation error: {e}")
    
    # Test environment variable overrides
    print(f"\nTesting environment variable overrides:")
    try:
        os.environ["DEPLOYMENT_RESOURCE_LIMITS_CPU"] = "4000m"
        os.environ["SECURITY_KEY_MANAGEMENT_KEY_ROTATION_DAYS"] = "14"
        
        config_manager = ConfigManager()
        deployment_config = config_manager.load_deployment_config()
        security_config = config_manager.load_security_config()
        
        print(f"  ✓ CPU override applied: {deployment_config.resource_limits.cpu}")
        print(f"  ✓ Key rotation override applied: {security_config.key_management.key_rotation_days} days")
        
        # Clean up environment variables
        del os.environ["DEPLOYMENT_RESOURCE_LIMITS_CPU"]
        del os.environ["SECURITY_KEY_MANAGEMENT_KEY_ROTATION_DAYS"]
        
    except Exception as e:
        print(f"  ✗ Environment override error: {e}")
    
    print(f"\nConfiguration system test completed!")


if __name__ == "__main__":
    test_config_loading()