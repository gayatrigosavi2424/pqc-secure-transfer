# PowerShell script to test the PQC deployment locally
param(
    [string]$Environment = "dev"
)

Write-Host "🚀 Testing PQC Secure Transfer Deployment - $Environment Environment" -ForegroundColor Green

# Check if Docker is running
try {
    docker version | Out-Null
    Write-Host "✅ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}

# Start the services
Write-Host "🔄 Starting PQC services..." -ForegroundColor Yellow
docker-compose -f docker-compose.dev.yml up -d

# Wait for services to be ready
Write-Host "⏳ Waiting for services to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

# Test PQC service health
Write-Host "🏥 Testing PQC service health..." -ForegroundColor Yellow
try {
    $healthResponse = Invoke-RestMethod -Uri "http://localhost:8765/health" -Method Get -TimeoutSec 10
    if ($healthResponse.status -eq "healthy") {
        Write-Host "✅ PQC service is healthy" -ForegroundColor Green
        Write-Host "   Algorithm: $($healthResponse.pqc_algorithm)" -ForegroundColor Cyan
        Write-Host "   Version: $($healthResponse.version)" -ForegroundColor Cyan
    } else {
        Write-Host "⚠️  PQC service health check returned: $($healthResponse.status)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ PQC service health check failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test metrics endpoint
Write-Host "📊 Testing metrics endpoint..." -ForegroundColor Yellow
try {
    $metricsResponse = Invoke-WebRequest -Uri "http://localhost:9090/metrics" -Method Get -TimeoutSec 10
    if ($metricsResponse.StatusCode -eq 200) {
        Write-Host "✅ Metrics endpoint is accessible" -ForegroundColor Green
        $metricsContent = $metricsResponse.Content
        if ($metricsContent -match "pqc_key_exchanges_total") {
            Write-Host "✅ PQC-specific metrics are available" -ForegroundColor Green
        } else {
            Write-Host "⚠️  PQC-specific metrics not found" -ForegroundColor Yellow
        }
    }
} catch {
    Write-Host "❌ Metrics endpoint test failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test Prometheus
Write-Host "📈 Testing Prometheus..." -ForegroundColor Yellow
try {
    $prometheusResponse = Invoke-WebRequest -Uri "http://localhost:9091" -Method Get -TimeoutSec 10
    if ($prometheusResponse.StatusCode -eq 200) {
        Write-Host "✅ Prometheus is accessible at http://localhost:9091" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Prometheus test failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test Grafana
Write-Host "📊 Testing Grafana..." -ForegroundColor Yellow
try {
    $grafanaResponse = Invoke-WebRequest -Uri "http://localhost:3000" -Method Get -TimeoutSec 10
    if ($grafanaResponse.StatusCode -eq 200) {
        Write-Host "✅ Grafana is accessible at http://localhost:3000" -ForegroundColor Green
        Write-Host "   Login: admin/admin" -ForegroundColor Cyan
    }
} catch {
    Write-Host "❌ Grafana test failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Performance test
Write-Host "⚡ Running performance test..." -ForegroundColor Yellow
try {
    # Test PQC key exchange performance
    $startTime = Get-Date
    for ($i = 1; $i -le 5; $i++) {
        $testResponse = Invoke-RestMethod -Uri "http://localhost:8765/test-pqc" -Method Post -TimeoutSec 30
        Write-Host "   Test $i completed" -ForegroundColor Cyan
    }
    $endTime = Get-Date
    $duration = ($endTime - $startTime).TotalSeconds
    $throughput = 5 / $duration
    
    Write-Host "✅ Performance test completed" -ForegroundColor Green
    Write-Host "   Operations: 5 PQC key exchanges" -ForegroundColor Cyan
    Write-Host "   Duration: $([math]::Round($duration, 2)) seconds" -ForegroundColor Cyan
    Write-Host "   Throughput: $([math]::Round($throughput, 2)) ops/sec" -ForegroundColor Cyan
    
    if ($throughput -gt 1.0) {
        Write-Host "✅ Performance meets requirements" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Performance below expected threshold" -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ Performance test failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Show service URLs
Write-Host "`n🌐 Service URLs:" -ForegroundColor Green
Write-Host "   PQC Service: http://localhost:8765" -ForegroundColor Cyan
Write-Host "   Metrics: http://localhost:9090/metrics" -ForegroundColor Cyan
Write-Host "   Prometheus: http://localhost:9091" -ForegroundColor Cyan
Write-Host "   Grafana: http://localhost:3000 (admin/admin)" -ForegroundColor Cyan
Write-Host "   Alertmanager: http://localhost:9093" -ForegroundColor Cyan

Write-Host "`n🎯 Deployment test completed!" -ForegroundColor Green
Write-Host "To stop services: docker-compose -f docker-compose.dev.yml down" -ForegroundColor Yellow