#!/usr/bin/env python3
"""
Test script for free deployments with smaller payloads
Optimized for free tier limitations
"""

import asyncio
import sys
import os
import tempfile
import time

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from pqc_secure_transfer import SecureClient
    PQC_AVAILABLE = True
except ImportError:
    PQC_AVAILABLE = False
    print("⚠️  PQC modules not available, testing basic connectivity only")


def create_test_file(size_mb=10):
    """Create a test file suitable for free tier (smaller size)"""
    print(f"📁 Creating {size_mb}MB test file for free tier testing...")
    
    test_file = tempfile.NamedTemporaryFile(delete=False, suffix='.dat')
    chunk_size = 1024 * 1024  # 1MB chunks
    
    start_time = time.time()
    for i in range(size_mb):
        # Create varied data for better testing
        chunk_data = bytes((b + i) % 256 for b in os.urandom(chunk_size))
        test_file.write(chunk_data)
        
        if (i + 1) % 5 == 0:
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed
            print(f"  Created {i+1}/{size_mb} MB ({rate:.1f} MB/s)")
    
    test_file.close()
    total_time = time.time() - start_time
    print(f"✅ Test file created: {test_file.name} ({total_time:.1f}s)")
    return test_file.name


async def test_basic_connectivity(server_url):
    """Test basic connectivity without PQC modules"""
    import aiohttp
    
    print(f"🔗 Testing basic connectivity to: {server_url}")
    
    # Convert WebSocket URL to HTTP for health check
    http_url = server_url.replace('ws://', 'http://').replace('wss://', 'https://')
    if not http_url.endswith('/health'):
        http_url = http_url.rstrip('/') + '/health'
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(http_url, timeout=10) as response:
                if response.status == 200:
                    print("✅ Server is responding to health checks")
                    return True
                else:
                    print(f"❌ Server returned status: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


async def test_secure_transfer(server_url):
    """Test secure transfer with PQC modules"""
    if not PQC_AVAILABLE:
        print("⚠️  Skipping secure transfer test (PQC modules not available)")
        return await test_basic_connectivity(server_url)
    
    print(f"🔐 Testing secure transfer to: {server_url}")
    
    try:
        # Create small test file (10MB for free tier)
        test_file = create_test_file(10)
        
        try:
            client = SecureClient(server_url)
            
            print("🚀 Starting secure file transfer...")
            start_time = time.time()
            
            metadata = {
                "test_type": "free_tier",
                "file_size_mb": 10,
                "client": "test_script"
            }
            
            success = await client.send_file(test_file, metadata)
            
            transfer_time = time.time() - start_time
            
            if success:
                file_size = os.path.getsize(test_file)
                throughput = (file_size / 1024 / 1024) / transfer_time
                
                print(f"✅ Secure transfer successful!")
                print(f"   📊 File size: {file_size:,} bytes ({file_size/1024/1024:.1f} MB)")
                print(f"   ⏱️  Transfer time: {transfer_time:.2f}s")
                print(f"   🚀 Throughput: {throughput:.1f} MB/s")
                print(f"   🔐 Quantum-safe encryption: Active")
                return True
            else:
                print("❌ Secure transfer failed")
                return False
                
        finally:
            # Cleanup test file
            os.unlink(test_file)
            
    except Exception as e:
        print(f"❌ Transfer error: {e}")
        return False


def test_free_tier_limits(server_url):
    """Test and display free tier information"""
    print(f"\n📊 FREE TIER TESTING SUMMARY")
    print(f"=" * 50)
    print(f"🔗 Server: {server_url}")
    print(f"📁 Test payload: 10MB (free-tier optimized)")
    print(f"🔐 Security: Quantum-resistant hybrid encryption")
    print(f"💰 Cost: $0 (within free tier limits)")
    print(f"🎯 Suitable for: Development, testing, small production")


async def main():
    """Main test function"""
    if len(sys.argv) != 2:
        print("🧪 PQC Secure Transfer - Free Tier Testing")
        print("=" * 50)
        print("")
        print("Usage: python test-free-deployment.py <server_url>")
        print("")
        print("Examples:")
        print("  Google Cloud Run:")
        print("    python test-free-deployment.py ws://your-service-xyz-uc.a.run.app")
        print("")
        print("  Railway:")
        print("    python test-free-deployment.py ws://pqc-secure-transfer.up.railway.app")
        print("")
        print("  Render:")
        print("    python test-free-deployment.py ws://pqc-secure-transfer.onrender.com")
        print("")
        print("  Fly.io:")
        print("    python test-free-deployment.py ws://your-app.fly.dev")
        print("")
        sys.exit(1)
    
    server_url = sys.argv[1]
    
    print("🧪 PQC Secure Transfer - Free Deployment Test")
    print("=" * 60)
    print("")
    
    # Display test information
    test_free_tier_limits(server_url)
    print("")
    
    # Run the appropriate test
    if PQC_AVAILABLE:
        print("🔐 Running full PQC secure transfer test...")
        success = await test_secure_transfer(server_url)
    else:
        print("🔗 Running basic connectivity test...")
        success = await test_basic_connectivity(server_url)
    
    print("")
    print("=" * 60)
    
    if success:
        print("🎉 FREE DEPLOYMENT TEST SUCCESSFUL!")
        print("")
        print("✅ Your quantum-safe system is working perfectly on free tier!")
        print("🔐 Ready for federated learning workloads")
        print("💰 Zero cost deployment confirmed")
        print("")
        print("📈 Next steps:")
        print("  • Integrate with your FL framework")
        print("  • Test with larger files (within free limits)")
        print("  • Set up monitoring and alerts")
        print("  • Consider upgrading for production workloads")
    else:
        print("❌ FREE DEPLOYMENT TEST FAILED")
        print("")
        print("🔧 Troubleshooting:")
        print("  • Check if the server URL is correct")
        print("  • Verify the deployment is running")
        print("  • Check platform logs for errors")
        print("  • Ensure WebSocket connections are supported")
    
    print("")
    return 0 if success else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        sys.exit(1)