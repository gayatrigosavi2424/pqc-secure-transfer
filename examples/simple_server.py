#!/usr/bin/env python3
"""
Simple Health Check Server for PQC Secure Transfer
"""

import asyncio
import json
from aiohttp import web
import time
import os


async def health_check(request):
    """Health check endpoint"""
    return web.json_response({
        "status": "healthy",
        "service": "PQC Secure Transfer",
        "version": "1.0.0",
        "pqc_algorithm": "Kyber768",
        "timestamp": int(time.time()),
        "uptime": int(time.time() - start_time)
    })


async def metrics(request):
    """Metrics endpoint for Prometheus"""
    metrics_data = f"""# HELP pqc_key_exchanges_total Total number of PQC key exchanges
# TYPE pqc_key_exchanges_total counter
pqc_key_exchanges_total 0

# HELP pqc_files_transferred_total Total number of files transferred
# TYPE pqc_files_transferred_total counter
pqc_files_transferred_total 0

# HELP pqc_bytes_transferred_total Total bytes transferred
# TYPE pqc_bytes_transferred_total counter
pqc_bytes_transferred_total 0

# HELP pqc_server_uptime_seconds Server uptime in seconds
# TYPE pqc_server_uptime_seconds gauge
pqc_server_uptime_seconds {int(time.time() - start_time)}
"""
    return web.Response(text=metrics_data, content_type='text/plain')


async def test_pqc(request):
    """Test PQC functionality endpoint"""
    # Simulate PQC key exchange
    await asyncio.sleep(0.1)  # Simulate processing time
    
    return web.json_response({
        "status": "success",
        "message": "PQC key exchange simulation completed",
        "algorithm": "Kyber768",
        "key_size": 1568,
        "processing_time_ms": 100
    })


async def init_app():
    """Initialize the web application"""
    app = web.Application()
    
    # Add routes
    app.router.add_get('/health', health_check)
    app.router.add_get('/metrics', metrics)
    app.router.add_post('/test-pqc', test_pqc)
    
    return app


async def main():
    """Main server function"""
    global start_time
    start_time = time.time()
    
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', '8765'))
    
    print(f"🚀 Starting PQC Secure Transfer Server")
    print(f"   Host: {host}")
    print(f"   Port: {port}")
    print(f"   Health: http://{host}:{port}/health")
    print(f"   Metrics: http://{host}:{port}/metrics")
    print("=" * 50)
    
    app = await init_app()
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, host, port)
    await site.start()
    
    print(f"✅ Server started successfully!")
    
    try:
        # Keep the server running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())