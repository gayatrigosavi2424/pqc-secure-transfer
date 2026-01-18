# DigitalOcean App Platform Deployment Guide

Deploy your PQC Secure Transfer System on DigitalOcean App Platform for simple, developer-friendly cloud hosting.

## 🎯 Why DigitalOcean App Platform?

- **Developer-Friendly**: Simple deployment from GitHub
- **Predictable Pricing**: Fixed monthly costs
- **Auto-scaling**: Built-in scaling capabilities
- **Integrated CI/CD**: Automatic deployments from Git

## 📋 Prerequisites

- DigitalOcean account
- GitHub repository (already created)
- DigitalOcean CLI (doctl) installed (optional)

## 🚀 Quick Deployment (2 minutes)

### Method 1: Deploy from GitHub (Web Interface)

1. **Login to DigitalOcean**
   - Go to https://cloud.digitalocean.com/apps
   - Click "Create App"

2. **Connect GitHub Repository**
   - Choose "GitHub" as source
   - Select your repository: `gayatrigosavi2424/pqc-secure-transfer`
   - Branch: `main`
   - Autodeploy: ✅ Enabled

3. **Configure App**
   - **Name**: `pqc-secure-transfer`
   - **Region**: Choose closest to your users
   - **Plan**: Basic ($5/month) or Professional ($12/month)

4. **Environment Variables**
   ```
   PQC_ALGORITHM=Kyber768
   PQC_KEY_STORE_PATH=/app/keys
   STREAM_CHUNK_SIZE=4194304
   ```

5. **Deploy**
   - Click "Create Resources"
   - Wait 3-5 minutes for deployment

### Method 2: Deploy with CLI

```bash
# Install doctl
# macOS: brew install doctl
# Linux: snap install doctl
# Windows: Download from GitHub releases

# Authenticate
doctl auth init

# Create app spec file
cat > app.yaml << EOF
name: pqc-secure-transfer
services:
- name: pqc-server
  source_dir: /
  github:
    repo: gayatrigosavi2424/pqc-secure-transfer
    branch: main
    deploy_on_push: true
  run_command: python examples/server.py --host 0.0.0.0 --port 8080
  environment_slug: python
  instance_count: 1
  instance_size_slug: basic-xxs
  http_port: 8080
  routes:
  - path: /
  envs:
  - key: PQC_ALGORITHM
    value: Kyber768
  - key: PQC_KEY_STORE_PATH
    value: /app/keys
  - key: PORT
    value: "8080"
EOF

# Deploy
doctl apps create --spec app.yaml
```

## 🔧 Advanced Configuration

### Complete App Spec Configuration

Create `digitalocean-app.yaml`:

```yaml
name: pqc-secure-transfer
region: nyc1

services:
- name: pqc-server
  source_dir: /
  github:
    repo: gayatrigosavi2424/pqc-secure-transfer
    branch: main
    deploy_on_push: true
  dockerfile_path: Dockerfile
  instance_count: 1
  instance_size_slug: professional-xs  # $12/month
  http_port: 8765
  
  routes:
  - path: /
  
  envs:
  - key: PQC_ALGORITHM
    value: Kyber768
  - key: PQC_KEY_STORE_PATH
    value: /app/keys
  - key: STREAM_CHUNK_SIZE
    value: "4194304"
  - key: USE_AES_NI
    value: "true"
  
  health_check:
    http_path: /health
    initial_delay_seconds: 60
    period_seconds: 30
    timeout_seconds: 5
    success_threshold: 1
    failure_threshold: 3

- name: pqc-worker
  source_dir: /
  github:
    repo: gayatrigosavi2424/pqc-secure-transfer
    branch: main
  run_command: python examples/worker.py
  instance_count: 2
  instance_size_slug: basic-xs  # $5/month
  
  envs:
  - key: WORKER_MODE
    value: "true"
  - key: PQC_ALGORITHM
    value: Kyber768

databases:
- name: pqc-redis
  engine: REDIS
  version: "6"
  size: db-s-1vcpu-1gb  # $15/month

static_sites:
- name: pqc-dashboard
  source_dir: /dashboard
  github:
    repo: gayatrigosavi2424/pqc-secure-transfer
    branch: main
  build_command: npm run build
  output_dir: dist
  
jobs:
- name: key-rotation
  source_dir: /
  github:
    repo: gayatrigosavi2424/pqc-secure-transfer
    branch: main
  run_command: python scripts/rotate_keys.py
  schedule: "0 2 * * 0"  # Weekly on Sunday at 2 AM
  instance_size_slug: basic-xxs
```

Deploy with:
```bash
doctl apps create --spec digitalocean-app.yaml
```

