# Google Cloud Run Deployment Guide

Deploy your PQC Secure Transfer System on Google Cloud Run for serverless, auto-scaling deployment.

## 🎯 Why Google Cloud Run?

- **Serverless**: Pay only for requests, scale to zero
- **Easy Deployment**: Deploy directly from source code
- **Auto-scaling**: Handles traffic spikes automatically
- **Cost-effective**: Great for variable workloads

## 📋 Prerequisites

- Google Cloud account with billing enabled
- Google Cloud SDK (gcloud) installed
- Docker installed locally

## 🚀 Quick Deployment (5 minutes)

### Method 1: Deploy from Source (Recommended)

```bash
# 1. Login to Google Cloud
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# 2. Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable containerregistry.googleapis.com

# 3. Deploy directly from source
gcloud run deploy pqc-secure-transfer \
    --source . \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --port 8765 \
    --memory 2Gi \
    --cpu 2 \
    --max-instances 10 \
    --set-env-vars="PQC_ALGORITHM=Kyber768,PQC_KEY_STORE_PATH=/app/keys"
```

### Method 2: Deploy from Container Registry

```bash
# 1. Build and push to Google Container Registry
docker build -t gcr.io/YOUR_PROJECT_ID/pqc-secure-transfer .
docker push gcr.io/YOUR_PROJECT_ID/pqc-secure-transfer

# 2. Deploy to Cloud Run
gcloud run deploy pqc-secure-transfer \
    --image gcr.io/YOUR_PROJECT_ID/pqc-secure-transfer \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --port 8765 \
    --memory 2Gi \
    --cpu 2
```

## 🔧 Advanced Configuration

### Cloud Run Service YAML

Create `cloudrun-service.yaml`:

```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: pqc-secure-transfer
  annotations:
    run.googleapis.com/ingress: all
    run.googleapis.com/execution-environment: gen2
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/maxScale: "10"
        autoscaling.knative.dev/minScale: "0"
        run.googleapis.com/cpu-throttling: "false"
        run.googleapis.com/memory: "2Gi"
        run.googleapis.com/cpu: "2"
    spec:
      containerConcurrency: 100
      timeoutSeconds: 3600
      containers:
      - image: gcr.io/YOUR_PROJECT_ID/pqc-secure-transfer
        ports:
        - containerPort: 8765
        env:
        - name: PQC_ALGORITHM
          value: "Kyber768"
        - name: PQC_KEY_STORE_PATH
          value: "/app/keys"
        - name: STREAM_CHUNK_SIZE
          value: "4194304"
        resources:
          limits:
            cpu: "2"
            memory: "2Gi"
        volumeMounts:
        - name: keys-volume
          mountPath: /app/keys
      volumes:
      - name: keys-volume
        csi:
          driver: gcsfuse.run.googleapis.com
          volumeAttributes:
            bucketName: YOUR_BUCKET_NAME
```

Deploy with:
```bash
gcloud run services replace cloudrun-service.yaml --region us-central1
```

## 💾 Persistent Storage with Cloud Storage

### Create Storage Bucket for Keys

```bash
# Create bucket for key storage
gsutil mb gs://YOUR_PROJECT_ID-pqc-keys

# Enable versioning for key backup
gsutil versioning set on gs://YOUR_PROJECT_ID-pqc-keys

# Set lifecycle policy
cat > lifecycle.json << EOF
{
  "rule": [
    {
      "action": {"type": "Delete"},
      "condition": {"age": 365}
    }
  ]
}
EOF

gsutil lifecycle set lifecycle.json gs://YOUR_PROJECT_ID-pqc-keys
```

### Mount Storage to Cloud Run

```bash
# Deploy with Cloud Storage mount
gcloud run deploy pqc-secure-transfer \
    --source . \
    --region us-central1 \
    --allow-unauthenticated \
    --add-volume name=keys-volume,type=cloud-storage,bucket=YOUR_PROJECT_ID-pqc-keys \
    --add-volume-mount volume=keys-volume,mount-path=/app/keys \
    --memory 2Gi \
    --cpu 2
```

