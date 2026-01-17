#!/usr/bin/env python3
"""
Secure File Transfer Client
Sends large files using hybrid PQC encryption
"""

import os
import sys
import asyncio
import argparse
import tempfile

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pqc_secure_transfer import SecureClient


def create_test_file(size_mb: int, filename: str = None) -> str:
    """Create a test file of specified size"""
    if filename is None:
        test_file = tempfile.NamedTemporaryFile(delete=False, suffix='.dat')
        filename = test_file.name
        test_file.close()
    
    print(f"Creating {size_mb}MB test file: {filename}")
    
    with open(filename, 'wb') as f:
        chunk_size = 1024 * 1024  # 1MB chunks
        data_chunk = os.urandom(chunk_size)
        
        for i in range(size_mb):
            f.write(data_chunk)
            if (i + 1) % 100 == 0:
                print(f"  Written {i+1}/{size_mb} MB")
    
    print(f"Test file created: {filename}")
    return filename


async def main():
    parser = argparse.ArgumentParser(description="PQC Secure File Transfer Client")
    parser.add_argument("--server", default="ws://localhost:8765", help="Server WebSocket URI")
    parser.add_argument("--file", help="File to send")
    parser.add_argument("--create-test", type=int, help="Create test file of specified size (MB)")
    parser.add_argument("--test-size", type=int, default=100, help="Size of test file in MB")
    
    args = parser.parse_args()
    
    print(f"PQC Secure File Transfer Client")
    print(f"Server: {args.server}")
    print("=" * 50)
    
    try:
        # Determine file to send
        if args.create_test:
            file_to_send = create_test_file(args.create_test)
            cleanup_file = True
        elif args.file:
            if not os.path.exists(args.file):
                print(f"Error: File not found: {args.file}")
                return
            file_to_send = args.file
            cleanup_file = False
        else:
            # Create default test file
            file_to_send = create_test_file(args.test_size)
            cleanup_file = True
        
        # Get file info
        file_size = os.path.getsize(file_to_send)
        print(f"File to send: {file_to_send}")
        print(f"File size: {file_size:,} bytes ({file_size/1024/1024:.1f} MB)")
        
        # Create client and send file
        client = SecureClient(server_uri=args.server)
        
        metadata = {
            "original_name": os.path.basename(file_to_send),
            "size_mb": file_size / 1024 / 1024,
            "client_info": "PQC Demo Client"
        }
        
        print("Connecting to server and establishing secure channel...")
        success = await client.send_file(file_to_send, metadata)
        
        if success:
            print("✅ File transfer completed successfully!")
        else:
            print("❌ File transfer failed!")
        
        # Cleanup test file if created
        if cleanup_file:
            os.unlink(file_to_send)
            print(f"Cleaned up test file: {file_to_send}")
            
    except KeyboardInterrupt:
        print("\nTransfer cancelled by user")
    except Exception as e:
        print(f"Client error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())