## 💾 Persistent Storage with Spaces

### Create DigitalOcean Spaces (S3-compatible)

```bash
# Create Spaces bucket for key storage
doctl compute spaces create pqc-secure-keys --region nyc3

# Generate Spaces access keys
doctl compute spaces keys create pqc-spaces-key
```

### Configure App with Spaces

Update your app spec:

```yaml
services:
- name: pqc-server
  # ... other configuration
  envs:
  - key: AWS_ACCESS_KEY_ID
    value: YOUR_SPACES_ACCESS_KEY
  - key: AWS_SECRET_ACCESS_KEY
    value: YOUR_SPACES_SECRET_KEY
  - key: AWS_ENDPOINT_URL
    value: https://nyc3.digitaloceanspaces.com
  - key: S3_BUCKET_NAME
    value: pqc-secure-keys
  - key: PQC_KEY_STORE_PATH
    value: s3://pqc-secure-keys/keys
```

## 🌐 Custom Domain and SSL

### Add Custom Domain

```bash
# Add domain to your app
doctl apps update YOUR_APP_ID --spec app.yaml

# Update app spec with domain
cat >> app.yaml << EOF
domains:
- domain: pqc.yourdomain.com
  type: PRIMARY
  wildcard: false
EOF

# Apply changes
doctl apps update YOUR_APP_ID --spec app.yaml
```

### SSL Certificate (Automatic)

DigitalOcean automatically provisions Let's Encrypt SSL certificates for custom domains.

## 🔐 Environment Variables and Secrets

### Secure Environment Variables

```bash
# Set encrypted environment variables
doctl apps update YOUR_APP_ID --spec - << EOF
name: pqc-secure-transfer
services:
- name: pqc-server
  envs:
  - key: PQC_MASTER_PASSWORD
    value: your-secure-password
    type: SECRET
  - key: DATABASE_URL
    value: postgresql://user:pass@host:port/db
    type: SECRET
EOF
```

### Using DigitalOcean Managed Databases

```yaml
databases:
- name: pqc-postgres
  engine: PG
  version: "13"
  size: db-s-1vcpu-1gb
  num_nodes: 1

services:
- name: pqc-server
  envs:
  - key: DATABASE_URL
    scope: RUN_AND_BUILD_TIME
    type: SECRET
    value: ${pqc-postgres.DATABASE_URL}
```

## 📊 Monitoring and Logging

### Built-in Monitoring

DigitalOcean provides built-in monitoring:
- CPU usage
- Memory usage
- Network I/O
- Request metrics
- Error rates

### Custom Metrics with Prometheus

Create `monitoring/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
- job_name: 'pqc-secure-transfer'
  static_configs:
  - targets: ['pqc-secure-transfer.ondigitalocean.app:8765']
  metrics_path: /metrics
```

Add monitoring service to app spec:

```yaml
services:
- name: prometheus
  source_dir: /monitoring
  dockerfile_path: monitoring/Dockerfile
  instance_count: 1
  instance_size_slug: basic-xs
  http_port: 9090
  routes:
  - path: /monitoring
```

### Log Aggregation

```bash
# View logs
doctl apps logs YOUR_APP_ID --type run

# Follow logs in real-time
doctl apps logs YOUR_APP_ID --type run --follow

# Get build logs
doctl apps logs YOUR_APP_ID --type build
```

## 🚀 CI/CD and Deployment

### Automatic Deployments

DigitalOcean automatically deploys when you push to the connected branch:

```bash
# Make changes and push
git add .
git commit -m "Update PQC configuration"
git push origin main

# Deployment starts automatically
# Monitor progress in DigitalOcean dashboard
```

### Manual Deployments

```bash
# Trigger manual deployment
doctl apps create-deployment YOUR_APP_ID

# Check deployment status
doctl apps get-deployment YOUR_APP_ID DEPLOYMENT_ID
```

### Environment-Specific Deployments

Create separate apps for different environments:

```bash
# Production app
doctl apps create --spec production-app.yaml

# Staging app
doctl apps create --spec staging-app.yaml

# Development app
doctl apps create --spec development-app.yaml
```

## 💰 Cost Optimization

### Pricing Tiers

| Plan | vCPU | RAM | Price/Month | Best For |
|------|------|-----|-------------|----------|
| Basic XXS | 0.25 | 512MB | $5 | Development |
| Basic XS | 0.5 | 1GB | $10 | Small production |
| Professional XS | 1 | 1GB | $12 | Production |
| Professional S | 1 | 2GB | $24 | High traffic |

### Cost Estimation Example

For a production setup:
- **App (Professional XS)**: $12/month
- **Database (1GB)**: $15/month
- **Spaces (250GB)**: $5/month
- **Total**: ~$32/month

