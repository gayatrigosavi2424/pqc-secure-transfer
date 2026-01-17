#!/usr/bin/env python3
"""
Comprehensive test of the PQC Secure Transfer System
Tests all components without requiring liboqs installation
"""

import os
import sys
import tempfile
import hashlib
from unittest.mock import Mock, patch

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_streaming_encryption():
    """Test streaming encryption without PQC dependencies"""
    print("Testing Streaming Encryption...")
    
    try:
        from pqc_secure_transfer.streaming_encryptor import StreamingEncryptor
        
        # Create test data
        test_data = b"Hello, World! " * 1000000  # ~13MB of test data
        key = os.urandom(32)  # 256-bit key
        
        # Create temporary files
        with tempfile.NamedTemporaryFile() as input_file, \
             tempfile.NamedTemporaryFile() as encrypted_file, \
             tempfile.NamedTemporaryFile() as decrypted_file:
            
            # Write test data
            input_file.write(test_data)
            input_file.flush()
            input_file.seek(0)
            
            # Encrypt
            encryptor = StreamingEncryptor(key)
            original_hash = encryptor.encrypt_stream(input_file, encrypted_file)
            
            # Decrypt
            encrypted_file.seek(0)
            decrypted_hash = encryptor.decrypt_stream(encrypted_file, decrypted_file)
            
            # Verify
            decrypted_file.seek(0)
            decrypted_data = decrypted_file.read()
            
            assert decrypted_data == test_data, "Decrypted data doesn't match original"
            assert original_hash == decrypted_hash, "Hash verification failed"
            
            print("✅ Streaming encryption test passed")
            return True
            
    except Exception as e:
        print(f"❌ Streaming encryption test failed: {e}")
        return False


def test_key_manager():
    """Test key management system"""
    print("Testing Key Manager...")
    
    try:
        from pqc_secure_transfer.key_manager import KeyManager
        
        # Create temporary key store
        with tempfile.TemporaryDirectory() as temp_dir:
            key_manager = KeyManager(temp_dir, master_password="test123")
            
            # Test key storage
            test_public = b"test_public_key_data"
            test_private = b"test_private_key_data"
            
            success = key_manager.store_keypair(
                key_id="test_key",
                public_key=test_public,
                private_key=test_private,
                algorithm="TestAlgorithm",
                metadata={"test": True}
            )
            
            assert success, "Failed to store keypair"
            
            # Test key loading
            loaded = key_manager.load_keypair("test_key")
            assert loaded is not None, "Failed to load keypair"
            
            loaded_public, loaded_private, algorithm = loaded
            assert loaded_public == test_public, "Public key mismatch"
            assert loaded_private == test_private, "Private key mismatch"
            assert algorithm == "TestAlgorithm", "Algorithm mismatch"
            
            # Test key listing
            keys = key_manager.list_keys()
            assert len(keys) == 1, "Key list length mismatch"
            assert keys[0]["key_id"] == "test_key", "Key ID mismatch"
            
            print("✅ Key manager test passed")
            return True
            
    except Exception as e:
        print(f"❌ Key manager test failed: {e}")
        return False


def test_hybrid_crypto_mock():
    """Test hybrid crypto with mocked liboqs"""
    print("Testing Hybrid Crypto (mocked)...")
    
    try:
        # Mock the oqs module
        mock_oqs = Mock()
        mock_kem = Mock()
        
        # Configure mock KEM
        mock_kem.generate_keypair.return_value = b"mock_pqc_public_key"
        mock_kem.export_secret_key.return_value = b"mock_pqc_secret_key"
        mock_kem.encap_secret.return_value = (b"mock_ciphertext", b"mock_shared_secret")
        mock_kem.decap_secret.return_value = b"mock_shared_secret"
        
        mock_oqs.KeyEncapsulation.return_value.__enter__.return_value = mock_kem
        mock_oqs.KeyEncapsulation.return_value.__exit__.return_value = None
        
        with patch.dict('sys.modules', {'oqs': mock_oqs}):
            from pqc_secure_transfer.hybrid_crypto import HybridCrypto
            
            # Test keypair generation
            crypto = HybridCrypto("Kyber768")
            public_key, private_key = crypto.generate_keypair()
            
            assert public_key is not None, "Public key generation failed"
            assert private_key is not None, "Private key generation failed"
            
            print("✅ Hybrid crypto test passed (mocked)")
            return True
            
    except Exception as e:
        print(f"❌ Hybrid crypto test failed: {e}")
        return False


