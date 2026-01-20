"""
Cloud-native secret management system for PQC Secure Transfer.
Provides unified interface for AWS Secrets Manager, GCP Secret Manager, and Azure Key Vault.
"""

import os
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Optional, List, Any, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio
import base64

# Cloud provider imports (with fallbacks for missing dependencies)
try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    AWS_AVAILABLE = True
except ImportError:
    AWS_AVAILABLE = False

try:
    from google.cloud import secretmanager
    from google.api_core import exceptions as gcp_exceptions
    GCP_AVAILABLE = True
except ImportError:
    GCP_AVAILABLE = False

try:
    from azure.keyvault.secrets import SecretClient
    from azure.identity import DefaultAzureCredential
    from azure.core.exceptions import AzureError
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False

from monitoring.pqc_metrics_integration import record_security_event

logger = logging.getLogger(__name__)


@dataclass
class SecretMetadata:
    """Metadata for a secret."""
    name: str
    version: str
    created_at: datetime
    updated_at: datetime
    rotation_schedule: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    description: Optional[str] = None


@dataclass
class SecretValue:
    """Container for secret value and metadata."""
    value: Union[str, bytes]
    metadata: SecretMetadata
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'value': base64.b64encode(self.value if isinstance(self.value, bytes) else self.value.encode()).decode(),
            'metadata': {
                'name': self.metadata.name,
                'version': self.metadata.version,
                'created_at': self.metadata.created_at.isoformat(),
                'updated_at': self.metadata.updated_at.isoformat(),
                'rotation_schedule': self.metadata.rotation_schedule,
                'tags': self.metadata.tags,
                'description': self.metadata.description
            }
        }