### Optimization Tips

```yaml
# Use smaller instances for workers
services:
- name: pqc-worker
  instance_size_slug: basic-xxs  # $5 instead of $12
  instance_count: 1

# Scale based on usage
- name: pqc-server
  instance_count: 1  # Start with 1, scale up as needed
```

## 🧪 Testing and Validation

### Health Checks

Add health check endpoint to your server:

```python
# Add to examples/server.py
@app.route('/health')
def health_check():
    return {'status': 'healthy', 'timestamp': time.time()}
```

Update app spec:

```yaml
services:
- name: pqc-server
  health_check:
    http_path: /health
    initial_delay_seconds: 60
    period_seconds: 30
```

### Load Testing

```bash
# Get app URL
APP_URL=$(doctl apps get YOUR_APP_ID --format URL --no-header)

# Test with curl
curl $APP_URL/health

# Load test with Apache Bench
ab -n 1000 -c 10 $APP_URL/health

# Test file transfer
python examples/client.py --server $APP_URL --create-test 10
```

## 🔧 Troubleshooting

### Common Issues

1. **Build Failures**
   ```bash
   # Check build logs
   doctl apps logs YOUR_APP_ID --type build
   
   # Common fix: Update Dockerfile
   # Ensure all dependencies are in requirements.txt
   ```

2. **Runtime Errors**
   ```bash
   # Check runtime logs
   doctl apps logs YOUR_APP_ID --type run --follow
   
   # Check environment variables
   doctl apps get YOUR_APP_ID
   ```

3. **Port Configuration**
   ```yaml
   # Ensure port matches your application
   services:
   - name: pqc-server
     http_port: 8765  # Must match your server port
   ```

### Debug Mode

```yaml
services:
- name: pqc-server
  envs:
  - key: DEBUG
    value: "true"
  - key: LOG_LEVEL
    value: "DEBUG"
```

## 🚀 One-Click Deployment

### GitHub Actions Integration

Create `.github/workflows/deploy-digitalocean.yml`:

```yaml
name: Deploy to DigitalOcean

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Install doctl
      uses: digitalocean/action-doctl@v2
      with:
        token: ${{ secrets.DIGITALOCEAN_ACCESS_TOKEN }}
    
    - name: Update app
      run: |
        doctl apps update ${{ secrets.APP_ID }} --spec digitalocean-app.yaml
```

### Quick Deploy Script

Create `deploy-to-digitalocean.sh`:

```bash
#!/bin/bash

# Configuration
APP_NAME="pqc-secure-transfer"
REGION="nyc1"

echo "🚀 Deploying to DigitalOcean App Platform..."

# Check if doctl is installed
if ! command -v doctl &> /dev/null; then
    echo "Installing doctl..."
    # Add installation commands for your OS
fi

# Create app spec
cat > app.yaml << EOF
name: $APP_NAME
region: $REGION
services:
- name: pqc-server
  source_dir: /
  github:
    repo: gayatrigosavi2424/pqc-secure-transfer
    branch: main
    deploy_on_push: true
  dockerfile_path: Dockerfile
  instance_count: 1
  instance_size_slug: professional-xs
  http_port: 8765
  routes:
  - path: /
  envs:
  - key: PQC_ALGORITHM
    value: Kyber768
  health_check:
    http_path: /health
EOF

# Create app
APP_ID=$(doctl apps create --spec app.yaml --format ID --no-header)

echo "✅ App created with ID: $APP_ID"
echo "🔗 Monitor deployment: https://cloud.digitalocean.com/apps/$APP_ID"

# Wait for deployment
echo "⏳ Waiting for deployment to complete..."
doctl apps get $APP_ID --wait

# Get app URL
APP_URL=$(doctl apps get $APP_ID --format LiveURL --no-header)

echo "🎉 Deployment complete!"
echo "🔗 App URL: $APP_URL"
echo "🧪 Test with: python examples/client.py --server $APP_URL --create-test 10"
```

Run with:
```bash
chmod +x deploy-to-digitalocean.sh
./deploy-to-digitalocean.sh
```

## 📈 Scaling Configuration

### Auto-scaling

```yaml
services:
- name: pqc-server
  instance_count: 1
  autoscaling:
    min_instance_count: 1
    max_instance_count: 5
    metrics:
    - type: cpu
      target: 70
```

### Load Balancing

DigitalOcean automatically load balances between multiple instances.

Your PQC Secure Transfer System is now running on DigitalOcean App Platform with automatic deployments! 🚀

**Next**: Check out [Kubernetes deployment](kubernetes.md) for enterprise-scale orchestration.