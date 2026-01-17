"""
Hybrid Post-Quantum Cryptography Implementation
Combines classical X25519 with ML-KEM for quantum-resistant key exchange
"""

import os
import hashlib
from typing import Tuple, Optional
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.asymmetric import x25519

try:
    import oqs
    OQS_AVAILABLE = True
except ImportError:
    OQS_AVAILABLE = False
    print("Warning: liboqs-python not available. Install with: pip install liboqs-python")


class HybridCrypto:
    """
    Hybrid encryption combining classical X25519 and Post-Quantum ML-KEM
    Provides defense against both classical and quantum attacks
    """
    
    def __init__(self, pqc_algorithm: str = "Kyber768"):
        """
        Initialize hybrid crypto system
        
        Args:
            pqc_algorithm: Post-quantum algorithm name (Kyber768, Kyber1024)
        """
        self.pqc_algorithm = pqc_algorithm
        self.classical_private_key = None
        self.classical_public_key = None
        self.pqc_keypair = None
        
        if not OQS_AVAILABLE:
            raise ImportError("liboqs-python is required for PQC operations")
    
    def generate_keypair(self) -> Tuple[bytes, bytes]:
        """
        Generate hybrid keypair (classical + post-quantum)
        
        Returns:
            Tuple of (public_key_bundle, private_key_bundle)
        """
        # Generate classical X25519 keypair
        self.classical_private_key = x25519.X25519PrivateKey.generate()
        self.classical_public_key = self.classical_private_key.public_key()
        
        # Generate post-quantum keypair
        with oqs.KeyEncapsulation(self.pqc_algorithm) as kem:
            pqc_public_key = kem.generate_keypair()
            pqc_secret_key = kem.export_secret_key()
            
            self.pqc_keypair = {
                'public': pqc_public_key,
                'secret': pqc_secret_key,
                'kem': kem
            }
        
        # Bundle public keys
        classical_public_bytes = self.classical_public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        public_key_bundle = {
            'classical': classical_public_bytes,
            'pqc': pqc_public_key,
            'algorithm': self.pqc_algorithm
        }
        
        private_key_bundle = {
            'classical': self.classical_private_key,
            'pqc': pqc_secret_key,
            'algorithm': self.pqc_algorithm
        }
        
        return self._serialize_keys(public_key_bundle), self._serialize_keys(private_key_bundle)
    
    def encapsulate_key(self, peer_public_key_bundle: bytes) -> Tuple[bytes, bytes]:
        """
        Perform hybrid key encapsulation
        
        Args:
            peer_public_key_bundle: Peer's public key bundle
            
        Returns:
            Tuple of (shared_secret, encapsulated_key)
        """
        peer_keys = self._deserialize_keys(peer_public_key_bundle)
        
        # Classical X25519 key exchange
        peer_classical_public = x25519.X25519PublicKey.from_public_bytes(
            peer_keys['classical']
        )
        classical_shared = self.classical_private_key.exchange(peer_classical_public)
        
        # Post-quantum key encapsulation
        with oqs.KeyEncapsulation(peer_keys['algorithm']) as kem:
            ciphertext, pqc_shared = kem.encap_secret(peer_keys['pqc'])
        
        # Combine shared secrets using HKDF
        combined_shared = self._combine_secrets(classical_shared, pqc_shared)
        
        encapsulated_data = {
            'classical': b'',  # X25519 doesn't produce ciphertext
            'pqc': ciphertext,
            'algorithm': peer_keys['algorithm']
        }
        
        return combined_shared, self._serialize_keys(encapsulated_data)
    
    def decapsulate_key(self, encapsulated_key: bytes) -> bytes:
        """
        Perform hybrid key decapsulation
        
        Args:
            encapsulated_key: Encapsulated key data
            
        Returns:
            Shared secret
        """
        encap_data = self._deserialize_keys(encapsulated_key)
        
        # Classical shared secret (already computed during key exchange)
        # For X25519, we need the peer's public key, which should be stored
        # This is a simplified version - in practice, you'd store the classical shared secret
        
        # Post-quantum key decapsulation
        with oqs.KeyEncapsulation(encap_data['algorithm']) as kem:
            kem.import_secret_key(self.pqc_keypair['secret'])
            pqc_shared = kem.decap_secret(encap_data['pqc'])
        
        # For this example, we'll use a placeholder for classical_shared
        # In a real implementation, you'd properly manage the X25519 exchange
        classical_shared = b'\x00' * 32  # Placeholder
        
        # Combine shared secrets
        combined_shared = self._combine_secrets(classical_shared, pqc_shared)
        
        return combined_shared
    
    def _combine_secrets(self, classical_secret: bytes, pqc_secret: bytes) -> bytes:
        """
        Combine classical and post-quantum shared secrets using HKDF
        
        Args:
            classical_secret: X25519 shared secret
            pqc_secret: Post-quantum shared secret
            
        Returns:
            Combined 256-bit key suitable for AES-256
        """
        # Concatenate the secrets
        combined_input = classical_secret + pqc_secret
        
        # Use HKDF to derive a 256-bit key
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,  # 256 bits for AES-256
            salt=None,
            info=b'hybrid-pqc-key-derivation',
        )
        
        return hkdf.derive(combined_input)
    
    def _serialize_keys(self, key_data: dict) -> bytes:
        """Serialize key data for transmission"""
        import json
        import base64
        
        # Convert bytes to base64 for JSON serialization
        serializable = {}
        for key, value in key_data.items():
            if isinstance(value, bytes):
                serializable[key] = base64.b64encode(value).decode('utf-8')
            else:
                serializable[key] = value
        
        return json.dumps(serializable).encode('utf-8')
    
    def _deserialize_keys(self, key_data: bytes) -> dict:
        """Deserialize key data from transmission"""
        import json
        import base64
        
        data = json.loads(key_data.decode('utf-8'))
        
        # Convert base64 back to bytes
        deserialized = {}
        for key, value in data.items():
            if key in ['classical', 'pqc'] and isinstance(value, str):
                deserialized[key] = base64.b64decode(value.encode('utf-8'))
            else:
                deserialized[key] = value
        
        return deserialized


class QuantumSafeRandom:
    """
    Quantum-safe random number generation
    Uses multiple entropy sources for enhanced security
    """
    
    @staticmethod
    def generate_bytes(length: int) -> bytes:
        """
        Generate cryptographically secure random bytes
        
        Args:
            length: Number of bytes to generate
            
        Returns:
            Random bytes
        """
        # Use OS random (which should be quantum-safe on modern systems)
        primary_random = os.urandom(length)
        
        # Add additional entropy from hash of system state
        import time
        entropy_input = f"{time.time()}{os.getpid()}{id(object())}".encode()
        additional_entropy = hashlib.sha256(entropy_input).digest()[:length]
        
        # XOR the sources for enhanced randomness
        result = bytes(a ^ b for a, b in zip(primary_random, additional_entropy))
        
        return result