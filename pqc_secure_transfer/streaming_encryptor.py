"""
Streaming Authenticated Encryption for Large Payloads
Handles 15-20GB files efficiently with constant memory usage
"""

import os
import struct
from typing import Iterator, BinaryIO, Optional
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import hashlib


class StreamingEncryptor:
    """
    Streaming AEAD encryption for large files using AES-256-GCM
    Processes data in chunks to maintain constant memory usage
    """
    
    def __init__(self, key: bytes, chunk_size: int = 4 * 1024 * 1024):  # 4MB chunks
        """
        Initialize streaming encryptor
        
        Args:
            key: 256-bit encryption key
            chunk_size: Size of each chunk in bytes (default 4MB)
        """
        if len(key) != 32:
            raise ValueError("Key must be 256 bits (32 bytes)")
        
        self.key = key
        self.chunk_size = chunk_size
        self.nonce_size = 12  # 96 bits for GCM
        self.tag_size = 16    # 128 bits for GCM authentication tag
    
    def encrypt_stream(self, input_stream: BinaryIO, output_stream: BinaryIO, 
                      associated_data: Optional[bytes] = None) -> bytes:
        """
        Encrypt a stream of data chunk by chunk
        
        Args:
            input_stream: Input data stream
            output_stream: Output encrypted stream
            associated_data: Additional authenticated data
            
        Returns:
            Overall file hash for integrity verification
        """
        # Generate master nonce for this file
        master_nonce = get_random_bytes(self.nonce_size)
        
        # Write header: master_nonce + file_size (if available)
        try:
            # Try to get file size
            current_pos = input_stream.tell()
            input_stream.seek(0, 2)  # Seek to end
            file_size = input_stream.tell()
            input_stream.seek(current_pos)  # Restore position
        except (OSError, IOError):
            file_size = 0  # Unknown size for non-seekable streams
        
        header = master_nonce + struct.pack('<Q', file_size)
        output_stream.write(header)
        
        chunk_index = 0
        file_hasher = hashlib.sha256()
        
        while True:
            chunk = input_stream.read(self.chunk_size)
            if not chunk:
                break
            
            # Generate unique nonce for this chunk
            chunk_nonce = self._generate_chunk_nonce(master_nonce, chunk_index)
            
            # Encrypt chunk
            cipher = AES.new(self.key, AES.MODE_GCM, nonce=chunk_nonce)
            
            if associated_data:
                cipher.update(associated_data)
            
            ciphertext, tag = cipher.encrypt_and_digest(chunk)
            
            # Write chunk: size + nonce + tag + ciphertext
            chunk_header = struct.pack('<I', len(ciphertext)) + chunk_nonce + tag
            output_stream.write(chunk_header)
            output_stream.write(ciphertext)
            
            # Update file hash
            file_hasher.update(chunk)
            
            chunk_index += 1
        
        return file_hasher.digest()
    
    def decrypt_stream(self, input_stream: BinaryIO, output_stream: BinaryIO,
                      associated_data: Optional[bytes] = None) -> bytes:
        """
        Decrypt a stream of data chunk by chunk
        
        Args:
            input_stream: Input encrypted stream
            output_stream: Output decrypted stream
            associated_data: Additional authenticated data
            
        Returns:
            File hash for integrity verification
        """
        # Read header
        header = input_stream.read(self.nonce_size + 8)
        if len(header) != self.nonce_size + 8:
            raise ValueError("Invalid encrypted file header")
        
        master_nonce = header[:self.nonce_size]
        file_size = struct.unpack('<Q', header[self.nonce_size:])[0]
        
        chunk_index = 0
        file_hasher = hashlib.sha256()
        
        while True:
            # Read chunk header
            chunk_header = input_stream.read(4 + self.nonce_size + self.tag_size)
            if len(chunk_header) == 0:
                break  # End of file
            
            if len(chunk_header) != 4 + self.nonce_size + self.tag_size:
                raise ValueError("Invalid chunk header")
            
            chunk_size = struct.unpack('<I', chunk_header[:4])[0]
            chunk_nonce = chunk_header[4:4 + self.nonce_size]
            tag = chunk_header[4 + self.nonce_size:]
            
            # Read ciphertext
            ciphertext = input_stream.read(chunk_size)
            if len(ciphertext) != chunk_size:
                raise ValueError("Incomplete chunk data")
            
            # Verify nonce matches expected pattern
            expected_nonce = self._generate_chunk_nonce(master_nonce, chunk_index)
            if chunk_nonce != expected_nonce:
                raise ValueError(f"Nonce mismatch at chunk {chunk_index}")
            
            # Decrypt chunk
            cipher = AES.new(self.key, AES.MODE_GCM, nonce=chunk_nonce)
            
            if associated_data:
                cipher.update(associated_data)
            
            try:
                plaintext = cipher.decrypt_and_verify(ciphertext, tag)
            except ValueError as e:
                raise ValueError(f"Authentication failed at chunk {chunk_index}: {e}")
            
            output_stream.write(plaintext)
            file_hasher.update(plaintext)
            
            chunk_index += 1
        
        return file_hasher.digest()
    
    def encrypt_file(self, input_path: str, output_path: str, 
                    associated_data: Optional[bytes] = None) -> bytes:
        """
        Encrypt a file using streaming encryption
        
        Args:
            input_path: Path to input file
            output_path: Path to output encrypted file
            associated_data: Additional authenticated data
            
        Returns:
            File hash for integrity verification
        """
        with open(input_path, 'rb') as input_file, \
             open(output_path, 'wb') as output_file:
            return self.encrypt_stream(input_file, output_file, associated_data)
    
    def decrypt_file(self, input_path: str, output_path: str,
                    associated_data: Optional[bytes] = None) -> bytes:
        """
        Decrypt a file using streaming decryption
        
        Args:
            input_path: Path to input encrypted file
            output_path: Path to output decrypted file
            associated_data: Additional authenticated data
            
        Returns:
            File hash for integrity verification
        """
        with open(input_path, 'rb') as input_file, \
             open(output_path, 'wb') as output_file:
            return self.decrypt_stream(input_file, output_file, associated_data)
    
    def _generate_chunk_nonce(self, master_nonce: bytes, chunk_index: int) -> bytes:
        """
        Generate a unique nonce for each chunk
        
        Args:
            master_nonce: Master nonce for the file
            chunk_index: Index of the current chunk
            
        Returns:
            Unique nonce for the chunk
        """
        # Use first 8 bytes of master nonce + 4 bytes of chunk index
        if len(master_nonce) < 8:
            raise ValueError("Master nonce too short")
        
        chunk_bytes = struct.pack('<I', chunk_index)
        return master_nonce[:8] + chunk_bytes
    
    @staticmethod
    def estimate_encrypted_size(original_size: int, chunk_size: int = 4 * 1024 * 1024) -> int:
        """
        Estimate the size of encrypted file
        
        Args:
            original_size: Size of original file
            chunk_size: Chunk size used for encryption
            
        Returns:
            Estimated encrypted file size
        """
        header_size = 12 + 8  # nonce + file_size
        num_chunks = (original_size + chunk_size - 1) // chunk_size
        chunk_overhead = num_chunks * (4 + 12 + 16)  # size + nonce + tag per chunk
        
        return header_size + original_size + chunk_overhead


class ProgressTracker:
    """
    Track progress of large file operations
    """
    
    def __init__(self, total_size: int, description: str = "Processing"):
        """
        Initialize progress tracker
        
        Args:
            total_size: Total size to process
            description: Description of the operation
        """
        self.total_size = total_size
        self.processed = 0
        self.description = description
        
        try:
            from tqdm import tqdm
            self.pbar = tqdm(total=total_size, desc=description, unit='B', unit_scale=True)
            self.has_tqdm = True
        except ImportError:
            self.pbar = None
            self.has_tqdm = False
    
    def update(self, chunk_size: int):
        """Update progress"""
        self.processed += chunk_size
        if self.has_tqdm and self.pbar:
            self.pbar.update(chunk_size)
        else:
            # Simple text progress
            percent = (self.processed / self.total_size) * 100
            print(f"\r{self.description}: {percent:.1f}% ({self.processed}/{self.total_size})", end='')
    
    def close(self):
        """Close progress tracker"""
        if self.has_tqdm and self.pbar:
            self.pbar.close()
        else:
            print()  # New line