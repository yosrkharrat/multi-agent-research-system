# Multi-Agent Research System - Start Ollama (PowerShell)
# Run this script to install and start Ollama

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "============================================================"
Write-Host "  Starting Ollama for Multi-Agent Research System"
Write-Host "============================================================"
Write-Host ""

# Check if Ollama is already running
Write-Host "Checking if Ollama is already running..."
try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -ErrorAction SilentlyContinue -TimeoutSec 2
    Write-Host "✅ Ollama is already running on localhost:11434"
    Write-Host "Skipping installation"
    $ollama_running = $true
} catch {
    $ollama_running = $false
}

# Check if Ollama is installed
$ollama_path = "$env:ProgramFiles\Ollama\ollama.exe"
$ollama_installed = Test-Path $ollama_path

if (-not $ollama_installed) {
    Write-Host ""
    Write-Host "❌ Ollama is not installed."
    Write-Host ""
    Write-Host "Installation required. You have two options:"
    Write-Host ""
    Write-Host "Option 1: Download installer (recommended)"
    Write-Host "  → Visit https://ollama.ai/download"
    Write-Host "  → Download 'Ollama-0.x.x-windows.exe'"
    Write-Host "  → Run the installer"
    Write-Host "  → Run this script again"
    Write-Host ""
    Write-Host "Option 2: Install via winget"
    Write-Host "  $ winget install --id Ollama.Ollama -e"
    Write-Host ""
    Read-Host "Press Enter after installing Ollama"
    exit 1
}

Write-Host "✅ Ollama found at $ollama_path"

if (-not $ollama_running) {
    Write-Host ""
    Write-Host "Starting Ollama server..."
    Write-Host ""
    
    # Start Ollama in background
    Start-Process $ollama_path -ArgumentList "serve"
    
    # Wait for Ollama to be ready
    Write-Host "Waiting for Ollama to initialize (this may take 30 seconds)..."
    $retries = 0
    $max_retries = 15
    
    while ($retries -lt $max_retries) {
        Start-Sleep -Seconds 2
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -ErrorAction SilentlyContinue -TimeoutSec 2
            Write-Host "✅ Ollama server is ready!"
            break
        } catch {
            $retries++
        }
    }
    
    if ($retries -eq $max_retries) {
        Write-Host ""
        Write-Host "❌ Ollama failed to start. Please:"
        Write-Host "  1. Check if port 11434 is already in use"
        Write-Host "  2. Check Ollama installation"
        Write-Host "  3. Try running manually:"
        Write-Host "     & '$ollama_path' serve"
        Read-Host "Press Enter to exit"
        exit 1
    }
}

# Check for models
Write-Host ""
Write-Host "Checking for required models..."

$models = & ollama list 2>$null
if ($models -notmatch "mistral") {
    Write-Host ""
    Write-Host "⚠️  Model 'mistral' not found. Pulling it now..."
    Write-Host "This will download ~7GB. Please wait..."
    Write-Host ""
    
    & ollama pull mistral
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "❌ Failed to pull mistral model"
        Read-Host "Press Enter to exit"
        exit 1
    }
}

Write-Host ""
Write-Host "✅ All models ready!"
Write-Host ""
Write-Host "============================================================"
Write-Host "  ✅ Ollama is ready to use!"
Write-Host "  Keep this window open while running the research system"
Write-Host "============================================================"
Write-Host ""
Write-Host "Press Ctrl+C to stop Ollama"
Write-Host ""

# Keep running
while ($true) {
    Start-Sleep -Seconds 300
}
