"""
Automated PQC key rotation system.
Handles scheduled rotation, emergency rotation, and key lifecycle management.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import os

from .secret_manager import UnifiedSecretManager, create_secret_manager
from monitoring.pqc_metrics_integration import record_key_rotation, record_security_event, update_active_keys

logger = logging.getLogger(__name__)


class RotationType(Enum):
    """Types of key rotation."""
    SCHEDULED = "scheduled"
    EMERGENCY = "emergency"
    MANUAL = "manual"
    COMPLIANCE = "compliance"


class RotationStatus(Enum):
    """Status of key rotation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class RotationPolicy:
    """Key rotation policy configuration."""
    algorithm: str
    rotation_interval_days: int
    max_key_age_days: int
    backup_retention_days: int
    enable_automatic_rotation: bool = True
    emergency_rotation_threshold_hours: int = 24
    compliance_rotation_required: bool = True
    
    def is_rotation_due(self, last_rotation: datetime) -> bool:
        """Check if rotation is due based on policy."""
        age = datetime.utcnow() - last_rotation
        return age.days >= self.rotation_interval_days
    
    def is_emergency_rotation_needed(self, last_rotation: datetime) -> bool:
        """Check if emergency rotation is needed."""
        age = datetime.utcnow() - last_rotation
        return age.days > self.max_key_age_days


@dataclass
class RotationRecord:
    """Record of a key rotation operation."""
    rotation_id: str
    key_name: str
    algorithm: str
    rotation_type: RotationType
    status: RotationStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    old_key_version: Optional[str] = None
    new_key_version: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'rotation_id': self.rotation_id,
            'key_name': self.key_name,
            'algorithm': self.algorithm,
            'rotation_type': self.rotation_type.value,
            'status': self.status.value,
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error_message': self.error_message,
            'old_key_version': self.old_key_version,
            'new_key_version': self.new_key_version,
            'metadata': self.metadata
        }


class PQCKeyGenerator:
    """PQC key generation utilities."""
    
    @staticmethod
    def generate_keypair(algorithm: str = "Kyber768") -> tuple[bytes, bytes]:
        """Generate a new PQC keypair."""
        try:
            # Import PQC modules
            from pqc_secure_transfer import PQCKeyExchange
            
            kex = PQCKeyExchange(algorithm)
            public_key, private_key = kex.generate_keypair()
            
            logger.info(f"Generated new {algorithm} keypair")
            return public_key, private_key
            
        except ImportError:
            logger.error("PQC modules not available for key generation")
            raise
        except Exception as e:
            logger.error(f"Failed to generate {algorithm} keypair: {e}")
            raise
    
    @staticmethod
    def validate_keypair(public_key: bytes, private_key: bytes, algorithm: str = "Kyber768") -> bool:
        """Validate a PQC keypair."""
        try:
            from pqc_secure_transfer import PQCKeyExchange
            
            kex = PQCKeyExchange(algorithm)
            
            # Test encapsulation/decapsulation
            shared_secret, ciphertext = kex.encapsulate(public_key)
            decapsulated_secret = kex.decapsulate(ciphertext, private_key)
            
            is_valid = shared_secret == decapsulated_secret
            logger.info(f"Keypair validation {'passed' if is_valid else 'failed'} for {algorithm}")
            return is_valid
            
        except Exception as e:
            logger.error(f"Keypair validation failed for {algorithm}: {e}")
            return False


