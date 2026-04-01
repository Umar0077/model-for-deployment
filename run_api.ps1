# FastAPI Emotion Detection Server - Run Script
# This script activates the virtual environment, installs dependencies, and runs the server

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Emotion Detection API Server" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Activate virtual environment if it exists
if (Test-Path ".venv\Scripts\Activate.ps1") {
    Write-Host "[1/3] Activating virtual environment..." -ForegroundColor Yellow
    & .venv\Scripts\Activate.ps1
    Write-Host "✓ Virtual environment activated" -ForegroundColor Green
} else {
    Write-Host "[1/3] No virtual environment found, using global Python" -ForegroundColor Yellow
}

Write-Host ""

# Install/upgrade requirements
Write-Host "[2/3] Installing/updating dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt --quiet
Write-Host "✓ Dependencies ready" -ForegroundColor Green

Write-Host ""

# Get local IP address for mobile testing
Write-Host "[3/3] Starting FastAPI server..." -ForegroundColor Yellow
$ipAddress = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.InterfaceAlias -like "*Wi-Fi*" -or $_.InterfaceAlias -like "*Ethernet*"} | Select-Object -First 1).IPAddress

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Server Starting!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Local URL:    http://localhost:8000" -ForegroundColor White
Write-Host "Network URL:  http://${ipAddress}:8000" -ForegroundColor White
Write-Host "API Docs:     http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "Mobile Testing:" -ForegroundColor Yellow
Write-Host "  Use http://${ipAddress}:8000 from your phone" -ForegroundColor White
Write-Host "  Health check: http://${ipAddress}:8000/health" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Optional: Set API key for testing (uncomment to enable)
# $env:API_KEY = "your-secret-key-here"
# Write-Host "API Key enabled: $env:API_KEY" -ForegroundColor Yellow

# Run uvicorn with hot reload for development
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