## 🌐 Custom Domain and SSL

### Set up Custom Domain

```bash
# Map custom domain
gcloud run domain-mappings create \
    --service pqc-secure-transfer \
    --domain pqc.yourdomain.com \
    --region us-central1

# Verify domain ownership (follow instructions from above command)
# Add DNS records as instructed
```

### SSL Certificate (Automatic)

Cloud Run automatically provisions SSL certificates for custom domains.

## 🔐 Authentication and Security

### Enable IAM Authentication

```bash
# Deploy with authentication required
gcloud run deploy pqc-secure-transfer \
    --source . \
    --region us-central1 \
    --no-allow-unauthenticated

# Grant access to specific users
gcloud run services add-iam-policy-binding pqc-secure-transfer \
    --member="user:user@example.com" \
    --role="roles/run.invoker" \
    --region us-central1
```

### Service Account with Minimal Permissions

```bash
# Create service account
gcloud iam service-accounts create pqc-service-account \
    --display-name="PQC Secure Transfer Service Account"

# Grant minimal permissions
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:pqc-service-account@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"

# Deploy with service account
gcloud run deploy pqc-secure-transfer \
    --source . \
    --region us-central1 \
    --service-account pqc-service-account@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

## 📊 Monitoring and Logging

### Enable Cloud Monitoring

```bash
# Cloud Run automatically sends metrics to Cloud Monitoring
# View metrics at: https://console.cloud.google.com/monitoring

# Create custom dashboard
gcloud monitoring dashboards create --config-from-file=dashboard.json
```

### Custom Metrics Dashboard

Create `dashboard.json`:

```json
{
  "displayName": "PQC Secure Transfer Dashboard",
  "mosaicLayout": {
    "tiles": [
      {
        "width": 6,
        "height": 4,
        "widget": {
          "title": "Request Count",
          "xyChart": {
            "dataSets": [
              {
                "timeSeriesQuery": {
                  "timeSeriesFilter": {
                    "filter": "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"pqc-secure-transfer\"",
                    "aggregation": {
                      "alignmentPeriod": "60s",
                      "perSeriesAligner": "ALIGN_RATE"
                    }
                  }
                }
              }
            ]
          }
        }
      }
    ]
  }
}
```

### Log Analysis

```bash
# View logs
gcloud logs read "resource.type=cloud_run_revision AND resource.labels.service_name=pqc-secure-transfer" \
    --limit 50 \
    --format json

# Create log-based metric
gcloud logging metrics create pqc_transfer_count \
    --description="Count of PQC file transfers" \
    --log-filter='resource.type="cloud_run_revision" AND resource.labels.service_name="pqc-secure-transfer" AND "Transfer successful"'
```

## 🚀 CI/CD with Cloud Build

### Automated Deployment

Create `.gcloudignore`:
```
.git
.gitignore
README.md
Dockerfile
.dockerignore
node_modules
npm-debug.log
```

Create `cloudbuild.yaml`:

```yaml
steps:
  # Build the container image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/pqc-secure-transfer:$COMMIT_SHA', '.']
  
  # Push the container image to Container Registry
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/pqc-secure-transfer:$COMMIT_SHA']
  
  # Deploy container image to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
    - 'run'
    - 'deploy'
    - 'pqc-secure-transfer'
    - '--image'
    - 'gcr.io/$PROJECT_ID/pqc-secure-transfer:$COMMIT_SHA'
    - '--region'
    - 'us-central1'
    - '--platform'
    - 'managed'
    - '--allow-unauthenticated'

images:
  - 'gcr.io/$PROJECT_ID/pqc-secure-transfer:$COMMIT_SHA'
```

### GitHub Integration

```bash
# Connect GitHub repository
gcloud builds triggers create github \
    --repo-name=pqc-secure-transfer \
    --repo-owner=gayatrigosavi2424 \
    --branch-pattern="^main$" \
    --build-config=cloudbuild.yaml
