# Azure Container Instances Deployment Guide

Deploy your PQC Secure Transfer System on Azure Container Instances (ACI) for simple, serverless container hosting.

## 🎯 Why Azure Container Instances?

- **Serverless Containers**: No VM management required
- **Fast Startup**: Containers start in seconds
- **Pay-per-second**: Cost-effective for variable workloads
- **Simple Deployment**: Easy container hosting without orchestration

## 📋 Prerequisites

- Azure account with active subscription
- Azure CLI installed and configured
- Docker installed locally

## 🚀 Quick Deployment (3 minutes)

### Method 1: Deploy from Azure Container Registry

```bash
# 1. Login to Azure
az login
az account set --subscription "Your Subscription Name"

# 2. Create resource group
az group create --name pqc-secure-transfer-rg --location eastus

# 3. Create Azure Container Registry
az acr create --resource-group pqc-secure-transfer-rg \
    --name pqcsecuretransfer \
    --sku Basic \
    --admin-enabled true

# 4. Build and push image
az acr build --registry pqcsecuretransfer \
    --image pqc-secure-transfer:latest .

# 5. Deploy to Container Instances
az container create \
    --resource-group pqc-secure-transfer-rg \
    --name pqc-secure-transfer \
    --image pqcsecuretransfer.azurecr.io/pqc-secure-transfer:latest \
    --registry-login-server pqcsecuretransfer.azurecr.io \
    --registry-username pqcsecuretransfer \
    --registry-password $(az acr credential show --name pqcsecuretransfer --query "passwords[0].value" -o tsv) \
    --dns-name-label pqc-secure-transfer-$(date +%s) \
    --ports 8765 \
    --cpu 2 \
    --memory 4 \
    --environment-variables PQC_ALGORITHM=Kyber768 PQC_KEY_STORE_PATH=/app/keys \
    --restart-policy Always
```

### Method 2: Deploy from Docker Hub

```bash
# 1. Build and push to Docker Hub
docker build -t yourusername/pqc-secure-transfer .
docker push yourusername/pqc-secure-transfer

# 2. Deploy to ACI
az container create \
    --resource-group pqc-secure-transfer-rg \
    --name pqc-secure-transfer \
    --image yourusername/pqc-secure-transfer:latest \
    --dns-name-label pqc-secure-transfer-unique \
    --ports 8765 \
    --cpu 2 \
    --memory 4 \
    --environment-variables PQC_ALGORITHM=Kyber768 \
    --restart-policy Always
```

## 🔧 Advanced Configuration

### ARM Template Deployment

Create `azure-template.json`:

```json
{
    "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
    "contentVersion": "1.0.0.0",
    "parameters": {
        "containerName": {
            "type": "string",
            "defaultValue": "pqc-secure-transfer"
        },
        "imageName": {
            "type": "string",
            "defaultValue": "pqcsecuretransfer.azurecr.io/pqc-secure-transfer:latest"
        },
        "dnsNameLabel": {
            "type": "string",
            "defaultValue": "[concat('pqc-', uniqueString(resourceGroup().id))]"
        }
    },
    "resources": [
        {
            "type": "Microsoft.ContainerInstance/containerGroups",
            "apiVersion": "2021-09-01",
            "name": "[parameters('containerName')]",
            "location": "[resourceGroup().location]",
            "properties": {
                "containers": [
                    {
                        "name": "[parameters('containerName')]",
                        "properties": {
                            "image": "[parameters('imageName')]",
                            "ports": [
                                {
                                    "port": 8765,
                                    "protocol": "TCP"
                                }
                            ],
                            "environmentVariables": [
                                {
                                    "name": "PQC_ALGORITHM",
                                    "value": "Kyber768"
                                },
                                {
                                    "name": "PQC_KEY_STORE_PATH",
                                    "value": "/app/keys"
                                }
                            ],
                            "resources": {
                                "requests": {
                                    "cpu": 2,
                                    "memoryInGB": 4
                                }
                            },
                            "volumeMounts": [
                                {
                                    "name": "keys-volume",
                                    "mountPath": "/app/keys"
                                }
                            ]
                        }
                    }
                ],
                "osType": "Linux",
                "restartPolicy": "Always",
                "ipAddress": {
                    "type": "Public",
                    "dnsNameLabel": "[parameters('dnsNameLabel')]",
                    "ports": [
                        {
                            "port": 8765,
                            "protocol": "TCP"
                        }
                    ]
                },
                "volumes": [
                    {
                        "name": "keys-volume",
                        "azureFile": {
                            "shareName": "pqc-keys",
                            "storageAccountName": "[variables('storageAccountName')]",
                            "storageAccountKey": "[listKeys(resourceId('Microsoft.Storage/storageAccounts', variables('storageAccountName')), '2021-04-01').keys[0].value]"
                        }
                    }
                ]
            },
            "dependsOn": [
                "[resourceId('Microsoft.Storage/storageAccounts', variables('storageAccountName'))]"
            ]
        },
        {
            "type": "Microsoft.Storage/storageAccounts",
            "apiVersion": "2021-04-01",
            "name": "[variables('storageAccountName')]",
            "location": "[resourceGroup().location]",
            "sku": {
                "name": "Standard_LRS"
            },
            "kind": "StorageV2",
            "properties": {
                "accessTier": "Hot"
            }
        }
    ],
    "variables": {
        "storageAccountName": "[concat('pqcstorage', uniqueString(resourceGroup().id))]"
    },
    "outputs": {
        "containerIPv4Address": {
            "type": "string",
            "value": "[reference(resourceId('Microsoft.ContainerInstance/containerGroups', parameters('containerName'))).ipAddress.ip]"
        },
        "containerFQDN": {
            "type": "string",
            "value": "[reference(resourceId('Microsoft.ContainerInstance/containerGroups', parameters('containerName'))).ipAddress.fqdn]"
        }
    }
}
```

