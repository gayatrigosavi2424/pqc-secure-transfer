# Free Cloud Deployment Options

Deploy your PQC Secure Transfer System completely **FREE** using these platforms with generous free tiers.

## 🆓 **Best Free Options**

| Platform | Free Tier | Duration | Best For |
|----------|-----------|----------|----------|
| **Google Cloud Run** | 2M requests/month | Forever | Production-ready |
| **Railway** | $5 credit/month | Forever | Easy deployment |
| **Render** | 750 hours/month | Forever | Simple hosting |
| **Fly.io** | 3 shared VMs | Forever | Global deployment |
| **Heroku** | 1000 dyno hours | Forever | Quick prototyping |
| **Oracle Cloud** | Always Free VMs | Forever | Full VMs |
| **GitHub Codespaces** | 120 hours/month | Forever | Development |

## 🚀 **Fastest Free Deployments**

### 1. Google Cloud Run (100% Free for Light Usage)

**Free Tier**: 2 million requests, 400,000 GiB-seconds, 200,000 vCPU-seconds per month

```bash
# One-command deployment
gcloud run deploy pqc-secure-transfer \
    --source https://github.com/gayatrigosavi2424/pqc-secure-transfer \
    --region us-central1 \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1 \
    --max-instances 10

# Get your free URL
SERVICE_URL=$(gcloud run services describe pqc-secure-transfer --region us-central1 --format 'value(status.url)')
echo "🆓 Free deployment: $SERVICE_URL"
```

**Perfect for**: Production use with moderate traffic (easily handles 1000+ requests/day)

### 2. Railway (Free $5 Credit Monthly)

**Free Tier**: $5 credit every month (enough for small apps)

1. **Go to**: https://railway.app
2. **Sign up** with GitHub
3. **Deploy**: Click "Deploy from GitHub repo"
4. **Select**: `gayatrigosavi2424/pqc-secure-transfer`
5. **Auto-deploy**: Railway detects Dockerfile and deploys automatically

**Perfect for**: Development and small production workloads

### 3. Render (Free 750 Hours/Month)

**Free Tier**: 750 hours of runtime per month (enough for 24/7 operation)

1. **Go to**: https://render.com
2. **Sign up** with GitHub
3. **New Web Service** → Connect GitHub
4. **Repository**: `gayatrigosavi2424/pqc-secure-transfer`
5. **Settings**:
   - **Environment**: Docker
   - **Plan**: Free
   - **Port**: 8765

**Perfect for**: Always-on free hosting

### 4. Fly.io (3 Free VMs)

**Free Tier**: 3 shared-cpu-1x VMs with 256MB RAM each

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Login and deploy
flyctl auth login
flyctl launch --name pqc-secure-transfer --region ord

# Deploy
flyctl deploy
```

**Perfect for**: Global deployment with multiple regions

## 🔧 **Free Deployment Configurations**

### Optimized for Free Tiers

Create `free-deployment-config.yaml`:

```yaml
# Optimized for free tiers
resources:
  memory: 512Mi  # Minimal memory usage
  cpu: 0.5       # Half CPU to stay in free limits

environment:
  PQC_ALGORITHM: Kyber768
  STREAM_CHUNK_SIZE: 1048576  # 1MB chunks (smaller for free tier)
  MAX_FILE_SIZE: 1073741824   # 1GB max (reasonable for free tier)
  LOG_LEVEL: INFO

scaling:
  min_instances: 0  # Scale to zero when not in use
  max_instances: 3  # Limit concurrent instances
```

### Docker Configuration for Free Tiers

Create `Dockerfile.free`:

```dockerfile
# Lightweight version for free deployments
FROM python:3.11-slim

# Install only essential dependencies
WORKDIR /app
COPY requirements.txt .

# Install minimal dependencies
RUN pip install --no-cache-dir \
    cryptography==41.0.0 \
    pycryptodome==3.19.0 \
    websockets==12.0 \
    aiofiles==23.2.0

# Copy only essential files
COPY pqc_secure_transfer/ ./pqc_secure_transfer/
COPY examples/server.py ./
COPY simple_demo.py ./

# Create non-root user
RUN useradd -m -u 1000 pqcuser && chown -R pqcuser:pqcuser /app
USER pqcuser

# Expose port
EXPOSE 8765

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import pqc_secure_transfer; print('OK')" || exit 1