class KeyRotationManager:
    """Manages automated key rotation for PQC keys."""
    
    def __init__(self, secret_manager: UnifiedSecretManager):
        self.secret_manager = secret_manager
        self.rotation_policies: Dict[str, RotationPolicy] = {}
        self.rotation_history: List[RotationRecord] = []
        self.active_rotations: Dict[str, RotationRecord] = {}
        self.rotation_callbacks: List[Callable[[RotationRecord], None]] = []
        
        # Load default policies
        self._load_default_policies()
        
        logger.info("Key rotation manager initialized")
    
    def _load_default_policies(self):
        """Load default rotation policies for different algorithms."""
        algorithms = ["Kyber512", "Kyber768", "Kyber1024"]
        
        for algorithm in algorithms:
            # Environment-specific policies
            env = os.getenv('ENVIRONMENT', 'dev')
            
            if env == 'prod':
                rotation_days = 7  # Weekly rotation in production
                max_age_days = 14
                backup_retention = 90
            elif env == 'staging':
                rotation_days = 14  # Bi-weekly in staging
                max_age_days = 30
                backup_retention = 60
            else:
                rotation_days = 30  # Monthly in development
                max_age_days = 60
                backup_retention = 30
            
            policy = RotationPolicy(
                algorithm=algorithm,
                rotation_interval_days=rotation_days,
                max_key_age_days=max_age_days,
                backup_retention_days=backup_retention,
                enable_automatic_rotation=env != 'dev'  # Disable auto-rotation in dev
            )
            
            self.rotation_policies[algorithm] = policy
            logger.info(f"Loaded rotation policy for {algorithm}: {rotation_days} day interval")
    
    def set_rotation_policy(self, algorithm: str, policy: RotationPolicy):
        """Set rotation policy for an algorithm."""
        self.rotation_policies[algorithm] = policy
        logger.info(f"Updated rotation policy for {algorithm}")
    
    def add_rotation_callback(self, callback: Callable[[RotationRecord], None]):
        """Add callback to be called when rotation completes."""
        self.rotation_callbacks.append(callback)
    
    async def rotate_key(self, key_name: str, algorithm: str, 
                        rotation_type: RotationType = RotationType.MANUAL) -> RotationRecord:
        """Rotate a specific key."""
        rotation_id = f"rot_{key_name}_{int(datetime.utcnow().timestamp())}"
        
        rotation_record = RotationRecord(
            rotation_id=rotation_id,
            key_name=key_name,
            algorithm=algorithm,
            rotation_type=rotation_type,
            status=RotationStatus.PENDING,
            started_at=datetime.utcnow()
        )
        
        self.active_rotations[rotation_id] = rotation_record
        logger.info(f"Starting key rotation: {rotation_id}")
        
        try:
            # Update status to in progress
            rotation_record.status = RotationStatus.IN_PROGRESS
            
            # Get current key version (if exists)
            current_secret = await self.secret_manager.retrieve_secret(key_name)
            if current_secret:
                rotation_record.old_key_version = current_secret.metadata.version
            
            # Generate new keypair
            logger.info(f"Generating new {algorithm} keypair for {key_name}")
            public_key, private_key = PQCKeyGenerator.generate_keypair(algorithm)
            
            # Validate the new keypair
            if not PQCKeyGenerator.validate_keypair(public_key, private_key, algorithm):
                raise Exception("Generated keypair failed validation")
            
            # Store new private key
            private_key_name = f"{key_name}_private"
            success = await self.secret_manager.store_pqc_key(
                private_key_name, private_key, algorithm, "private"
            )
            
            if not success:
                raise Exception("Failed to store new private key")
            
            # Store new public key
            public_key_name = f"{key_name}_public"
            success = await self.secret_manager.store_pqc_key(
                public_key_name, public_key, algorithm, "public"
            )
            
            if not success:
                raise Exception("Failed to store new public key")
            
            # Update rotation record
            rotation_record.status = RotationStatus.COMPLETED
            rotation_record.completed_at = datetime.utcnow()
            
            # Get new key version
            new_secret = await self.secret_manager.retrieve_secret(private_key_name)
            if new_secret:
                rotation_record.new_key_version = new_secret.metadata.version
            
            logger.info(f"Key rotation completed successfully: {rotation_id}")
            
            # Record metrics
            record_key_rotation(algorithm, rotation_type.value)
            record_security_event("key_rotated", "info")
            
            # Notify callbacks
            for callback in self.rotation_callbacks:
                try:
                    callback(rotation_record)
                except Exception as e:
                    logger.error(f"Rotation callback failed: {e}")
            
        except Exception as e:
            logger.error(f"Key rotation failed: {rotation_id}: {e}")
            
            rotation_record.status = RotationStatus.FAILED
            rotation_record.error_message = str(e)
            rotation_record.completed_at = datetime.utcnow()
            
            record_security_event("key_rotation_failed", "error")
        
        finally:
            # Move from active to history
            if rotation_id in self.active_rotations:
                del self.active_rotations[rotation_id]
            self.rotation_history.append(rotation_record)
        
        return rotation_record
    
    async def check_rotation_schedule(self) -> List[str]:
        """Check which keys need rotation based on policies."""
        keys_needing_rotation = []
        
        try:
            # Get all PQC keys
            pqc_keys = await self.secret_manager.list_pqc_keys()
            
            for key_name in pqc_keys:
                if not key_name.endswith('_private'):
                    continue  # Only check private keys
                
                base_key_name = key_name.replace('_private', '')
                
                # Get key metadata
                secret = await self.secret_manager.retrieve_secret(key_name)
                if not secret:
                    continue
                
                # Determine algorithm from metadata or key name
                algorithm = secret.metadata.tags.get('pqc_algorithm', 'Kyber768')
                
                # Check if we have a policy for this algorithm
                if algorithm not in self.rotation_policies:
                    continue
                
                policy = self.rotation_policies[algorithm]
                
                # Check if automatic rotation is enabled
                if not policy.enable_automatic_rotation:
                    continue
                
                # Check if rotation is due
                last_rotation = secret.metadata.updated_at
                if policy.is_rotation_due(last_rotation):
                    keys_needing_rotation.append(base_key_name)
                    logger.info(f"Key {base_key_name} needs rotation (last rotated: {last_rotation})")
                
                # Check for emergency rotation
                elif policy.is_emergency_rotation_needed(last_rotation):
                    keys_needing_rotation.append(base_key_name)
                    logger.warning(f"Key {base_key_name} needs EMERGENCY rotation (age: {datetime.utcnow() - last_rotation})")
                    record_security_event("emergency_rotation_needed", "warning")
        
        except Exception as e:
            logger.error(f"Failed to check rotation schedule: {e}")
        
        return keys_needing_rotation
    
    async def perform_scheduled_rotations(self) -> List[RotationRecord]:
        """Perform all scheduled key rotations."""
        keys_to_rotate = await self.check_rotation_schedule()
        rotation_results = []
        
        for key_name in keys_to_rotate:
            try:
                # Determine algorithm for the key
                private_key_secret = await self.secret_manager.retrieve_secret(f"{key_name}_private")
                if not private_key_secret:
                    continue
                
                algorithm = private_key_secret.metadata.tags.get('pqc_algorithm', 'Kyber768')
                
                # Perform rotation
                result = await self.rotate_key(key_name, algorithm, RotationType.SCHEDULED)
                rotation_results.append(result)
                
                # Add delay between rotations to avoid overwhelming the system
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Failed to rotate key {key_name}: {e}")
        
        return rotation_results
    
    async def emergency_rotate_all_keys(self, reason: str = "Emergency rotation") -> List[RotationRecord]:
        """Perform emergency rotation of all PQC keys."""
        logger.warning(f"Emergency key rotation initiated: {reason}")
        record_security_event("emergency_rotation_initiated", "critical")
        
        pqc_keys = await self.secret_manager.list_pqc_keys()
        rotation_results = []
        
        for key_name in pqc_keys:
            if not key_name.endswith('_private'):
                continue
            
            base_key_name = key_name.replace('_private', '')
            
            try:
                # Get algorithm
                secret = await self.secret_manager.retrieve_secret(key_name)
                if not secret:
                    continue
                
                algorithm = secret.metadata.tags.get('pqc_algorithm', 'Kyber768')
                
                # Perform emergency rotation
                result = await self.rotate_key(base_key_name, algorithm, RotationType.EMERGENCY)
                result.metadata['emergency_reason'] = reason
                rotation_results.append(result)
                
            except Exception as e:
                logger.error(f"Emergency rotation failed for {base_key_name}: {e}")
        
        logger.info(f"Emergency rotation completed: {len(rotation_results)} keys processed")
        return rotation_results
    
    def get_rotation_history(self, key_name: Optional[str] = None, 
                           limit: int = 100) -> List[RotationRecord]:
        """Get rotation history."""
        history = self.rotation_history
        
        if key_name:
            history = [r for r in history if r.key_name == key_name]
        
        # Sort by start time, most recent first
        history.sort(key=lambda r: r.started_at, reverse=True)
        
        return history[:limit]
    
    def get_active_rotations(self) -> List[RotationRecord]:
        """Get currently active rotations."""
        return list(self.active_rotations.values())
    
    async def cleanup_old_key_versions(self, retention_days: int = 90):
        """Clean up old key versions based on retention policy."""
        logger.info(f"Starting cleanup of key versions older than {retention_days} days")
        
        try:
            pqc_keys = await self.secret_manager.list_pqc_keys()
            cleanup_count = 0
            
            for key_name in pqc_keys:
                # This would need to be implemented based on the specific secret manager
                # For now, we'll just log the intent
                logger.debug(f"Would cleanup old versions of {key_name}")
                cleanup_count += 1
            
            logger.info(f"Key cleanup completed: {cleanup_count} keys processed")
            record_security_event("key_cleanup_completed", "info")
            
        except Exception as e:
            logger.error(f"Key cleanup failed: {e}")
            record_security_event("key_cleanup_failed", "error")


