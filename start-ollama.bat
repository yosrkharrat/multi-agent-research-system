@echo off
REM Multi-Agent Research System - Start Ollama
REM Downloads, installs, and starts Ollama if needed

echo.
echo ============================================================
echo  Starting Ollama for Multi-Agent Research System
echo ============================================================
echo.

REM Check if Ollama is already running
echo Checking if Ollama is already running...
curl -s http://localhost:11434/api/tags >nul 2>&1
if !errorlevel! equ 0 (
    echo ✅ Ollama is already running on localhost:11434
    echo Skipping installation
    goto CHECK_MODELS
)

REM Check if Ollama is installed
if not exist "%ProgramFiles%\Ollama\ollama.exe" (
    echo.
    echo ❌ Ollama is not installed.
    echo.
    echo Installation required. You have two options:
    echo.
    echo Option 1: Download installer (recommended)
    echo   → Visit https://ollama.ai/download
    echo   → Download "Ollama-0.x.x-windows.exe"
    echo   → Run the installer
    echo   → Run this script again
    echo.
    echo Option 2: Install via winget
    echo   $ winget install --id Ollama.Ollama -e
    echo.
    pause
    exit /b 1
)

echo ✅ Ollama found at %ProgramFiles%\Ollama

REM Start Ollama
echo.
echo Starting Ollama server...
echo.
start "" "%ProgramFiles%\Ollama\ollama.exe" serve

REM Wait for Ollama to start
echo.
echo Waiting for Ollama to initialize (this may take 30 seconds)...
set RETRY=0
:WAIT_LOOP
timeout /t 2 /nobreak >nul
curl -s http://localhost:11434/api/tags >nul 2>&1
if !errorlevel! equ 0 (
    echo ✅ Ollama server is ready!
    goto CHECK_MODELS
)
set /a RETRY=!RETRY!+1
if !RETRY! lss 15 goto WAIT_LOOP

echo.
echo ❌ Ollama failed to start. Please:
echo   1. Check if port 11434 is already in use
echo   2. Check Ollama installation
echo   3. Try running manually: "%ProgramFiles%\Ollama\ollama.exe" serve
pause
exit /b 1

:CHECK_MODELS
echo.
echo Checking for required models...
ollama list | findstr mistral >nul 2>&1
if !errorlevel! neq 0 (
    echo.
    echo ⚠️  Model 'mistral' not found. Pulling it now...
    echo This will download ~7GB. Please wait...
    echo.
    ollama pull mistral
    if !errorlevel! neq 0 (
        echo.
        echo ❌ Failed to pull mistral model
        pause
        exit /b 1
    )
)

echo.
echo ✅ All models ready!
echo.
echo ============================================================
echo  Ollama is ready to use!
echo  Keep this window open while running the research system
echo ============================================================
echo.

REM Keep window open
echo Press Ctrl+C to stop Ollama
:KEEP_RUNNING
timeout /t 300 /nobreak >nul
goto KEEP_RUNNING
