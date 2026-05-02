@echo off
REM Download and install Ollama automatically
REM Right-click and select "Run as administrator"

echo.
echo ============================================================
echo  Installing Ollama for Windows
echo ============================================================
echo.

REM Check if already installed
if exist "%ProgramFiles%\Ollama\ollama.exe" (
    echo ✅ Ollama is already installed!
    pause
    exit /b 0
)

REM Download
set DOWNLOAD_URL=https://ollama.ai/download/OllamaSetup.exe
set INSTALLER=%TEMP%\OllamaSetup.exe

echo Downloading Ollama installer from:
echo %DOWNLOAD_URL%
echo.

powershell -Command "(New-Object System.Net.WebClient).DownloadFile('%DOWNLOAD_URL%', '%INSTALLER%')"

if not exist "%INSTALLER%" (
    echo.
    echo ❌ Failed to download Ollama installer
    echo.
    echo Alternative: Download manually from https://ollama.ai/download
    echo.
    pause
    exit /b 1
)

echo ✅ Download complete
echo.
echo Installing Ollama...
echo.

REM Run installer silently
"%INSTALLER%" /S

REM Wait for installation
echo Waiting for installation...
timeout /t 30 /nobreak >nul

REM Verify
if exist "%ProgramFiles%\Ollama\ollama.exe" (
    echo.
    echo ✅ Ollama installed successfully!
    echo.
    echo Installation path: %ProgramFiles%\Ollama
    echo.
    del /f /q "%INSTALLER%" 2>nul
    echo Next step: Run start-ollama.bat
    echo.
    pause
    exit /b 0
) else (
    echo.
    echo ❌ Installation verification failed
    echo.
    echo Please download manually from: https://ollama.ai/download
    echo.
    pause
    exit /b 1
)