# Start server
CMD ["python", "server.py", "--host", "0.0.0.0", "--port", "8765"]
```

## 🌐 **Platform-Specific Free Setup**

### Google Cloud Run (Recommended)

**Why it's the best free option**:
- Truly serverless (pay only when used)
- Automatic HTTPS
- Global CDN
- 99.95% uptime SLA

**Setup**:
```bash
# Enable free tier optimizations
gcloud run deploy pqc-secure-transfer \
    --source https://github.com/gayatrigosavi2424/pqc-secure-transfer \
    --region us-central1 \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1 \
    --concurrency 80 \
    --max-instances 5 \
    --set-env-vars="PQC_ALGORITHM=Kyber768,STREAM_CHUNK_SIZE=1048576"
```

### Railway Free Setup

**Railway Configuration** (`railway.toml`):
```toml
[build]
builder = "dockerfile"
dockerfilePath = "Dockerfile"

[deploy]
healthcheckPath = "/health"
healthcheckTimeout = 300
restartPolicyType = "on_failure"

[[deploy.environmentVariables]]
name = "PQC_ALGORITHM"
value = "Kyber768"

[[deploy.environmentVariables]]
name = "PORT"
value = "8765"
```

### Render Free Setup

**Render Configuration** (`render.yaml`):
```yaml
services:
  - type: web
    name: pqc-secure-transfer
    env: docker
    plan: free
    dockerfilePath: ./Dockerfile
    envVars:
      - key: PQC_ALGORITHM
        value: Kyber768
      - key: PORT
        value: 8765
    healthCheckPath: /health
```

### Fly.io Free Setup

**Fly Configuration** (`fly.toml`):
```toml
app = "pqc-secure-transfer"
primary_region = "ord"

[build]
  dockerfile = "Dockerfile"

[env]
  PQC_ALGORITHM = "Kyber768"
  PORT = "8765"

[http_service]
  internal_port = 8765
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true
  min_machines_running = 0

[[vm]]
  cpu_kind = "shared"
  cpus = 1
  memory_mb = 256
```

## 💡 **Free Tier Optimization Tips**

### 1. Minimize Resource Usage

```python
# Add to your server.py for free tier optimization
import os

# Optimize for free tier
MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', 1024*1024*1024))  # 1GB default
CHUNK_SIZE = int(os.getenv('STREAM_CHUNK_SIZE', 1024*1024))      # 1MB chunks

# Add memory-efficient processing
def optimize_for_free_tier():
    import gc
    gc.collect()  # Force garbage collection
```

### 2. Auto-Sleep Configuration

```python
# Add auto-sleep for free tiers
import time
import threading

class AutoSleep:
    def __init__(self, idle_timeout=300):  # 5 minutes
        self.idle_timeout = idle_timeout
        self.last_activity = time.time()
        
    def activity(self):
        self.last_activity = time.time()
        
    def check_idle(self):
        if time.time() - self.last_activity > self.idle_timeout:
            print("💤 Entering sleep mode to conserve free tier resources")
            # Implement graceful shutdown or sleep
```

### 3. Request Limiting

```python
# Limit concurrent requests for free tier
from asyncio import Semaphore

# Limit to 3 concurrent transfers on free tier
CONCURRENT_LIMIT = int(os.getenv('CONCURRENT_LIMIT', 3))
transfer_semaphore = Semaphore(CONCURRENT_LIMIT)

async def handle_transfer(websocket, path):
    async with transfer_semaphore:
        # Handle transfer with limited concurrency
        await process_transfer(websocket, path)
