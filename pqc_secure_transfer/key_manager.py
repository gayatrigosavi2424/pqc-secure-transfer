"""
Key Management System for Post-Quantum Cryptography
Handles key generation, storage, rotation, and lifecycle management
"""

import os
import json
import time
import hashlib
from typing import Dict, Optional, Tuple, List
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64


class KeyManager:
    """
    Secure key management for PQC systems
    Handles key storage, rotation, and lifecycle management
    """
    
    def __init__(self, key_store_path: str = ".pqc_keys", master_password: Optional[str] = None):
        """
        Initialize key manager
        
        Args:
            key_store_path: Directory to store encrypted keys
            master_password: Master password for key encryption (if None, will prompt)
        """
        self.key_store_path = key_store_path
        self.master_password = master_password
        self.encryption_key = None
        self.key_cache = {}
        
        # Create key store directory
        os.makedirs(key_store_path, exist_ok=True)
        
        # Initialize master key
        self._initialize_master_key()
    
    def _initialize_master_key(self):
        """Initialize or load the master encryption key"""
        master_key_path = os.path.join(self.key_store_path, "master.key")
        
        if os.path.exists(master_key_path):
            # Load existing master key
            if not self.master_password:
                self.master_password = input("Enter master password: ")
            
            with open(master_key_path, 'rb') as f:
                encrypted_master = f.read()
            
            # Derive key from password
            salt = encrypted_master[:16]  # First 16 bytes are salt
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            password_key = base64.urlsafe_b64encode(kdf.derive(self.master_password.encode()))
            
            # Decrypt master key
            f = Fernet(password_key)
            try:
                self.encryption_key = f.decrypt(encrypted_master[16:])
            except Exception:
                raise ValueError("Invalid master password")
        else:
            # Create new master key
            if not self.master_password:
                self.master_password = input("Create master password: ")
            
            # Generate new master key
            self.encryption_key = Fernet.generate_key()
            
            # Encrypt master key with password
            salt = os.urandom(16)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            password_key = base64.urlsafe_b64encode(kdf.derive(self.master_password.encode()))
            
            f = Fernet(password_key)
            encrypted_master = f.encrypt(self.encryption_key)
            
            # Save encrypted master key
            with open(master_key_path, 'wb') as f:
                f.write(salt + encrypted_master)
    
    def store_keypair(self, key_id: str, public_key: bytes, private_key: bytes, 
                     algorithm: str, metadata: Optional[Dict] = None) -> bool:
        """
        Store a keypair securely
        
        Args:
            key_id: Unique identifier for the keypair
            public_key: Public key bytes
            private_key: Private key bytes
            algorithm: Algorithm name (e.g., "Kyber768")
            metadata: Optional metadata
            
        Returns:
            True if stored successfully
        """
        try:
            key_data = {
                "key_id": key_id,
                "algorithm": algorithm,
                "public_key": base64.b64encode(public_key).decode(),
                "private_key": base64.b64encode(private_key).decode(),
                "created_at": time.time(),
                "metadata": metadata or {}
            }
            
            # Encrypt key data
            f = Fernet(self.encryption_key)
            encrypted_data = f.encrypt(json.dumps(key_data).encode())
            
            # Store encrypted key
            key_file_path = os.path.join(self.key_store_path, f"{key_id}.key")
            with open(key_file_path, 'wb') as f:
                f.write(encrypted_data)
            
            # Cache the key
            self.key_cache[key_id] = key_data
            
            return True
            
        except Exception as e:
            print(f"Error storing keypair {key_id}: {e}")
            return False
    
    def load_keypair(self, key_id: str) -> Optional[Tuple[bytes, bytes, str]]:
        """
        Load a keypair
        
        Args:
            key_id: Key identifier
            
        Returns:
            Tuple of (public_key, private_key, algorithm) or None if not found
        """
        # Check cache first
        if key_id in self.key_cache:
            key_data = self.key_cache[key_id]
        else:
            # Load from disk
            key_file_path = os.path.join(self.key_store_path, f"{key_id}.key")
            if not os.path.exists(key_file_path):
                return None
            
            try:
                with open(key_file_path, 'rb') as f:
                    encrypted_data = f.read()
                
                # Decrypt key data
                f = Fernet(self.encryption_key)
                decrypted_data = f.decrypt(encrypted_data)
                key_data = json.loads(decrypted_data.decode())
                
                # Cache the key
                self.key_cache[key_id] = key_data
                
            except Exception as e:
                print(f"Error loading keypair {key_id}: {e}")
                return None
        
        # Extract key components
        public_key = base64.b64decode(key_data["public_key"])
        private_key = base64.b64decode(key_data["private_key"])
        algorithm = key_data["algorithm"]
        
        return public_key, private_key, algorithm
    
    def list_keys(self) -> List[Dict]:
        """
        List all stored keys with metadata
        
        Returns:
            List of key metadata dictionaries
        """
        keys = []
        
        for filename in os.listdir(self.key_store_path):
            if filename.endswith('.key') and filename != 'master.key':
                key_id = filename[:-4]  # Remove .key extension
                
                try:
                    key_data = self.load_keypair(key_id)
                    if key_data:
                        # Get metadata from cache
                        if key_id in self.key_cache:
                            metadata = self.key_cache[key_id]
                            keys.append({
                                "key_id": key_id,
                                "algorithm": metadata["algorithm"],
                                "created_at": metadata["created_at"],
                                "metadata": metadata.get("metadata", {})
                            })
                except Exception:
                    continue
        
        return keys
    
    def delete_key(self, key_id: str) -> bool:
        """
        Delete a stored key
        
        Args:
            key_id: Key identifier
            
        Returns:
            True if deleted successfully
        """
        try:
            key_file_path = os.path.join(self.key_store_path, f"{key_id}.key")
            if os.path.exists(key_file_path):
                os.remove(key_file_path)
            
            # Remove from cache
            if key_id in self.key_cache:
                del self.key_cache[key_id]
            
            return True
            
        except Exception as e:
            print(f"Error deleting key {key_id}: {e}")
            return False
    
    def rotate_keys(self, key_id: str, new_algorithm: Optional[str] = None) -> Optional[str]:
        """
        Rotate a keypair (generate new keys, keep old ones for transition)
        
        Args:
            key_id: Original key identifier
            new_algorithm: New algorithm to use (if different)
            
        Returns:
            New key ID or None if failed
        """
        try:
            # Load existing key
            existing_key = self.load_keypair(key_id)
            if not existing_key:
                return None
            
            _, _, old_algorithm = existing_key
            algorithm = new_algorithm or old_algorithm
            
            # Generate new keypair
            from .hybrid_crypto import HybridCrypto
            crypto = HybridCrypto(algorithm)
            new_public, new_private = crypto.generate_keypair()
            
            # Create new key ID
            new_key_id = f"{key_id}_rotated_{int(time.time())}"
            
            # Store new keypair
            metadata = {
                "rotated_from": key_id,
                "rotation_time": time.time()
            }
            
            if self.store_keypair(new_key_id, new_public, new_private, algorithm, metadata):
                return new_key_id
            else:
                return None
                
        except Exception as e:
            print(f"Error rotating key {key_id}: {e}")
            return None
    
    def export_public_key(self, key_id: str, format: str = "pem") -> Optional[str]:
        """
        Export public key in specified format
        
        Args:
            key_id: Key identifier
            format: Export format ("pem", "der", "raw")
            
        Returns:
            Exported key string or None if failed
        """
        key_data = self.load_keypair(key_id)
        if not key_data:
            return None
        
        public_key, _, algorithm = key_data
        
        if format == "raw":
            return base64.b64encode(public_key).decode()
        elif format == "pem":
            # Create PEM-like format for PQC keys
            b64_key = base64.b64encode(public_key).decode()
            return f"-----BEGIN {algorithm.upper()} PUBLIC KEY-----\n{b64_key}\n-----END {algorithm.upper()} PUBLIC KEY-----"
        elif format == "der":
            return public_key.hex()
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def import_public_key(self, key_data: str, key_id: str, algorithm: str, format: str = "pem") -> bool:
        """
        Import a public key
        
        Args:
            key_data: Key data string
            key_id: Key identifier
            algorithm: Algorithm name
            format: Import format ("pem", "der", "raw")
            
        Returns:
            True if imported successfully
        """
        try:
            if format == "raw":
                public_key = base64.b64decode(key_data)
            elif format == "pem":
                # Extract key from PEM format
                lines = key_data.strip().split('\n')
                b64_data = ''.join(line for line in lines if not line.startswith('-----'))
                public_key = base64.b64decode(b64_data)
            elif format == "der":
                public_key = bytes.fromhex(key_data)
            else:
                raise ValueError(f"Unsupported format: {format}")
            
            # Store as public-only key (no private key)
            metadata = {"imported": True, "public_only": True}
            return self.store_keypair(key_id, public_key, b"", algorithm, metadata)
            
        except Exception as e:
            print(f"Error importing public key: {e}")
            return False
    
    def get_key_fingerprint(self, key_id: str) -> Optional[str]:
        """
        Get fingerprint of a key
        
        Args:
            key_id: Key identifier
            
        Returns:
            SHA256 fingerprint of the public key
        """
        key_data = self.load_keypair(key_id)
        if not key_data:
            return None
        
        public_key, _, _ = key_data
        fingerprint = hashlib.sha256(public_key).hexdigest()
        return fingerprint
    
    def cleanup_old_keys(self, max_age_days: int = 30) -> int:
        """
        Clean up old keys based on age
        
        Args:
            max_age_days: Maximum age in days
            
        Returns:
            Number of keys deleted
        """
        current_time = time.time()
        max_age_seconds = max_age_days * 24 * 3600
        deleted_count = 0
        
        keys = self.list_keys()
        for key_info in keys:
            key_age = current_time - key_info["created_at"]
            if key_age > max_age_seconds:
                if self.delete_key(key_info["key_id"]):
                    deleted_count += 1
                    print(f"Deleted old key: {key_info['key_id']}")
        
        return deleted_count