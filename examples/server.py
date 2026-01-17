#!/usr/bin/env python3
"""
Secure File Transfer Server
Receives large files using hybrid PQC encryption
"""

import os
import sys
import asyncio
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pqc_secure_transfer import SecureServer


async def main():
    parser = argparse.ArgumentParser(description="PQC Secure File Transfer Server")
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--port", type=int, default=8765, help="Server port")
    parser.add_argument("--output-dir", default="./received_files", help="Directory for received files")
    
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    print(f"Starting PQC Secure Transfer Server")
    print(f"Host: {args.host}")
    print(f"Port: {args.port}")
    print(f"Output directory: {args.output_dir}")
    print("=" * 50)
    
    try:
        server = SecureServer(host=args.host, port=args.port)
        await server.start_server()
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"Server error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())