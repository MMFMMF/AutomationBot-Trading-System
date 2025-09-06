@echo off
title AutomationBot Comprehensive Trading Viewer
echo.
echo ================================================================
echo  LAUNCHING AUTOMATIONBOT COMPREHENSIVE TRADING VIEWER
echo  SINGLE SOURCE OF TRUTH - NO WEB DEPENDENCY
echo ================================================================
echo.

cd /d "%~dp0"

echo Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found. Please install Python first.
    pause
    exit /b 1
)

echo Installing required packages...
pip install pillow requests >nul 2>&1

echo.
echo Starting Comprehensive Trading Viewer...
echo This is now your SINGLE SOURCE OF TRUTH for trading operations.
echo All functionality is available through this desktop interface.
echo.

python comprehensive_trading_viewer.py

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to start viewer. Check Python installation and dependencies.
    pause
    exit /b 1
)

echo.
echo Viewer closed successfully.
pause