```

## 🧪 **Testing Free Deployments**

### Quick Test Script

Create `test-free-deployment.py`:

```python
#!/usr/bin/env python3
"""Test script for free deployments with smaller payloads"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pqc_secure_transfer import SecureClient

async def test_free_deployment(server_url):
    """Test deployment with free-tier appropriate payload"""
    print(f"🧪 Testing free deployment: {server_url}")
    
    try:
        client = SecureClient(server_url)
        
        # Test with smaller file (10MB) suitable for free tier
        print("📁 Creating 10MB test file...")
        test_file = create_small_test_file(10)  # 10MB
        
        print("🔐 Starting secure transfer...")
        success = await client.send_file(test_file, {"test": "free_tier"})
        
        if success:
            print("✅ Free deployment test successful!")
            print("🎉 Your quantum-safe system is running on free tier!")
        else:
            print("❌ Test failed")
            
        # Cleanup
        os.unlink(test_file)
        
    except Exception as e:
        print(f"❌ Test error: {e}")

def create_small_test_file(size_mb):
    """Create a small test file for free tier testing"""
    import tempfile
    
    test_file = tempfile.NamedTemporaryFile(delete=False, suffix='.dat')
    chunk_size = 1024 * 1024  # 1MB chunks
    
    for i in range(size_mb):
        test_file.write(os.urandom(chunk_size))
    
    test_file.close()
    return test_file.name

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test-free-deployment.py <server_url>")
        print("Example: python test-free-deployment.py ws://your-app.onrender.com")
        sys.exit(1)
    
    server_url = sys.argv[1]
    asyncio.run(test_free_deployment(server_url))
```

## 🎯 **Free Deployment Recommendations**

### For Different Use Cases

**🧪 Development & Testing**
- **Google Cloud Run**: Best free tier, automatic scaling
- **GitHub Codespaces**: For development environment

**🚀 Small Production**
- **Railway**: $5 monthly credit, easy deployment
- **Render**: 750 hours/month, always-on capability

**🌍 Global Deployment**
- **Fly.io**: Multiple regions, 3 free VMs
- **Vercel**: Global edge network (for static parts)

**💪 More Resources**
- **Oracle Cloud**: Always Free VMs (1/8 OCPU, 1GB RAM)
- **AWS Free Tier**: 12 months free (t2.micro instances)

## 🚀 **One-Click Free Deployment**

Create `deploy-free.sh`:

```bash
#!/bin/bash

echo "🆓 PQC Secure Transfer - Free Deployment Options"
echo "=============================================="

echo "Choose your free deployment platform:"
echo "1. Google Cloud Run (2M requests/month free)"
echo "2. Railway ($5 credit/month)"
echo "3. Render (750 hours/month free)"
echo "4. Fly.io (3 free VMs)"
echo ""

read -p "Enter choice (1-4): " choice

case $choice in
    1)
        echo "🚀 Deploying to Google Cloud Run (FREE)..."
        gcloud run deploy pqc-secure-transfer \
            --source https://github.com/gayatrigosavi2424/pqc-secure-transfer \
            --region us-central1 \
            --allow-unauthenticated \
            --memory 512Mi \
            --cpu 1 \
            --max-instances 5 \
            --set-env-vars="PQC_ALGORITHM=Kyber768"
        
        URL=$(gcloud run services describe pqc-secure-transfer --region us-central1 --format 'value(status.url)')
        echo "✅ FREE deployment complete: $URL"
        ;;
        
    2)
        echo "🚀 Railway Deployment Instructions:"
        echo "1. Go to https://railway.app"
        echo "2. Sign up with GitHub (FREE)"
        echo "3. Click 'Deploy from GitHub repo'"
        echo "4. Select: gayatrigosavi2424/pqc-secure-transfer"
        echo "5. Get $5 monthly credit (FREE)"
        ;;
        
    3)
        echo "🚀 Render Deployment Instructions:"
        echo "1. Go to https://render.com"
        echo "2. Sign up with GitHub (FREE)"
        echo "3. New Web Service → Connect GitHub"
        echo "4. Select: gayatrigosavi2424/pqc-secure-transfer"
        echo "5. Choose 'Free' plan (750 hours/month)"
        ;;
        
    4)
        echo "🚀 Fly.io Deployment:"
        if command -v flyctl >/dev/null 2>&1; then
            flyctl auth login
            flyctl launch --name pqc-secure-transfer --region ord
            flyctl deploy
        else
            echo "Install flyctl first: curl -L https://fly.io/install.sh | sh"
        fi
        ;;
esac

echo ""
echo "🧪 Test your FREE deployment:"
echo "python test-free-deployment.py ws://YOUR_FREE_URL"
echo ""
echo "🎉 Your quantum-safe system is running FREE in the cloud!"
```

## 💰 **Cost Breakdown (All FREE)**

| Platform | Monthly Cost | Usage Limits | Perfect For |
|----------|--------------|--------------|-------------|
| **Google Cloud Run** | $0 | 2M requests | Production |
| **Railway** | $0 | $5 credit | Development |
| **Render** | $0 | 750 hours | Always-on |
| **Fly.io** | $0 | 3 VMs | Global |
| **Heroku** | $0 | 1000 hours | Prototyping |

## 🎉 **Your Free Quantum-Safe System**

With these free options, you can:

✅ **Deploy immediately** without any cost  
✅ **Handle moderate traffic** (thousands of requests/day)  
✅ **Test with real workloads** up to 1GB files  
✅ **Scale automatically** based on demand  
✅ **Get HTTPS/SSL** automatically  
✅ **Monitor performance** with built-in dashboards  

**Start with Google Cloud Run for the best free experience** - it can easily handle your PQC secure transfer needs without any cost for typical development and small production workloads!

Your quantum-safe federated learning system is now **completely free to deploy and run**! 🚀🆓