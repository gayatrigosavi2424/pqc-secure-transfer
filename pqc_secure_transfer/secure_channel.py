"""
Secure Communication Channel
Combines hybrid PQC key exchange with streaming encryption
"""

import asyncio
import json
import struct
from typing import Optional, Dict, Any, Callable
import websockets
from websockets.server import WebSocketServerProtocol
from websockets.client import WebSocketClientProtocol

from .hybrid_crypto import HybridCrypto
from .streaming_encryptor import StreamingEncryptor
from .key_manager import KeyManager


class SecureChannel:
    """
    Secure communication channel using hybrid PQC + streaming encryption
    Handles the complete secure data transfer protocol
    """
    
    def __init__(self, role: str = "client", pqc_algorithm: str = "Kyber768"):
        """
        Initialize secure channel
        
        Args:
            role: "client" or "server"
            pqc_algorithm: Post-quantum algorithm to use
        """
        self.role = role
        self.hybrid_crypto = HybridCrypto(pqc_algorithm)
        self.key_manager = KeyManager()
        self.session_key = None
        self.is_established = False
        
        # Generate our keypair
        self.public_key, self.private_key = self.hybrid_crypto.generate_keypair()
    
    async def establish_secure_session(self, websocket) -> bool:
        """
        Establish a secure session using hybrid key exchange
        
        Args:
            websocket: WebSocket connection
            
        Returns:
            True if session established successfully
        """
        try:
            if self.role == "server":
                return await self._server_handshake(websocket)
            else:
                return await self._client_handshake(websocket)
        except Exception as e:
            print(f"Handshake failed: {e}")
            return False
    
    async def _server_handshake(self, websocket: WebSocketServerProtocol) -> bool:
        """Server-side handshake"""
        # Send our public key
        await websocket.send(json.dumps({
            "type": "public_key",
            "data": self.public_key.decode('utf-8')
        }))
        
        # Receive client's public key and encapsulated key
        message = await websocket.recv()
        data = json.loads(message)
        
        if data["type"] != "key_exchange":
            raise ValueError("Expected key_exchange message")
        
        client_public_key = data["public_key"].encode('utf-8')
        encapsulated_key = data["encapsulated_key"].encode('utf-8')
        
        # Perform our own key encapsulation with client's public key
        our_shared_secret, our_encapsulated = self.hybrid_crypto.encapsulate_key(client_public_key)
        
        # Decapsulate client's key
        client_shared_secret = self.hybrid_crypto.decapsulate_key(encapsulated_key)
        
        # Combine secrets (in practice, you'd use a more sophisticated method)
        combined_secret = self._combine_shared_secrets(our_shared_secret, client_shared_secret)
        self.session_key = combined_secret[:32]  # Use first 32 bytes for AES-256
        
        # Send our encapsulated key back
        await websocket.send(json.dumps({
            "type": "key_exchange_response",
            "encapsulated_key": our_encapsulated.decode('utf-8')
        }))
        
        # Receive confirmation
        confirmation = await websocket.recv()
        conf_data = json.loads(confirmation)
        
        if conf_data["type"] == "handshake_complete":
            self.is_established = True
            return True
        
        return False
    
    async def _client_handshake(self, websocket: WebSocketClientProtocol) -> bool:
        """Client-side handshake"""
        # Receive server's public key
        message = await websocket.recv()
        data = json.loads(message)
        
        if data["type"] != "public_key":
            raise ValueError("Expected public_key message")
        
        server_public_key = data["data"].encode('utf-8')
        
        # Perform key encapsulation
        shared_secret, encapsulated_key = self.hybrid_crypto.encapsulate_key(server_public_key)
        
        # Send our public key and encapsulated key
        await websocket.send(json.dumps({
            "type": "key_exchange",
            "public_key": self.public_key.decode('utf-8'),
            "encapsulated_key": encapsulated_key.decode('utf-8')
        }))
        
        # Receive server's encapsulated key
        response = await websocket.recv()
        resp_data = json.loads(response)
        
        if resp_data["type"] != "key_exchange_response":
            raise ValueError("Expected key_exchange_response")
        
        server_encapsulated = resp_data["encapsulated_key"].encode('utf-8')
        server_shared_secret = self.hybrid_crypto.decapsulate_key(server_encapsulated)
        
        # Combine secrets
        combined_secret = self._combine_shared_secrets(shared_secret, server_shared_secret)
        self.session_key = combined_secret[:32]
        
        # Send confirmation
        await websocket.send(json.dumps({
            "type": "handshake_complete"
        }))
        
        self.is_established = True
        return True
    
    async def send_large_file(self, websocket, file_path: str, 
                             metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Send a large file securely over the established channel
        
        Args:
            websocket: WebSocket connection
            file_path: Path to file to send
            metadata: Optional metadata about the file
            
        Returns:
            True if file sent successfully
        """
        if not self.is_established:
            raise RuntimeError("Secure session not established")
        
        import os
        file_size = os.path.getsize(file_path)
        
        # Create streaming encryptor
        encryptor = StreamingEncryptor(self.session_key)
        
        # Send file metadata
        file_metadata = {
            "type": "file_transfer_start",
            "filename": os.path.basename(file_path),
            "size": file_size,
            "encrypted_size": encryptor.estimate_encrypted_size(file_size),
            "metadata": metadata or {}
        }
        
        await websocket.send(json.dumps(file_metadata))
        
        # Wait for acknowledgment
        ack = await websocket.recv()
        ack_data = json.loads(ack)
        if ack_data["type"] != "ready_to_receive":
            return False
        
        # Stream encrypted file
        try:
            with open(file_path, 'rb') as input_file:
                chunk_size = 64 * 1024  # 64KB chunks for WebSocket
                encryptor_small = StreamingEncryptor(self.session_key, chunk_size)
                
                # Create a temporary buffer for encrypted data
                import io
                encrypted_buffer = io.BytesIO()
                
                # Encrypt the file
                file_hash = encryptor_small.encrypt_stream(input_file, encrypted_buffer)
                
                # Send encrypted data in chunks
                encrypted_buffer.seek(0)
                total_sent = 0
                
                while True:
                    chunk = encrypted_buffer.read(chunk_size)
                    if not chunk:
                        break
                    
                    # Send chunk with metadata
                    chunk_message = {
                        "type": "file_chunk",
                        "data": chunk.hex(),  # Convert to hex for JSON
                        "offset": total_sent,
                        "is_last": len(chunk) < chunk_size
                    }
                    
                    await websocket.send(json.dumps(chunk_message))
                    total_sent += len(chunk)
                
                # Send completion message with hash
                completion_message = {
                    "type": "file_transfer_complete",
                    "hash": file_hash.hex(),
                    "total_size": total_sent
                }
                
                await websocket.send(json.dumps(completion_message))
                
                # Wait for final confirmation
                final_ack = await websocket.recv()
                final_data = json.loads(final_ack)
                
                return final_data["type"] == "transfer_confirmed"
                
        except Exception as e:
            # Send error message
            error_message = {
                "type": "transfer_error",
                "error": str(e)
            }
            await websocket.send(json.dumps(error_message))
            return False
    
    async def receive_large_file(self, websocket, output_path: str) -> bool:
        """
        Receive a large file securely over the established channel
        
        Args:
            websocket: WebSocket connection
            output_path: Path where to save the received file
            
        Returns:
            True if file received successfully
        """
        if not self.is_established:
            raise RuntimeError("Secure session not established")
        
        try:
            # Receive file metadata
            metadata_msg = await websocket.recv()
            metadata = json.loads(metadata_msg)
            
            if metadata["type"] != "file_transfer_start":
                return False
            
            # Send ready acknowledgment
            await websocket.send(json.dumps({"type": "ready_to_receive"}))
            
            # Prepare to receive file
            import io
            encrypted_buffer = io.BytesIO()
            expected_hash = None
            
            while True:
                message = await websocket.recv()
                data = json.loads(message)
                
                if data["type"] == "file_chunk":
                    # Receive and buffer encrypted chunk
                    chunk_data = bytes.fromhex(data["data"])
                    encrypted_buffer.write(chunk_data)
                    
                elif data["type"] == "file_transfer_complete":
                    expected_hash = bytes.fromhex(data["hash"])
                    break
                    
                elif data["type"] == "transfer_error":
                    print(f"Transfer error: {data['error']}")
                    return False
            
            # Decrypt the received data
            encrypted_buffer.seek(0)
            decryptor = StreamingEncryptor(self.session_key)
            
            with open(output_path, 'wb') as output_file:
                actual_hash = decryptor.decrypt_stream(encrypted_buffer, output_file)
            
            # Verify hash
            if actual_hash == expected_hash:
                await websocket.send(json.dumps({"type": "transfer_confirmed"}))
                return True
            else:
                await websocket.send(json.dumps({
                    "type": "transfer_error", 
                    "error": "Hash verification failed"
                }))
                return False
                
        except Exception as e:
            await websocket.send(json.dumps({
                "type": "transfer_error",
                "error": str(e)
            }))
            return False
    
    def _combine_shared_secrets(self, secret1: bytes, secret2: bytes) -> bytes:
        """
        Combine two shared secrets using a secure method
        
        Args:
            secret1: First shared secret
            secret2: Second shared secret
            
        Returns:
            Combined secret
        """
        import hashlib
        from cryptography.hazmat.primitives.kdf.hkdf import HKDF
        from cryptography.hazmat.primitives import hashes
        
        # Use HKDF to combine the secrets
        combined_input = secret1 + secret2
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=64,  # 512 bits
            salt=None,
            info=b'secure-channel-key-combination',
        )
        
        return hkdf.derive(combined_input)


class SecureServer:
    """
    Secure WebSocket server for receiving large files
    """
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.clients = {}
    
    async def handle_client(self, websocket, path):
        """Handle incoming client connection"""
        client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        print(f"Client connected: {client_id}")
        
        # Create secure channel for this client
        channel = SecureChannel(role="server")
        self.clients[client_id] = channel
        
        try:
            # Establish secure session
            if await channel.establish_secure_session(websocket):
                print(f"Secure session established with {client_id}")
                
                # Handle file transfers
                await self.handle_file_transfers(websocket, channel, client_id)
            else:
                print(f"Failed to establish secure session with {client_id}")
                
        except websockets.exceptions.ConnectionClosed:
            print(f"Client {client_id} disconnected")
        except Exception as e:
            print(f"Error handling client {client_id}: {e}")
        finally:
            if client_id in self.clients:
                del self.clients[client_id]
    
    async def handle_file_transfers(self, websocket, channel: SecureChannel, client_id: str):
        """Handle file transfer requests"""
        while True:
            try:
                # Wait for transfer requests
                message = await websocket.recv()
                data = json.loads(message)
                
                if data["type"] == "file_transfer_start":
                    # Receive file
                    output_path = f"received_{data['filename']}"
                    success = await channel.receive_large_file(websocket, output_path)
                    
                    if success:
                        print(f"Successfully received file from {client_id}: {output_path}")
                    else:
                        print(f"Failed to receive file from {client_id}")
                        
            except websockets.exceptions.ConnectionClosed:
                break
            except Exception as e:
                print(f"Error in file transfer with {client_id}: {e}")
                break
    
    async def start_server(self):
        """Start the secure server"""
        print(f"Starting secure server on {self.host}:{self.port}")
        async with websockets.serve(self.handle_client, self.host, self.port):
            await asyncio.Future()  # Run forever


class SecureClient:
    """
    Secure WebSocket client for sending large files
    """
    
    def __init__(self, server_uri: str = "ws://localhost:8765"):
        self.server_uri = server_uri
        self.channel = SecureChannel(role="client")
    
    async def send_file(self, file_path: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Send a file to the server
        
        Args:
            file_path: Path to file to send
            metadata: Optional metadata
            
        Returns:
            True if file sent successfully
        """
        try:
            async with websockets.connect(self.server_uri) as websocket:
                # Establish secure session
                if await self.channel.establish_secure_session(websocket):
                    print("Secure session established")
                    
                    # Send file
                    success = await self.channel.send_large_file(websocket, file_path, metadata)
                    
                    if success:
                        print(f"File sent successfully: {file_path}")
                    else:
                        print(f"Failed to send file: {file_path}")
                    
                    return success
                else:
                    print("Failed to establish secure session")
                    return False
                    
        except Exception as e:
            print(f"Error sending file: {e}")
            return False