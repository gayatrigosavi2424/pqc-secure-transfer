# Simple PQC deployment test
Write-Host "🚀 Testing PQC Secure Transfer Deployment" -ForegroundColor Green

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
    Write-Host "✅ PQC service responded" -ForegroundColor Green
    Write-Host "Response: $healthResponse" -ForegroundColor Cyan
} catch {
    Write-Host "❌ PQC service health check failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Show service URLs
Write-Host "`n🌐 Service URLs:" -ForegroundColor Green
Write-Host "   PQC Service: http://localhost:8765" -ForegroundColor Cyan
Write-Host "   Prometheus: http://localhost:9091" -ForegroundColor Cyan
Write-Host "   Grafana: http://localhost:3000" -ForegroundColor Cyan

Write-Host "`n🎯 Test completed!" -ForegroundColor Green