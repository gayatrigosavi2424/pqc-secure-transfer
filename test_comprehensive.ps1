# Comprehensive Testing Script for PQC Secure Transfer System
Write-Host "🧪 Comprehensive PQC System Testing" -ForegroundColor Green
Write-Host "=" * 50

# Test 1: Health Check
Write-Host "`n1️⃣ Testing System Health..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8765/health" -Method Get
    Write-Host "✅ Health Status: $($health.status)" -ForegroundColor Green
    Write-Host "   Algorithm: $($health.pqc_algorithm)" -ForegroundColor Cyan
    Write-Host "   Uptime: $($health.uptime) seconds" -ForegroundColor Cyan
} catch {
    Write-Host "❌ Health check failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 2: PQC Performance Test
Write-Host "`n2️⃣ Testing PQC Performance..." -ForegroundColor Yellow
$pqcTimes = @()
for ($i = 1; $i -le 10; $i++) {
    try {
        $startTime = Get-Date
        $result = Invoke-RestMethod -Uri "http://localhost:8765/test-pqc" -Method Post
        $endTime = Get-Date
        $duration = ($endTime - $startTime).TotalMilliseconds
        $pqcTimes += $duration
        Write-Host "   Test $i`: $([math]::Round($duration, 2))ms" -ForegroundColor Cyan
    } catch {
        Write-Host "   Test $i`: Failed" -ForegroundColor Red
    }
}

# Calculate statistics
$avgTime = ($pqcTimes | Measure-Object -Average).Average
$minTime = ($pqcTimes | Measure-Object -Minimum).Minimum
$maxTime = ($pqcTimes | Measure-Object -Maximum).Maximum

Write-Host "`n📊 PQC Performance Results:" -ForegroundColor Green
Write-Host "   Average: $([math]::Round($avgTime, 2))ms" -ForegroundColor Cyan
Write-Host "   Minimum: $([math]::Round($minTime, 2))ms" -ForegroundColor Cyan
Write-Host "   Maximum: $([math]::Round($maxTime, 2))ms" -ForegroundColor Cyan

# Test 3: Metrics Collection
Write-Host "`n3️⃣ Testing Metrics Collection..." -ForegroundColor Yellow
try {
    $metrics = Invoke-WebRequest -Uri "http://localhost:8765/metrics" -UseBasicParsing
    if ($metrics.StatusCode -eq 200) {
        Write-Host "✅ Metrics endpoint accessible" -ForegroundColor Green
        $metricsContent = $metrics.Content
        if ($metricsContent -match "pqc_server_uptime_seconds") {
            Write-Host "✅ PQC-specific metrics available" -ForegroundColor Green
        }
    }
} catch {
    Write-Host "❌ Metrics test failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 4: Monitoring Systems
Write-Host "`n4️⃣ Testing Monitoring Systems..." -ForegroundColor Yellow

# Test Prometheus
try {
    $prometheus = Invoke-WebRequest -Uri "http://localhost:9091" -UseBasicParsing -TimeoutSec 5
    if ($prometheus.StatusCode -eq 200) {
        Write-Host "✅ Prometheus accessible" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Prometheus test failed" -ForegroundColor Red
}

# Test Grafana
try {
    $grafana = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -TimeoutSec 5
    if ($grafana.StatusCode -eq 200) {
        Write-Host "✅ Grafana accessible" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Grafana test failed" -ForegroundColor Red
}

# Test 5: Load Testing
Write-Host "`n5️⃣ Load Testing (50 concurrent requests)..." -ForegroundColor Yellow
$jobs = @()
$startTime = Get-Date

for ($i = 1; $i -le 50; $i++) {
    $job = Start-Job -ScriptBlock {
        try {
            Invoke-RestMethod -Uri "http://localhost:8765/test-pqc" -Method Post -TimeoutSec 30
            return "Success"
        } catch {
            return "Failed"
        }
    }
    $jobs += $job
}

# Wait for all jobs to complete
$results = $jobs | Wait-Job | Receive-Job
$endTime = Get-Date
$totalTime = ($endTime - $startTime).TotalSeconds

$successCount = ($results | Where-Object { $_ -eq "Success" }).Count
$failCount = ($results | Where-Object { $_ -eq "Failed" }).Count

Write-Host "`n📈 Load Test Results:" -ForegroundColor Green
Write-Host "   Total Requests: 50" -ForegroundColor Cyan
Write-Host "   Successful: $successCount" -ForegroundColor Cyan
Write-Host "   Failed: $failCount" -ForegroundColor Cyan
Write-Host "   Total Time: $([math]::Round($totalTime, 2)) seconds" -ForegroundColor Cyan
Write-Host "   Throughput: $([math]::Round(50/$totalTime, 2)) requests/second" -ForegroundColor Cyan

# Cleanup jobs
$jobs | Remove-Job

Write-Host "`n🎯 Testing Complete!" -ForegroundColor Green
Write-Host "📊 Results Summary:" -ForegroundColor Yellow
Write-Host "   PQC Average Response: $([math]::Round($avgTime, 2))ms" -ForegroundColor Cyan
Write-Host "   Load Test Success Rate: $([math]::Round(($successCount/50)*100, 1))%" -ForegroundColor Cyan
Write-Host "   System Throughput: $([math]::Round(50/$totalTime, 2)) req/sec" -ForegroundColor