def test_file_operations():
    """Test file operations and utilities"""
    print("Testing File Operations...")
    
    try:
        from pqc_secure_transfer.streaming_encryptor import StreamingEncryptor
        
        # Test file encryption/decryption
        test_content = b"Test file content for encryption" * 10000
        key = os.urandom(32)
        
        with tempfile.NamedTemporaryFile(delete=False) as temp_input, \
             tempfile.NamedTemporaryFile(delete=False) as temp_encrypted, \
             tempfile.NamedTemporaryFile(delete=False) as temp_decrypted:
            
            # Write test content
            temp_input.write(test_content)
            temp_input.flush()
            
            # Get file paths
            input_path = temp_input.name
            encrypted_path = temp_encrypted.name
            decrypted_path = temp_decrypted.name
        
        try:
            # Encrypt file
            encryptor = StreamingEncryptor(key)
            original_hash = encryptor.encrypt_file(input_path, encrypted_path)
            
            # Decrypt file
            decrypted_hash = encryptor.decrypt_file(encrypted_path, decrypted_path)
            
            # Verify content
            with open(decrypted_path, 'rb') as f:
                decrypted_content = f.read()
            
            assert decrypted_content == test_content, "File content mismatch"
            assert original_hash == decrypted_hash, "Hash mismatch"
            
            print("✅ File operations test passed")
            return True
            
        finally:
            # Cleanup
            for path in [input_path, encrypted_path, decrypted_path]:
                try:
                    os.unlink(path)
                except:
                    pass
                    
    except Exception as e:
        print(f"❌ File operations test failed: {e}")
        return False


def test_performance_estimation():
    """Test performance estimation functions"""
    print("Testing Performance Estimation...")
    
    try:
        from pqc_secure_transfer.streaming_encryptor import StreamingEncryptor
        
        # Test size estimation
        original_size = 20 * 1024 * 1024 * 1024  # 20GB
        estimated_size = StreamingEncryptor.estimate_encrypted_size(original_size)
        
        # Should be slightly larger than original
        assert estimated_size > original_size, "Estimated size should be larger"
        
        # Overhead should be reasonable (less than 1% for large files)
        overhead = estimated_size - original_size
        overhead_percent = (overhead / original_size) * 100
        
        assert overhead_percent < 1.0, f"Overhead too high: {overhead_percent:.2f}%"
        
        print(f"✅ Performance estimation test passed (overhead: {overhead_percent:.3f}%)")
        return True
        
    except Exception as e:
        print(f"❌ Performance estimation test failed: {e}")
        return False


def test_error_handling():
    """Test error handling and edge cases"""
    print("Testing Error Handling...")
    
    try:
        from pqc_secure_transfer.streaming_encryptor import StreamingEncryptor
        
        # Test invalid key size
        try:
            StreamingEncryptor(b"short_key")  # Too short
            assert False, "Should have raised ValueError for short key"
        except ValueError:
            pass  # Expected
        
        # Test with valid key
        key = os.urandom(32)
        encryptor = StreamingEncryptor(key)
        
        # Test with non-existent file
        try:
            encryptor.encrypt_file("non_existent_file.txt", "output.enc")
            assert False, "Should have raised exception for non-existent file"
        except (FileNotFoundError, IOError):
            pass  # Expected
        
        print("✅ Error handling test passed")
        return True
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("PQC Secure Transfer System - Comprehensive Test")
    print("=" * 60)
    
    tests = [
        test_streaming_encryption,
        test_key_manager,
        test_hybrid_crypto_mock,
        test_file_operations,
        test_performance_estimation,
        test_error_handling
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            failed += 1
        print()
    
    print("=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! System is working correctly.")
        print("\nNext steps:")
        print("1. Install liboqs-python for full PQC functionality:")
        print("   pip install liboqs-python")
        print("2. Run the examples:")
        print("   python examples/basic_usage.py")
        print("   python examples/federated_learning_demo.py")
        print("3. Start the server/client demo:")
        print("   python examples/server.py")
        print("   python examples/client.py --create-test 100")
    else:
        print("❌ Some tests failed. Please check the error messages above.")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())