```

## 🔧 Environment-Specific Deployments

### Development Environment

```bash
gcloud run deploy pqc-secure-transfer-dev \
    --source . \
    --region us-central1 \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1 \
    --max-instances 2 \
    --set-env-vars="ENVIRONMENT=development"
```

### Production Environment

```bash
gcloud run deploy pqc-secure-transfer-prod \
    --source . \
    --region us-central1 \
    --no-allow-unauthenticated \
    --memory 4Gi \
    --cpu 4 \
    --max-instances 100 \
    --min-instances 1 \
    --set-env-vars="ENVIRONMENT=production" \
    --service-account pqc-service-account@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

## 💰 Cost Optimization

### Pricing Model
- **CPU**: $0.00002400 per vCPU-second
- **Memory**: $0.00000250 per GiB-second
- **Requests**: $0.40 per million requests
- **Free Tier**: 2 million requests, 400,000 GiB-seconds, 200,000 vCPU-seconds per month

### Cost Estimation Example

For 1000 requests/day with 2-second average response time:
- Monthly requests: ~30,000
- CPU time: 30,000 × 2s × 2 vCPU = 120,000 vCPU-seconds
- Memory time: 30,000 × 2s × 2 GiB = 120,000 GiB-seconds

**Monthly cost: ~$3-5** (mostly within free tier)

### Optimization Tips

```bash
# Use minimum resources for development
gcloud run deploy pqc-secure-transfer \
    --cpu 1 \
    --memory 512Mi \
    --max-instances 5

# Enable CPU throttling for cost savings
gcloud run services update pqc-secure-transfer \
    --cpu-throttling \
    --region us-central1
```

## 🧪 Testing Deployment

### Health Check

```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe pqc-secure-transfer \
    --region us-central1 \
    --format 'value(status.url)')

# Test health endpoint
curl $SERVICE_URL/health

# Test file transfer
python examples/client.py --server $SERVICE_URL --create-test 10
```

### Load Testing

```bash
# Install Apache Bench
sudo apt-get install apache2-utils

# Run load test
ab -n 100 -c 10 $SERVICE_URL/health
```

## 🚀 One-Click Deployment Script

Create `deploy-to-cloudrun.sh`:

```bash
#!/bin/bash

# Configuration
PROJECT_ID="your-project-id"
SERVICE_NAME="pqc-secure-transfer"
REGION="us-central1"

# Set project
gcloud config set project $PROJECT_ID

# Enable APIs
echo "Enabling required APIs..."
gcloud services enable run.googleapis.com cloudbuild.googleapis.com

# Deploy
echo "Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
    --source . \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --port 8765 \
    --memory 2Gi \
    --cpu 2 \
    --max-instances 10 \
    --set-env-vars="PQC_ALGORITHM=Kyber768"

# Get URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
    --region $REGION \
    --format 'value(status.url)')

echo "🚀 Deployment complete!"
echo "Service URL: $SERVICE_URL"
echo "Test with: python examples/client.py --server $SERVICE_URL --create-test 10"
```

Run with:
```bash
chmod +x deploy-to-cloudrun.sh
./deploy-to-cloudrun.sh
```

## 📈 Scaling Configuration

### Auto-scaling Settings

```bash
# Configure auto-scaling
gcloud run services update pqc-secure-transfer \
    --min-instances 1 \
    --max-instances 100 \
    --concurrency 80 \
    --cpu-throttling \
    --region us-central1
```

### Traffic Splitting (Blue/Green Deployment)

```bash
# Deploy new version
gcloud run deploy pqc-secure-transfer \
    --source . \
    --region us-central1 \
    --no-traffic

# Split traffic between versions
gcloud run services update-traffic pqc-secure-transfer \
    --to-revisions pqc-secure-transfer-00001-abc=50,pqc-secure-transfer-00002-def=50 \
    --region us-central1
```

Your PQC Secure Transfer System is now running on Google Cloud Run with serverless scalability! 🚀

**Next**: Check out [Azure Container Instances](azure-container-instances.md) for another cloud option.