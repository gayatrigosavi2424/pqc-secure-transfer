"""
Security configuration classes.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from .base_config import BaseConfig, Environment


@dataclass
class EncryptionConfig(BaseConfig):
    """Encryption configuration."""
    enable_encryption_at_rest: bool = True
    enable_encryption_in_transit: bool = True
    pqc_algorithm: str = "Kyber768"
    key_size: int = 768
    
    def _validate_custom(self) -> List[str]:
        """Validate encryption configuration."""
        errors = []
        
        supported_algorithms = ["Kyber512", "Kyber768", "Kyber1024"]
        if self.pqc_algorithm not in supported_algorithms:
            errors.append(f"pqc_algorithm must be one of: {supported_algorithms}")
        
        valid_key_sizes = [512, 768, 1024]
        if self.key_size not in valid_key_sizes:
            errors.append(f"key_size must be one of: {valid_key_sizes}")
        
        return errors


@dataclass
class KeyManagementConfig(BaseConfig):
    """Key management configuration."""
    key_rotation_days: int = 30
    enable_key_backup: bool = True
    backup_retention_days: int = 90
    enable_key_escrow: bool = False
    
    def _validate_custom(self) -> List[str]:
        """Validate key management configuration."""
        errors = []
        
        if self.key_rotation_days < 1:
            errors.append("key_rotation_days must be at least 1")
        
        if self.key_rotation_days > 365:
            errors.append("key_rotation_days cannot exceed 365")
        
        if self.backup_retention_days < self.key_rotation_days:
            errors.append("backup_retention_days must be at least as long as key_rotation_days")
        
        return errors


@dataclass
class AccessControlConfig(BaseConfig):
    """Access control configuration."""
    enable_rbac: bool = True
    enable_mfa: bool = False
    session_timeout_minutes: int = 60
    max_failed_attempts: int = 5
    lockout_duration_minutes: int = 15
    
    def _validate_custom(self) -> List[str]:
        """Validate access control configuration."""
        errors = []
        
        if self.session_timeout_minutes < 5:
            errors.append("session_timeout_minutes must be at least 5")
        
        if self.max_failed_attempts < 1:
            errors.append("max_failed_attempts must be at least 1")
        
        if self.lockout_duration_minutes < 1:
            errors.append("lockout_duration_minutes must be at least 1")
        
        return errors


@dataclass
class AuditConfig(BaseConfig):
    """Audit logging configuration."""
    enable_audit_logging: bool = True
    log_retention_days: int = 90
    enable_log_integrity_check: bool = True
    audit_log_encryption: bool = True
    
    def _validate_custom(self) -> List[str]:
        """Validate audit configuration."""
        errors = []
        
        if self.log_retention_days < 30:
            errors.append("log_retention_days must be at least 30 for compliance")
        
        return errors


@dataclass
class SecurityConfig(BaseConfig):
    """Main security configuration."""
    
    # Encryption settings
    encryption: EncryptionConfig = field(default_factory=EncryptionConfig)
    
    # Key management
    key_management: KeyManagementConfig = field(default_factory=KeyManagementConfig)
    
    # Access control
    access_control: AccessControlConfig = field(default_factory=AccessControlConfig)
    
    # Audit logging
    audit: AuditConfig = field(default_factory=AuditConfig)
    
    # Security scanning
    enable_vulnerability_scanning: bool = True
    enable_secret_scanning: bool = True
    enable_compliance_checks: bool = True
    
    # Network security
    enable_network_policies: bool = True
    allowed_cidr_blocks: List[str] = field(default_factory=lambda: ["0.0.0.0/0"])
    
    # Cloud-specific security settings
    cloud_security_settings: Dict[str, str] = field(default_factory=dict)
    
    def _validate_custom(self) -> List[str]:
        """Custom validation for security configuration."""
        errors = []
        
        # Validate sub-configurations
        errors.extend(self.encryption.validate())
        errors.extend(self.key_management.validate())
        errors.extend(self.access_control.validate())
        errors.extend(self.audit.validate())
        
        # Validate CIDR blocks
        for cidr in self.allowed_cidr_blocks:
            if not self._is_valid_cidr(cidr):
                errors.append(f"Invalid CIDR block: {cidr}")
        
        return errors
    
    def _is_valid_cidr(self, cidr: str) -> bool:
        """Validate CIDR block format."""
        try:
            import ipaddress
            ipaddress.ip_network(cidr, strict=False)
            return True
        except ValueError:
            return False
    
    @classmethod
    def for_environment(cls, environment: Environment) -> 'SecurityConfig':
        """Create environment-specific security configuration."""
        
        config = cls()
        
        if environment == Environment.DEVELOPMENT:
            # Relaxed security for development
            config.access_control.enable_mfa = False
            config.key_management.key_rotation_days = 90
            config.audit.log_retention_days = 30
            config.allowed_cidr_blocks = ["0.0.0.0/0"]  # Allow all for dev
            
        elif environment == Environment.STAGING:
            # Moderate security for staging
            config.access_control.enable_mfa = False
            config.key_management.key_rotation_days = 30
            config.audit.log_retention_days = 60
            
        elif environment == Environment.PRODUCTION:
            # Strict security for production
            config.access_control.enable_mfa = True
            config.key_management.key_rotation_days = 7
            config.key_management.enable_key_escrow = True
            config.audit.log_retention_days = 365
            config.enable_compliance_checks = True
            
            # Restrict network access in production
            config.allowed_cidr_blocks = [
                "10.0.0.0/8",    # Private networks
                "172.16.0.0/12", 
                "192.168.0.0/16"
            ]
        
        return config
    
    def get_pqc_config(self) -> Dict[str, str]:
        """Get PQC-specific configuration for application."""
        return {
            "PQC_ALGORITHM": self.encryption.pqc_algorithm,
            "PQC_KEY_SIZE": str(self.encryption.key_size),
            "KEY_ROTATION_DAYS": str(self.key_management.key_rotation_days),
            "ENABLE_KEY_BACKUP": str(self.key_management.enable_key_backup).lower(),
            "AUDIT_ENABLED": str(self.audit.enable_audit_logging).lower()
        }