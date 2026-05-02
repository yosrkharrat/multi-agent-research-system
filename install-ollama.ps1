# Download and install Ollama automatically
# Run this with: powershell -ExecutionPolicy Bypass -File install-ollama.ps1

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "============================================================"
Write-Host "  Installing Ollama for Windows"
Write-Host "============================================================"
Write-Host ""

# Check if already installed
if (Test-Path "$env:ProgramFiles\Ollama\ollama.exe") {
    Write-Host "✅ Ollama is already installed!"
    exit 0
}

# Download URL
$download_url = "https://ollama.ai/download/OllamaSetup.exe"
$installer = "$env:TEMP\OllamaSetup.exe"

Write-Host "Downloading Ollama installer..."
Write-Host "URL: $download_url"
Write-Host ""

try {
    # Use multiple methods to download
    try {
        # Method 1: WebClient (most compatible)
        $client = New-Object System.Net.WebClient
        $client.DownloadFile($download_url, $installer)
    } catch {
        # Method 2: Invoke-WebRequest (newer PowerShell)
        Invoke-WebRequest -Uri $download_url -OutFile $installer
    }
    
    if (-not (Test-Path $installer)) {
        throw "Failed to download Ollama installer"
    }
    
    Write-Host "✅ Download complete: $installer"
    Write-Host ""
    Write-Host "Installing Ollama..."
    Write-Host ""
    
    # Run installer silently
    & $installer /S
    
    # Wait for installation
    Write-Host "Waiting for installation to complete..."
    Start-Sleep -Seconds 30
    
    # Verify installation
    if (Test-Path "$env:ProgramFiles\Ollama\ollama.exe") {
        Write-Host ""
        Write-Host "✅ Ollama installed successfully!"
        Write-Host ""
        Write-Host "Installation path: $env:ProgramFiles\Ollama"
        Write-Host ""
        
        # Clean up
        Remove-Item $installer -Force -ErrorAction SilentlyContinue
        
        Write-Host "Next step: Run 'powershell -ExecutionPolicy Bypass -File start-ollama.ps1'"
        Write-Host ""
        exit 0
    } else {
        throw "Installation verification failed"
    }
    
} catch {
    Write-Host ""
    Write-Host "❌ Installation failed: $_"
    Write-Host ""
    Write-Host "Alternative installation methods:"
    Write-Host ""
    Write-Host "Option 1: Manual download"
    Write-Host "  → Visit https://ollama.ai/download"
    Write-Host "  → Download 'Ollama-windows' installer"
    Write-Host "  → Run the installer"
    Write-Host ""
    Write-Host "Option 2: Use brew (if installed)"
    Write-Host "  $ brew install ollama"
    Write-Host ""
    Write-Host "Option 3: Use chocolatey (if installed)"
    Write-Host "  $ choco install ollama"
    Write-Host ""
    Read-Host "Press Enter after installing Ollama"
    exit 1
}