class RotationScheduler:
    """Scheduler for automated key rotations."""
    
    def __init__(self, rotation_manager: KeyRotationManager):
        self.rotation_manager = rotation_manager
        self.running = False
        self.task: Optional[asyncio.Task] = None
        
    async def start(self, check_interval_hours: int = 6):
        """Start the rotation scheduler."""
        if self.running:
            logger.warning("Rotation scheduler is already running")
            return
        
        self.running = True
        self.task = asyncio.create_task(self._scheduler_loop(check_interval_hours))
        logger.info(f"Rotation scheduler started (check interval: {check_interval_hours} hours)")
    
    async def stop(self):
        """Stop the rotation scheduler."""
        if not self.running:
            return
        
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        logger.info("Rotation scheduler stopped")
    
    async def _scheduler_loop(self, check_interval_hours: int):
        """Main scheduler loop."""
        while self.running:
            try:
                logger.debug("Checking for scheduled key rotations")
                
                # Perform scheduled rotations
                results = await self.rotation_manager.perform_scheduled_rotations()
                
                if results:
                    logger.info(f"Completed {len(results)} scheduled rotations")
                
                # Update active key counts for metrics
                pqc_keys = await self.rotation_manager.secret_manager.list_pqc_keys()
                private_keys = [k for k in pqc_keys if k.endswith('_private')]
                public_keys = [k for k in pqc_keys if k.endswith('_public')]
                
                update_active_keys("Kyber768", "private", len(private_keys))
                update_active_keys("Kyber768", "public", len(public_keys))
                
                # Wait for next check
                await asyncio.sleep(check_interval_hours * 3600)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retrying


# Global instances
_rotation_manager: Optional[KeyRotationManager] = None
_rotation_scheduler: Optional[RotationScheduler] = None


def initialize_key_rotation(secret_manager: Optional[UnifiedSecretManager] = None) -> KeyRotationManager:
    """Initialize the global key rotation manager."""
    global _rotation_manager, _rotation_scheduler
    
    if not secret_manager:
        secret_manager = create_secret_manager()
    
    _rotation_manager = KeyRotationManager(secret_manager)
    _rotation_scheduler = RotationScheduler(_rotation_manager)
    
    logger.info("Key rotation system initialized")
    return _rotation_manager


def get_rotation_manager() -> Optional[KeyRotationManager]:
    """Get the global rotation manager."""
    return _rotation_manager


def get_rotation_scheduler() -> Optional[RotationScheduler]:
    """Get the global rotation scheduler."""
    return _rotation_scheduler


async def start_rotation_scheduler(check_interval_hours: int = 6):
    """Start the global rotation scheduler."""
    if _rotation_scheduler:
        await _rotation_scheduler.start(check_interval_hours)


async def stop_rotation_scheduler():
    """Stop the global rotation scheduler."""
    if _rotation_scheduler:
        await _rotation_scheduler.stop()