Deploy with:
```bash
az deployment group create \
    --resource-group pqc-secure-transfer-rg \
    --template-file azure-template.json \
    --parameters containerName=pqc-secure-transfer
```

## 💾 Persistent Storage with Azure Files

### Create Storage Account and File Share

```bash
# Create storage account
STORAGE_ACCOUNT_NAME="pqcstorage$(date +%s)"
az storage account create \
    --resource-group pqc-secure-transfer-rg \
    --name $STORAGE_ACCOUNT_NAME \
    --location eastus \
    --sku Standard_LRS

# Get storage key
STORAGE_KEY=$(az storage account keys list \
    --resource-group pqc-secure-transfer-rg \
    --account-name $STORAGE_ACCOUNT_NAME \
    --query "[0].value" --output tsv)

# Create file share
az storage share create \
    --name pqc-keys \
    --account-name $STORAGE_ACCOUNT_NAME \
    --account-key $STORAGE_KEY
```

### Deploy with Persistent Storage

```bash
az container create \
    --resource-group pqc-secure-transfer-rg \
    --name pqc-secure-transfer \
    --image pqcsecuretransfer.azurecr.io/pqc-secure-transfer:latest \
    --registry-login-server pqcsecuretransfer.azurecr.io \
    --registry-username pqcsecuretransfer \
    --registry-password $(az acr credential show --name pqcsecuretransfer --query "passwords[0].value" -o tsv) \
    --dns-name-label pqc-secure-transfer-$(date +%s) \
    --ports 8765 \
    --cpu 2 \
    --memory 4 \
    --azure-file-volume-account-name $STORAGE_ACCOUNT_NAME \
    --azure-file-volume-account-key $STORAGE_KEY \
    --azure-file-volume-share-name pqc-keys \
    --azure-file-volume-mount-path /app/keys \
    --environment-variables PQC_ALGORITHM=Kyber768 PQC_KEY_STORE_PATH=/app/keys
```

## 🌐 Load Balancing with Application Gateway

### Create Application Gateway

```bash
# Create virtual network
az network vnet create \
    --resource-group pqc-secure-transfer-rg \
    --name pqc-vnet \
    --address-prefix 10.0.0.0/16 \
    --subnet-name pqc-subnet \
    --subnet-prefix 10.0.1.0/24

# Create public IP
az network public-ip create \
    --resource-group pqc-secure-transfer-rg \
    --name pqc-gateway-ip \
    --allocation-method Static \
    --sku Standard

# Create Application Gateway
az network application-gateway create \
    --name pqc-app-gateway \
    --location eastus \
    --resource-group pqc-secure-transfer-rg \
    --vnet-name pqc-vnet \
    --subnet pqc-subnet \
    --capacity 2 \
    --sku Standard_v2 \
    --http-settings-cookie-based-affinity Disabled \
    --frontend-port 80 \
    --http-settings-port 8765 \
    --http-settings-protocol Http \
    --public-ip-address pqc-gateway-ip
```

