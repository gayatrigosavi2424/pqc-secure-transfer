#!/bin/bash

# Health check script for PQC Secure Transfer deployment
set -e

ENVIRONMENT=${1:-dev}
TIMEOUT=${2:-300}

echo "Performing health check for $ENVIRONMENT environment..."

# Get service endpoint based on environment
case $ENVIRONMENT in
    dev)
        SERVICE_URL="http://localhost:8765"
        ;;
    staging)
        SERVICE_URL=$(aws cloudformation describe-stacks \
            --stack-name pqc-secure-transfer-staging \
            --query 'Stacks[0].Outputs[?OutputKey==`ServiceEndpoint`].OutputValue' \
            --output text 2>/dev/null || echo "")
        ;;
    prod)
        SERVICE_URL=$(aws cloudformation describe-stacks \
            --stack-name pqc-secure-transfer-prod \
            --query 'Stacks[0].Outputs[?OutputKey==`ServiceEndpoint`].OutputValue' \
            --output text 2>/dev/null || echo "")
        ;;
esac

if [ -z "$SERVICE_URL" ]; then
    echo "Error: Could not determine service URL for environment $ENVIRONMENT"
    exit 1
fi

echo "Service URL: $SERVICE_URL"

# Wait for service to be ready
echo "Waiting for service to be ready (timeout: ${TIMEOUT}s)..."
start_time=$(date +%s)

while true; do
    current_time=$(date +%s)
    elapsed=$((current_time - start_time))
    
    if [ $elapsed -gt $TIMEOUT ]; then
        echo "Error: Health check timed out after ${TIMEOUT}s"
        exit 1
    fi
    
    # Check health endpoint
    if curl -f -s "$SERVICE_URL/health" > /dev/null 2>&1; then
        echo "✓ Health check passed"
        break
    else
        echo "Waiting for service... (${elapsed}s elapsed)"
        sleep 5
    fi
done

# Perform detailed health checks
echo "Performing detailed health checks..."

# Check health endpoint response
HEALTH_RESPONSE=$(curl -s "$SERVICE_URL/health" || echo "")
if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
    echo "✓ Service reports healthy status"
else
    echo "✗ Service health check failed"
    echo "Response: $HEALTH_RESPONSE"
    exit 1
fi

# Check PQC algorithm configuration
if echo "$HEALTH_RESPONSE" | grep -q "Kyber768"; then
    echo "✓ PQC algorithm configured correctly"
else
    echo "✗ PQC algorithm not configured properly"
    exit 1
fi

echo "All health checks passed successfully!"
echo "Service is ready at: $SERVICE_URL"