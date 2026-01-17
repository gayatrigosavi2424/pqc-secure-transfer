#!/usr/bin/env python3
"""
Basic usage example of the PQC Secure Transfer System
Demonstrates hybrid encryption for large files
"""

import os
import sys
import asyncio
import tempfile

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pqc_secure_transfer import HybridCrypto, StreamingEncryptor, KeyManager


def create_test_file(size_mb: int = 100) -> str:
    """Create a test file of specified size"""
    test_file = tempfile.NamedTemporaryFile(delete=False, suffix='.dat')
    
    print(f"Creating {size_mb}MB test file...")
    chunk_size = 1024 * 1024  # 1MB chunks
    data_chunk = os.urandom(chunk_size)
    
    for i in range(size_mb):
        test_file.write(data_chunk)
        if i % 10 == 0:
            print(f"  Written {i+1}/{size_mb} MB")
    
    test_file.close()
    print(f"Test file created: {test_file.name}")
    return test_file.name


def demo_hybrid_crypto():
    """Demonstrate hybrid cryptography key exchange"""
    print("\n=== Hybrid Cryptography Demo ===")
    
    # Create two parties
    alice = HybridCrypto("Kyber768")
    bob = HybridCrypto("Kyber768")
    
    # Generate keypairs
    print("Generating keypairs...")
    alice_public, alice_private = alice.generate_keypair()
    bob_public, bob_private = bob.generate_keypair()
    
    print(f"Alice public key size: {len(alice_public)} bytes")
    print(f"Bob public key size: {len(bob_public)} bytes")
    
    # Key exchange
    print("Performing key exchange...")
    alice_shared, alice_encap = alice.encapsulate_key(bob_public)
    bob_shared = bob.decapsulate_key(alice_encap)
    
    print(f"Alice shared secret: {alice_shared[:16].hex()}...")
    print(f"Bob shared secret: {bob_shared[:16].hex()}...")
    print(f"Keys match: {alice_shared == bob_shared}")


def demo_streaming_encryption():
    """Demonstrate streaming encryption for large files"""
    print("\n=== Streaming Encryption Demo ===")
    
    # Create test file (10MB for demo)
    test_file = create_test_file(10)
    
    try:
        # Generate encryption key
        key = os.urandom(32)  # 256-bit key
        encryptor = StreamingEncryptor(key)
        
        # Encrypt file
        print("Encrypting file...")
        encrypted_file = test_file + ".encrypted"
        original_hash = encryptor.encrypt_file(test_file, encrypted_file)
        
        # Check sizes
        original_size = os.path.getsize(test_file)
        encrypted_size = os.path.getsize(encrypted_file)
        overhead = encrypted_size - original_size
        
        print(f"Original size: {original_size:,} bytes")
        print(f"Encrypted size: {encrypted_size:,} bytes")
        print(f"Overhead: {overhead:,} bytes ({overhead/original_size*100:.2f}%)")
        
        # Decrypt file
        print("Decrypting file...")
        decrypted_file = test_file + ".decrypted"
        decrypted_hash = encryptor.decrypt_file(encrypted_file, decrypted_file)
        
        # Verify integrity
        print(f"Original hash: {original_hash.hex()}")
        print(f"Decrypted hash: {decrypted_hash.hex()}")
        print(f"Integrity verified: {original_hash == decrypted_hash}")
        
        # Cleanup
        os.unlink(encrypted_file)
        os.unlink(decrypted_file)
        
    finally:
        os.unlink(test_file)


def demo_key_management():
    """Demonstrate key management system"""
    print("\n=== Key Management Demo ===")
    
    # Create key manager with test password
    key_manager = KeyManager(key_store_path=".demo_keys", master_password="demo123")
    
    # Generate and store a keypair
    crypto = HybridCrypto("Kyber768")
    public_key, private_key = crypto.generate_keypair()
    
    key_id = "demo_keypair_001"
    print(f"Storing keypair: {key_id}")
    
    success = key_manager.store_keypair(
        key_id=key_id,
        public_key=public_key,
        private_key=private_key,
        algorithm="Kyber768",
        metadata={"purpose": "demo", "created_by": "basic_usage.py"}
    )
    
    if success:
        print("Keypair stored successfully")
        
        # Load the keypair
        loaded_keys = key_manager.load_keypair(key_id)
        if loaded_keys:
            loaded_public, loaded_private, algorithm = loaded_keys
            print(f"Keypair loaded successfully, algorithm: {algorithm}")
            print(f"Keys match: {loaded_public == public_key}")
        
        # Get fingerprint
        fingerprint = key_manager.get_key_fingerprint(key_id)
        print(f"Key fingerprint: {fingerprint}")
        
        # Export public key
        exported = key_manager.export_public_key(key_id, format="pem")
        print(f"Exported public key:\n{exported[:100]}...")
        
        # List all keys
        all_keys = key_manager.list_keys()
        print(f"Total keys in store: {len(all_keys)}")
        
        # Cleanup
        key_manager.delete_key(key_id)
        print("Demo key deleted")
    
    # Cleanup key store
    import shutil
    if os.path.exists(".demo_keys"):
        shutil.rmtree(".demo_keys")


async def demo_secure_transfer():
    """Demonstrate secure file transfer"""
    print("\n=== Secure Transfer Demo ===")
    print("This would demonstrate the full secure transfer protocol")
    print("Run server.py and client.py for a complete demo")


def main():
    """Run all demonstrations"""
    print("PQC Secure Transfer System - Basic Usage Demo")
    print("=" * 50)
    
    try:
        demo_hybrid_crypto()
        demo_streaming_encryption()
        demo_key_management()
        asyncio.run(demo_secure_transfer())
        
        print("\n=== Demo Complete ===")
        print("All components working correctly!")
        
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Please install required packages:")
        print("pip install -r requirements.txt")
    except Exception as e:
        print(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()