class SecretManagerInterface(ABC):
    """Abstract interface for secret management operations."""
    
    @abstractmethod
    async def store_secret(self, name: str, value: Union[str, bytes], 
                          metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Store a secret."""
        pass
    
    @abstractmethod
    async def retrieve_secret(self, name: str, version: Optional[str] = None) -> Optional[SecretValue]:
        """Retrieve a secret."""
        pass
    
    @abstractmethod
    async def update_secret(self, name: str, value: Union[str, bytes]) -> bool:
        """Update an existing secret."""
        pass
    
    @abstractmethod
    async def delete_secret(self, name: str) -> bool:
        """Delete a secret."""
        pass
    
    @abstractmethod
    async def list_secrets(self, prefix: Optional[str] = None) -> List[str]:
        """List available secrets."""
        pass
    
    @abstractmethod
    async def rotate_secret(self, name: str, new_value: Union[str, bytes]) -> bool:
        """Rotate a secret to a new value."""
        pass


class AWSSecretsManager(SecretManagerInterface):
    """AWS Secrets Manager implementation."""
    
    def __init__(self, region: str = "us-west-2"):
        if not AWS_AVAILABLE:
            raise ImportError("AWS SDK (boto3) not available")
        
        self.region = region
        self.client = boto3.client('secretsmanager', region_name=region)
        logger.info(f"Initialized AWS Secrets Manager in region {region}")
    
    async def store_secret(self, name: str, value: Union[str, bytes], 
                          metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Store a secret in AWS Secrets Manager."""
        try:
            secret_value = value if isinstance(value, str) else base64.b64encode(value).decode()
            
            # Prepare secret data
            secret_data = {
                'Name': name,
                'SecretString': secret_value
            }
            
            if metadata:
                secret_data['Description'] = metadata.get('description', f'PQC secret: {name}')
                if 'tags' in metadata:
                    secret_data['Tags'] = [
                        {'Key': k, 'Value': v} for k, v in metadata['tags'].items()
                    ]
            
            # Try to create the secret
            try:
                self.client.create_secret(**secret_data)
                logger.info(f"Created new secret: {name}")
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceExistsException':
                    # Secret exists, update it instead
                    await self.update_secret(name, value)
                    logger.info(f"Updated existing secret: {name}")
                else:
                    raise
            
            record_security_event("secret_stored", "info")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store secret {name}: {e}")
            record_security_event("secret_store_failed", "error")
            return False
    
    async def retrieve_secret(self, name: str, version: Optional[str] = None) -> Optional[SecretValue]:
        """Retrieve a secret from AWS Secrets Manager."""
        try:
            params = {'SecretId': name}
            if version:
                params['VersionId'] = version
            
            response = self.client.get_secret_value(**params)
            
            # Extract secret value
            secret_value = response.get('SecretString', '')
            if not secret_value and 'SecretBinary' in response:
                secret_value = base64.b64decode(response['SecretBinary'])
            
            # Create metadata
            metadata = SecretMetadata(
                name=name,
                version=response.get('VersionId', 'AWSCURRENT'),
                created_at=response.get('CreatedDate', datetime.now()),
                updated_at=response.get('CreatedDate', datetime.now()),
                description=response.get('Description')
            )
            
            record_security_event("secret_retrieved", "info")
            return SecretValue(value=secret_value, metadata=metadata)
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                logger.warning(f"Secret not found: {name}")
            else:
                logger.error(f"Failed to retrieve secret {name}: {e}")
                record_security_event("secret_retrieve_failed", "error")
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve secret {name}: {e}")
            record_security_event("secret_retrieve_failed", "error")
            return None
    
    async def update_secret(self, name: str, value: Union[str, bytes]) -> bool:
        """Update an existing secret."""
        try:
            secret_value = value if isinstance(value, str) else base64.b64encode(value).decode()
            
            self.client.update_secret(
                SecretId=name,
                SecretString=secret_value
            )
            
            logger.info(f"Updated secret: {name}")
            record_security_event("secret_updated", "info")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update secret {name}: {e}")
            record_security_event("secret_update_failed", "error")
            return False
    
    async def delete_secret(self, name: str) -> bool:
        """Delete a secret."""
        try:
            self.client.delete_secret(
                SecretId=name,
                ForceDeleteWithoutRecovery=False  # Allow recovery for 30 days
            )
            
            logger.info(f"Deleted secret: {name}")
            record_security_event("secret_deleted", "warning")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete secret {name}: {e}")
            record_security_event("secret_delete_failed", "error")
            return False
    
    async def list_secrets(self, prefix: Optional[str] = None) -> List[str]:
        """List available secrets."""
        try:
            paginator = self.client.get_paginator('list_secrets')
            secrets = []
            
            for page in paginator.paginate():
                for secret in page['SecretList']:
                    secret_name = secret['Name']
                    if not prefix or secret_name.startswith(prefix):
                        secrets.append(secret_name)
            
            return secrets
            
        except Exception as e:
            logger.error(f"Failed to list secrets: {e}")
            return []
    
    async def rotate_secret(self, name: str, new_value: Union[str, bytes]) -> bool:
        """Rotate a secret to a new value."""
        try:
            # AWS Secrets Manager has built-in rotation, but we'll implement manual rotation
            success = await self.update_secret(name, new_value)
            if success:
                record_security_event("secret_rotated", "info")
            return success
            
        except Exception as e:
            logger.error(f"Failed to rotate secret {name}: {e}")
            record_security_event("secret_rotation_failed", "error")
            return False


class GCPSecretManager(SecretManagerInterface):
    """Google Cloud Secret Manager implementation."""
    
    def __init__(self, project_id: str):
        if not GCP_AVAILABLE:
            raise ImportError("Google Cloud SDK not available")
        
        self.project_id = project_id
        self.client = secretmanager.SecretManagerServiceClient()
        self.parent = f"projects/{project_id}"
        logger.info(f"Initialized GCP Secret Manager for project {project_id}")
    
    async def store_secret(self, name: str, value: Union[str, bytes], 
                          metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Store a secret in GCP Secret Manager."""
        try:
            secret_id = f"{self.parent}/secrets/{name}"
            
            # Create secret if it doesn't exist
            try:
                secret = {
                    'replication': {'automatic': {}}
                }
                if metadata and 'labels' in metadata:
                    secret['labels'] = metadata['labels']
                
                self.client.create_secret(
                    request={
                        'parent': self.parent,
                        'secret_id': name,
                        'secret': secret
                    }
                )
                logger.info(f"Created new secret: {name}")
            except gcp_exceptions.AlreadyExists:
                logger.info(f"Secret already exists: {name}")
            
            # Add secret version
            secret_value = value if isinstance(value, bytes) else value.encode()
            
            self.client.add_secret_version(
                request={
                    'parent': secret_id,
                    'payload': {'data': secret_value}
                }
            )
            
            record_security_event("secret_stored", "info")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store secret {name}: {e}")
            record_security_event("secret_store_failed", "error")
            return False
    
    async def retrieve_secret(self, name: str, version: Optional[str] = None) -> Optional[SecretValue]:
        """Retrieve a secret from GCP Secret Manager."""
        try:
            version_name = f"{self.parent}/secrets/{name}/versions/{version or 'latest'}"
            
            response = self.client.access_secret_version(request={'name': version_name})
            
            secret_value = response.payload.data
            
            # Get secret metadata
            secret_info = self.client.get_secret(request={'name': f"{self.parent}/secrets/{name}"})
            
            metadata = SecretMetadata(
                name=name,
                version=response.name.split('/')[-1],
                created_at=secret_info.create_time,
                updated_at=secret_info.create_time,
                tags=dict(secret_info.labels) if secret_info.labels else {}
            )
            
            record_security_event("secret_retrieved", "info")
            return SecretValue(value=secret_value, metadata=metadata)
            
        except gcp_exceptions.NotFound:
            logger.warning(f"Secret not found: {name}")
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve secret {name}: {e}")
            record_security_event("secret_retrieve_failed", "error")
            return None
    
    async def update_secret(self, name: str, value: Union[str, bytes]) -> bool:
        """Update a secret by adding a new version."""
        try:
            secret_id = f"{self.parent}/secrets/{name}"
            secret_value = value if isinstance(value, bytes) else value.encode()
            
            self.client.add_secret_version(
                request={
                    'parent': secret_id,
                    'payload': {'data': secret_value}
                }
            )
            
            logger.info(f"Updated secret: {name}")
            record_security_event("secret_updated", "info")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update secret {name}: {e}")
            record_security_event("secret_update_failed", "error")
            return False
    
    async def delete_secret(self, name: str) -> bool:
        """Delete a secret."""
        try:
            secret_id = f"{self.parent}/secrets/{name}"
            
            self.client.delete_secret(request={'name': secret_id})
            
            logger.info(f"Deleted secret: {name}")
            record_security_event("secret_deleted", "warning")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete secret {name}: {e}")
            record_security_event("secret_delete_failed", "error")
            return False
    
    async def list_secrets(self, prefix: Optional[str] = None) -> List[str]:
        """List available secrets."""
        try:
            secrets = []
            
            for secret in self.client.list_secrets(request={'parent': self.parent}):
                secret_name = secret.name.split('/')[-1]
                if not prefix or secret_name.startswith(prefix):
                    secrets.append(secret_name)
            
            return secrets
            
        except Exception as e:
            logger.error(f"Failed to list secrets: {e}")
            return []
    
    async def rotate_secret(self, name: str, new_value: Union[str, bytes]) -> bool:
        """Rotate a secret to a new value."""
        try:
            success = await self.update_secret(name, new_value)
            if success:
                record_security_event("secret_rotated", "info")
            return success
            
        except Exception as e:
            logger.error(f"Failed to rotate secret {name}: {e}")
            record_security_event("secret_rotation_failed", "error")
            return False


class AzureKeyVault(SecretManagerInterface):
    """Azure Key Vault implementation."""
    
    def __init__(self, vault_url: str):
        if not AZURE_AVAILABLE:
            raise ImportError("Azure SDK not available")
        
        self.vault_url = vault_url
        self.client = SecretClient(vault_url=vault_url, credential=DefaultAzureCredential())
        logger.info(f"Initialized Azure Key Vault: {vault_url}")
    
    async def store_secret(self, name: str, value: Union[str, bytes], 
                          metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Store a secret in Azure Key Vault."""
        try:
            secret_value = value if isinstance(value, str) else base64.b64encode(value).decode()
            
            properties = {}
            if metadata:
                if 'tags' in metadata:
                    properties['tags'] = metadata['tags']
                if 'content_type' in metadata:
                    properties['content_type'] = metadata['content_type']
            
            self.client.set_secret(name, secret_value, **properties)
            
            logger.info(f"Stored secret: {name}")
            record_security_event("secret_stored", "info")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store secret {name}: {e}")
            record_security_event("secret_store_failed", "error")
            return False
    
    async def retrieve_secret(self, name: str, version: Optional[str] = None) -> Optional[SecretValue]:
        """Retrieve a secret from Azure Key Vault."""
        try:
            if version:
                secret = self.client.get_secret(name, version)
            else:
                secret = self.client.get_secret(name)
            
            metadata = SecretMetadata(
                name=name,
                version=secret.properties.version,
                created_at=secret.properties.created_on,
                updated_at=secret.properties.updated_on,
                tags=dict(secret.properties.tags) if secret.properties.tags else {}
            )
            
            record_security_event("secret_retrieved", "info")
            return SecretValue(value=secret.value, metadata=metadata)
            
        except Exception as e:
            logger.error(f"Failed to retrieve secret {name}: {e}")
            record_security_event("secret_retrieve_failed", "error")
            return None
    
    async def update_secret(self, name: str, value: Union[str, bytes]) -> bool:
        """Update an existing secret."""
        try:
            secret_value = value if isinstance(value, str) else base64.b64encode(value).decode()
            
            self.client.set_secret(name, secret_value)
            
            logger.info(f"Updated secret: {name}")
            record_security_event("secret_updated", "info")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update secret {name}: {e}")
            record_security_event("secret_update_failed", "error")
            return False
    
    async def delete_secret(self, name: str) -> bool:
        """Delete a secret."""
        try:
            delete_operation = self.client.begin_delete_secret(name)
            delete_operation.wait()
            
            logger.info(f"Deleted secret: {name}")
            record_security_event("secret_deleted", "warning")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete secret {name}: {e}")
            record_security_event("secret_delete_failed", "error")
            return False
    
    async def list_secrets(self, prefix: Optional[str] = None) -> List[str]:
        """List available secrets."""
        try:
            secrets = []
            
            for secret_properties in self.client.list_properties_of_secrets():
                secret_name = secret_properties.name
                if not prefix or secret_name.startswith(prefix):
                    secrets.append(secret_name)
            
            return secrets
            
        except Exception as e:
            logger.error(f"Failed to list secrets: {e}")
            return []
    
    async def rotate_secret(self, name: str, new_value: Union[str, bytes]) -> bool:
        """Rotate a secret to a new value."""
        try:
            success = await self.update_secret(name, new_value)
            if success:
                record_security_event("secret_rotated", "info")
            return success
            
        except Exception as e:
            logger.error(f"Failed to rotate secret {name}: {e}")
            record_security_event("secret_rotation_failed", "error")
            return False


class UnifiedSecretManager:
    """Unified secret manager that provides a single interface across cloud providers."""
    
    def __init__(self, provider: str, **kwargs):
        self.provider = provider.lower()
        self.backend: SecretManagerInterface
        
        if self.provider == "aws":
            region = kwargs.get('region', 'us-west-2')
            self.backend = AWSSecretsManager(region=region)
        elif self.provider == "gcp":
            project_id = kwargs.get('project_id')
            if not project_id:
                raise ValueError("project_id required for GCP Secret Manager")
            self.backend = GCPSecretManager(project_id=project_id)
        elif self.provider == "azure":
            vault_url = kwargs.get('vault_url')
            if not vault_url:
                raise ValueError("vault_url required for Azure Key Vault")
            self.backend = AzureKeyVault(vault_url=vault_url)
        else:
            raise ValueError(f"Unsupported provider: {provider}")
        
        logger.info(f"Initialized unified secret manager with {provider} backend")
    
    async def store_pqc_key(self, key_name: str, key_data: bytes, 
                           algorithm: str = "Kyber768", key_type: str = "private") -> bool:
        """Store a PQC key with appropriate metadata."""
        metadata = {
            'description': f'PQC {key_type} key for {algorithm}',
            'tags': {
                'pqc_algorithm': algorithm,
                'key_type': key_type,
                'created_by': 'pqc-secure-transfer',
                'rotation_schedule': 'monthly'
            },
            'content_type': 'application/octet-stream'
        }
        
        return await self.backend.store_secret(key_name, key_data, metadata)
    
    async def retrieve_pqc_key(self, key_name: str, version: Optional[str] = None) -> Optional[bytes]:
        """Retrieve a PQC key."""
        secret_value = await self.backend.retrieve_secret(key_name, version)
        if secret_value:
            if isinstance(secret_value.value, str):
                return base64.b64decode(secret_value.value)
            return secret_value.value
        return None
    
    async def rotate_pqc_key(self, key_name: str, new_key_data: bytes) -> bool:
        """Rotate a PQC key."""
        return await self.backend.rotate_secret(key_name, new_key_data)
    
    async def list_pqc_keys(self) -> List[str]:
        """List all PQC keys."""
        return await self.backend.list_secrets(prefix="pqc-")
    
    # Delegate all other methods to the backend
    async def store_secret(self, name: str, value: Union[str, bytes], 
                          metadata: Optional[Dict[str, Any]] = None) -> bool:
        return await self.backend.store_secret(name, value, metadata)
    
    async def retrieve_secret(self, name: str, version: Optional[str] = None) -> Optional[SecretValue]:
        return await self.backend.retrieve_secret(name, version)
    
    async def update_secret(self, name: str, value: Union[str, bytes]) -> bool:
        return await self.backend.update_secret(name, value)
    
    async def delete_secret(self, name: str) -> bool:
        return await self.backend.delete_secret(name)
    
    async def list_secrets(self, prefix: Optional[str] = None) -> List[str]:
        return await self.backend.list_secrets(prefix)
    
    async def rotate_secret(self, name: str, new_value: Union[str, bytes]) -> bool:
        return await self.backend.rotate_secret(name, new_value)


def create_secret_manager(provider: str = None, **kwargs) -> UnifiedSecretManager:
    """Factory function to create a secret manager based on environment or explicit provider."""
    
    # Auto-detect provider if not specified
    if not provider:
        if os.getenv('AWS_REGION') or os.getenv('AWS_DEFAULT_REGION'):
            provider = 'aws'
        elif os.getenv('GOOGLE_CLOUD_PROJECT') or os.getenv('GCP_PROJECT'):
            provider = 'gcp'
        elif os.getenv('AZURE_KEY_VAULT_URL'):
            provider = 'azure'
        else:
            provider = 'aws'  # Default fallback
    
    # Auto-populate kwargs from environment
    if provider == 'aws':
        kwargs.setdefault('region', os.getenv('AWS_REGION', 'us-west-2'))
    elif provider == 'gcp':
        kwargs.setdefault('project_id', os.getenv('GOOGLE_CLOUD_PROJECT') or os.getenv('GCP_PROJECT'))
    elif provider == 'azure':
        kwargs.setdefault('vault_url', os.getenv('AZURE_KEY_VAULT_URL'))
    
    return UnifiedSecretManager(provider, **kwargs)