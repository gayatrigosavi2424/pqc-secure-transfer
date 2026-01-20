# Comprehensive Testing Script for PQC Secure Transfer System
Write-Host "Testing PQC System Comprehensively" -ForegroundColor Green
Write-Host "=" * 50

# Test 1: Health Check
Write-Host "`nTest 1: System Health..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8765/health" -Method Get
    Write-Host "Health Status: $($health.status)" -ForegroundColor Green
    Write-Host "Algorithm: $($health.pqc_algorithm)" -ForegroundColor Cyan
    Write-Host "Uptime: $($health.uptime) seconds" -ForegroundColor Cyan
} catch {
    Write-Host "Health check failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 2: PQC Performance Test
Write-Host "`nTest 2: PQC Performance (10 tests)..." -ForegroundColor Yellow
$pqcTimes = @()
for ($i = 1; $i -le 10; $i++) {
    try {
        $startTime = Get-Date
        $result = Invoke-RestMethod -Uri "http://localhost:8765/test-pqc" -Method Post
        $endTime = Get-Date
        $duration = ($endTime - $startTime).TotalMilliseconds
        $pqcTimes += $duration
        Write-Host "Test $i : $([math]::Round($duration, 2))ms" -ForegroundColor Cyan
    } catch {
        Write-Host "Test $i : Failed" -ForegroundColor Red
    }
}

# Calculate statistics
if ($pqcTimes.Count -gt 0) {
    $avgTime = ($pqcTimes | Measure-Object -Average).Average
    $minTime = ($pqcTimes | Measure-Object -Minimum).Minimum
    $maxTime = ($pqcTimes | Measure-Object -Maximum).Maximum

    Write-Host "`nPQC Performance Results:" -ForegroundColor Green
    Write-Host "Average: $([math]::Round($avgTime, 2))ms" -ForegroundColor Cyan
    Write-Host "Minimum: $([math]::Round($minTime, 2))ms" -ForegroundColor Cyan
    Write-Host "Maximum: $([math]::Round($maxTime, 2))ms" -ForegroundColor Cyan
}

# Test 3: Metrics Collection
Write-Host "`nTest 3: Metrics Collection..." -ForegroundColor Yellow
try {
    $metrics = Invoke-WebRequest -Uri "http://localhost:8765/metrics" -UseBasicParsing
    if ($metrics.StatusCode -eq 200) {
        Write-Host "Metrics endpoint accessible" -ForegroundColor Green
    }
} catch {
    Write-Host "Metrics test failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 4: Monitoring Systems
Write-Host "`nTest 4: Monitoring Systems..." -ForegroundColor Yellow

# Test Prometheus
try {
    $prometheus = Invoke-WebRequest -Uri "http://localhost:9091" -UseBasicParsing -TimeoutSec 5
    if ($prometheus.StatusCode -eq 200) {
        Write-Host "Prometheus accessible" -ForegroundColor Green
    }
} catch {
    Write-Host "Prometheus test failed" -ForegroundColor Red
}

# Test Grafana
try {
    $grafana = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -TimeoutSec 5
    if ($grafana.StatusCode -eq 200) {
        Write-Host "Grafana accessible" -ForegroundColor Green
    }
} catch {
    Write-Host "Grafana test failed" -ForegroundColor Red
}

Write-Host "`nTesting Complete!" -ForegroundColor Green