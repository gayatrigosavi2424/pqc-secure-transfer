# Cloud Deployment Guide for PQC Secure Transfer System

This guide covers deploying your quantum-safe secure transfer system on major cloud platforms.

## 🌐 Deployment Options Overview

| Platform | Best For | Complexity | Cost | Scalability |
|----------|----------|------------|------|-------------|
| **AWS ECS** | Production, Auto-scaling | Medium | $$ | High |
| **Google Cloud Run** | Serverless, Easy start | Low | $ | Medium |
| **Azure Container Instances** | Simple deployment | Low | $ | Medium |
| **DigitalOcean App Platform** | Developer-friendly | Low | $ | Medium |
| **Kubernetes (Any Cloud)** | Enterprise, Full control | High | $$$ | Very High |
| **Railway/Render** | Quick prototyping | Very Low | $ | Low |

## 📋 Pre-Deployment Checklist

- [ ] Docker image builds successfully
- [ ] Environment variables configured
- [ ] SSL/TLS certificates ready (for production)
- [ ] Monitoring and logging configured
- [ ] Security groups/firewall rules planned
- [ ] Backup strategy for keys and data

## 🚀 Quick Start Options

Choose your preferred deployment method:

1. **[AWS ECS Deployment](aws-ecs.md)** - Production-ready with auto-scaling
2. **[Google Cloud Run](google-cloud-run.md)** - Serverless, pay-per-use  
3. **[Azure Container Instances](azure-container-instances.md)** - Simple container hosting
4. **[DigitalOcean App Platform](digitalocean.md)** - Developer-friendly platform
5. **[Kubernetes](kubernetes.md)** - Full container orchestration
6. **[Railway/Render](railway-render.md)** - Instant deployment from GitHub

## ⚡ One-Click Deployments

### Google Cloud Run (Fastest)
```bash
gcloud run deploy pqc-secure-transfer \
    --source https://github.com/gayatrigosavi2424/pqc-secure-transfer \
    --region us-central1 \
    --allow-unauthenticated
```

### DigitalOcean App Platform
```bash
doctl apps create --spec - << EOF
name: pqc-secure-transfer
services:
- name: pqc-server
  github:
    repo: gayatrigosavi2424/pqc-secure-transfer
    branch: main
  instance_size_slug: professional-xs
EOF
```

### Azure Container Instances
```bash
az container create \
    --resource-group pqc-rg \
    --name pqc-secure-transfer \
    --image gayatrigosavi2424/pqc-secure-transfer \
    --dns-name-label pqc-secure-transfer \
    --ports 8765
```