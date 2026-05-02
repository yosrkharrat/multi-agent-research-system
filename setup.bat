@echo off
REM Multi-Agent Research System - Quick Start Script (Windows)
REM This script checks prerequisites and helps you run the system

setlocal enabledelayedexpansion

echo.
echo ============================================================
echo  Multi-Agent Research System - Windows Setup Helper
echo ============================================================
echo.

REM Check Python
echo [1/3] Checking Python installation...
py --version >nul 2>&1
if !errorlevel! neq 0 (
    echo   ❌ Python not found! Please install Python 3.10+
    echo   Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('py --version 2^>^&1') do set PYVER=%%i
echo   ✅ Python %PYVER% found

REM Check Ollama
echo.
echo [2/3] Checking Ollama installation...
ollama --version >nul 2>&1
if !errorlevel! neq 0 (
    echo   ❌ Ollama not found!
    echo   Download from: https://ollama.ai/download
    echo   Or install via winget: winget install --id Ollama.Ollama -e
    echo.
    echo   After installing Ollama, run it in a separate terminal:
    echo   $ ollama serve
    pause
    exit /b 1
)
echo   ✅ Ollama found

REM Check if Ollama is running
echo.
echo [3/3] Checking if Ollama server is running on localhost:11434...
timeout /t 1 /nobreak >nul
curl -s http://localhost:11434/api/tags >nul 2>&1
if !errorlevel! neq 0 (
    echo.
    echo   ⚠️  Ollama server is NOT running!
    echo.
    echo   To use this system, you MUST have Ollama running in a separate terminal.
    echo.
    echo   Open a new PowerShell window and run:
    echo   $ ollama serve
    echo.
    echo   Then come back and run this script again.
    echo.
    pause
    exit /b 1
)
echo   ✅ Ollama server is running

REM Check models
echo.
echo Checking for required models...
ollama list | findstr mistral >nul 2>&1
if !errorlevel! neq 0 (
    echo   ⚠️  Model 'mistral' not found. Pulling it now...
    ollama pull mistral
)

REM All checks passed
echo.
echo ============================================================
echo   All checks passed! System is ready to run.
echo ============================================================
echo.
echo Choose what to do:
echo   1) Run quick test (5-10 min)
echo   2) Start API server (http://localhost:8002)
echo   3) Exit
echo.

set /p choice="Enter your choice (1-3): "

if "%choice%"=="1" (
    echo.
    echo Running quick test...
    set PYTHONPATH=src
    py test_quick.py
) else if "%choice%"=="2" (
    echo.
    echo Starting API server on http://localhost:8002
    echo Press Ctrl+C to stop
    echo.
    set PYTHONPATH=src
    py run.py
) else (
    echo Exiting.
)

endlocal
pause
