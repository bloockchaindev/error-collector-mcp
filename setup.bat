@echo off
REM Error Collector MCP - Quick Setup Script (Windows)
REM This script provides a simple way to run the Python setup script on Windows

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                                                              ║
echo ║           🚀 Error Collector MCP - Quick Setup              ║
echo ║                                                              ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is required but not installed.
    echo Please install Python 3.9+ from https://python.org and try again.
    pause
    exit /b 1
)

REM Check Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✅ Python %PYTHON_VERSION% found

REM Run the Python setup script
echo 🚀 Running interactive setup...

REM Check if package is installed
python -c "import error_collector_mcp" >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Package already installed, running configuration setup...
    python quick_setup.py
) else (
    echo 📦 Package not installed, running full setup...
    python setup.py
)

if %errorlevel% equ 0 (
    echo 🎉 Setup complete!
) else (
    echo ❌ Setup failed. Please check the error messages above.
    pause
    exit /b 1
)

pause