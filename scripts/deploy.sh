#!/bin/bash

# PQC Secure Transfer Deployment Script
set -e

ENVIRONMENT=${1:-dev}
IMAGE_TAG=${2:-latest}
CLOUD_PROVIDER=${3:-aws}

echo "Deploying PQC Secure Transfer to $ENVIRONMENT environment using $CLOUD_PROVIDER"

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|prod)$ ]]; then
    echo "Error: Environment must be dev, staging, or prod"
    exit 1
fi

# Validate cloud provider
if [[ ! "$CLOUD_PROVIDER" =~ ^(aws|gcp|azure)$ ]]; then
    echo "Error: Cloud provider must be aws, gcp, or azure"
    exit 1
fi

# Set configuration based on environment
case $ENVIRONMENT in
    dev)
        INSTANCE_COUNT=1
        INSTANCE_SIZE="small"
        ;;
    staging)
        INSTANCE_COUNT=2
        INSTANCE_SIZE="medium"
        ;;
    prod)
        INSTANCE_COUNT=5
        INSTANCE_SIZE="large"
        ;;
esac

echo "Configuration: $INSTANCE_COUNT instances of size $INSTANCE_SIZE"

# Deploy based on cloud provider
case $CLOUD_PROVIDER in
    aws)
        echo "Deploying to AWS using CloudFormation..."
        aws cloudformation deploy \
            --template-file cloudformation/pqc-ecs-stack.yaml \
            --stack-name pqc-secure-transfer-$ENVIRONMENT \
            --parameter-overrides \
                Environment=$ENVIRONMENT \
                InstanceCount=$INSTANCE_COUNT \
                InstanceSize=$INSTANCE_SIZE \
            --capabilities CAPABILITY_IAM
        ;;
    gcp)
        echo "Deploying to GCP using Terraform..."
        cd terraform/environments/$ENVIRONMENT
        terraform init
        terraform plan -var="cloud_provider=gcp" -var="image_tag=$IMAGE_TAG"
        terraform apply -auto-approve -var="cloud_provider=gcp" -var="image_tag=$IMAGE_TAG"
        cd -
        ;;
    azure)
        echo "Deploying to Azure using Terraform..."
        cd terraform/environments/$ENVIRONMENT
        terraform init
        terraform plan -var="cloud_provider=azure" -var="image_tag=$IMAGE_TAG"
        terraform apply -auto-approve -var="cloud_provider=azure" -var="image_tag=$IMAGE_TAG"
        cd -
        ;;
esac

echo "Deployment completed successfully!"
echo "Run './scripts/health-check.sh $ENVIRONMENT' to verify deployment"