## 🔐 Security Configuration

### Network Security Groups

```bash
# Create network security group
az network nsg create \
    --resource-group pqc-secure-transfer-rg \
    --name pqc-nsg

# Allow HTTPS traffic
az network nsg rule create \
    --resource-group pqc-secure-transfer-rg \
    --nsg-name pqc-nsg \
    --name AllowHTTPS \
    --protocol tcp \
    --priority 1000 \
    --destination-port-range 8765 \
    --access allow
```

### Key Vault Integration

```bash
# Create Key Vault
az keyvault create \
    --name pqc-keyvault-$(date +%s) \
    --resource-group pqc-secure-transfer-rg \
    --location eastus

# Store secrets
az keyvault secret set \
    --vault-name pqc-keyvault-$(date +%s) \
    --name "pqc-master-key" \
    --value "your-secure-master-key"

# Deploy with Key Vault reference
az container create \
    --resource-group pqc-secure-transfer-rg \
    --name pqc-secure-transfer \
    --image pqcsecuretransfer.azurecr.io/pqc-secure-transfer:latest \
    --secure-environment-variables PQC_MASTER_KEY="$(az keyvault secret show --vault-name pqc-keyvault-$(date +%s) --name pqc-master-key --query value -o tsv)"
```

## 📊 Monitoring and Logging

### Enable Container Insights

```bash
# Create Log Analytics workspace
az monitor log-analytics workspace create \
    --resource-group pqc-secure-transfer-rg \
    --workspace-name pqc-logs

# Get workspace ID
WORKSPACE_ID=$(az monitor log-analytics workspace show \
    --resource-group pqc-secure-transfer-rg \
    --workspace-name pqc-logs \
    --query customerId -o tsv)

# Get workspace key
WORKSPACE_KEY=$(az monitor log-analytics workspace get-shared-keys \
    --resource-group pqc-secure-transfer-rg \
    --workspace-name pqc-logs \
    --query primarySharedKey -o tsv)

# Deploy with logging
az container create \
    --resource-group pqc-secure-transfer-rg \
    --name pqc-secure-transfer \
    --image pqcsecuretransfer.azurecr.io/pqc-secure-transfer:latest \
    --log-analytics-workspace $WORKSPACE_ID \
    --log-analytics-workspace-key $WORKSPACE_KEY
```

### Custom Metrics and Alerts

```bash
# Create action group for alerts
az monitor action-group create \
    --resource-group pqc-secure-transfer-rg \
    --name pqc-alerts \
    --short-name pqc-alerts \
    --email admin admin@yourdomain.com

# Create CPU alert
az monitor metrics alert create \
    --name "PQC High CPU" \
    --resource-group pqc-secure-transfer-rg \
    --scopes $(az container show --resource-group pqc-secure-transfer-rg --name pqc-secure-transfer --query id -o tsv) \
    --condition "avg Percentage CPU > 80" \
    --description "High CPU usage alert" \
    --evaluation-frequency 1m \
    --window-size 5m \
    --action pqc-alerts
```

## 🚀 CI/CD with Azure DevOps

### Azure Pipeline YAML

Create `azure-pipelines.yml`:

```yaml
trigger:
- main

variables:
  imageRepository: 'pqc-secure-transfer'
  containerRegistry: 'pqcsecuretransfer.azurecr.io'
  dockerfilePath: '$(Build.SourcesDirectory)/Dockerfile'
  tag: '$(Build.BuildId)'
  resourceGroup: 'pqc-secure-transfer-rg'
  containerName: 'pqc-secure-transfer'

stages:
- stage: Build
  displayName: Build and push stage
  jobs:
  - job: Build
    displayName: Build
    pool:
      vmImage: ubuntu-latest
    steps:
    - task: Docker@2
      displayName: Build and push image
      inputs:
        command: buildAndPush
        repository: $(imageRepository)
        dockerfile: $(dockerfilePath)
        containerRegistry: $(dockerRegistryServiceConnection)
        tags: |
          $(tag)
          latest

- stage: Deploy
  displayName: Deploy stage
  dependsOn: Build
  jobs:
  - deployment: Deploy
    displayName: Deploy
    pool:
      vmImage: ubuntu-latest
    environment: 'production'
    strategy:
      runOnce:
        deploy:
          steps:
          - task: AzureCLI@2
            displayName: Deploy to Container Instances
            inputs:
              azureSubscription: $(azureServiceConnection)
              scriptType: bash
              scriptLocation: inlineScript
              inlineScript: |
                az container delete \
                  --resource-group $(resourceGroup) \
                  --name $(containerName) \
                  --yes || true
                
                az container create \
                  --resource-group $(resourceGroup) \
                  --name $(containerName) \
                  --image $(containerRegistry)/$(imageRepository):$(tag) \
                  --registry-login-server $(containerRegistry) \
                  --registry-username $(registryUsername) \
                  --registry-password $(registryPassword) \
                  --dns-name-label pqc-secure-transfer-prod \
                  --ports 8765 \
                  --cpu 2 \
                  --memory 4 \
                  --environment-variables PQC_ALGORITHM=Kyber768 \
                  --restart-policy Always
```

## 💰 Cost Optimization

### Pricing Model (East US)
- **vCPU**: $0.0000125 per vCPU-second
- **Memory**: $0.0000014 per GB-second
- **No additional charges** for container instances

### Cost Estimation Example

For 2 vCPU, 4GB RAM running 24/7:
- Monthly vCPU cost: 2 × 2,592,000 seconds × $0.0000125 = $64.80
- Monthly memory cost: 4 × 2,592,000 seconds × $0.0000014 = $14.51
- **Total monthly cost: ~$79**

### Cost Optimization Tips

```bash
# Use smaller instances for development
az container create \
    --cpu 1 \
    --memory 2 \
    # ... other parameters

# Use spot instances (when available)
az container create \
    --priority Spot \
    # ... other parameters
```

## 🧪 Testing and Validation

### Health Check Script

Create `test-deployment.sh`:

```bash
#!/bin/bash

# Get container FQDN
FQDN=$(az container show \
    --resource-group pqc-secure-transfer-rg \
    --name pqc-secure-transfer \
    --query ipAddress.fqdn -o tsv)

echo "Testing deployment at: http://$FQDN:8765"

# Test health endpoint
curl -f http://$FQDN:8765/health || echo "Health check failed"

# Test file transfer
python examples/client.py --server ws://$FQDN:8765 --create-test 10
```

### Load Testing

```bash
# Install Azure Load Testing CLI extension
az extension add --name load

# Create load test
az load test create \
    --name pqc-load-test \
    --resource-group pqc-secure-transfer-rg \
    --load-test-config-file loadtest.yaml
```

## 🚀 One-Click Deployment Script

Create `deploy-to-azure.sh`:

```bash
#!/bin/bash

# Configuration
RESOURCE_GROUP="pqc-secure-transfer-rg"
LOCATION="eastus"
CONTAINER_NAME="pqc-secure-transfer"
ACR_NAME="pqcsecuretransfer$(date +%s)"

echo "🚀 Deploying PQC Secure Transfer to Azure..."

# Create resource group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create ACR
az acr create --resource-group $RESOURCE_GROUP \
    --name $ACR_NAME \
    --sku Basic \
    --admin-enabled true

# Build and push
az acr build --registry $ACR_NAME \
    --image pqc-secure-transfer:latest .

# Get ACR credentials
ACR_SERVER="$ACR_NAME.azurecr.io"
ACR_USERNAME=$ACR_NAME
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv)

# Deploy container
az container create \
    --resource-group $RESOURCE_GROUP \
    --name $CONTAINER_NAME \
    --image $ACR_SERVER/pqc-secure-transfer:latest \
    --registry-login-server $ACR_SERVER \
    --registry-username $ACR_USERNAME \
    --registry-password $ACR_PASSWORD \
    --dns-name-label pqc-secure-transfer-$(date +%s) \
    --ports 8765 \
    --cpu 2 \
    --memory 4 \
    --environment-variables PQC_ALGORITHM=Kyber768 \
    --restart-policy Always

# Get FQDN
FQDN=$(az container show \
    --resource-group $RESOURCE_GROUP \
    --name $CONTAINER_NAME \
    --query ipAddress.fqdn -o tsv)

echo "✅ Deployment complete!"
echo "Service URL: http://$FQDN:8765"
echo "Test with: python examples/client.py --server ws://$FQDN:8765 --create-test 10"
```

Run with:
```bash
chmod +x deploy-to-azure.sh
./deploy-to-azure.sh
```

Your PQC Secure Transfer System is now running on Azure Container Instances! 🚀

**Next**: Check out [DigitalOcean App Platform](digitalocean.md) for another simple deployment option.