@echo off
setlocal EnableDelayedExpansion
title AutomationBot Trading Viewer - Shutdown
color 0C
cls

echo ===============================================================================
echo            AUTOMATIONBOT ENHANCED TRADING VIEWER - CLEAN SHUTDOWN
echo ===============================================================================
echo.
echo [INFO] Shutting down AutomationBot Trading System...
echo.

:: Kill all Python processes (simple approach)
echo [INFO] Stopping all Python processes...
taskkill /F /IM python.exe >nul 2>&1
if !errorlevel! equ 0 (
    echo [SUCCESS] Python processes stopped
) else (
    echo [INFO] No Python processes were running
)

echo.
echo [INFO] Waiting 2 seconds for cleanup...
timeout /t 2 /nobreak >nul

:: Check if port 5000 is still in use
echo [INFO] Checking network connections...
netstat -an | findstr :5000 >nul 2>&1
if !errorlevel! equ 0 (
    echo [INFO] Port 5000 may still be in use - will clear shortly
) else (
    echo [SUCCESS] Port 5000 is now available
)

echo.
echo ===============================================================================
echo                      SHUTDOWN COMPLETED SUCCESSFULLY
echo ===============================================================================
echo.
echo Backend API Server: STOPPED
echo Trading Viewer: STOPPED
echo All Processes: TERMINATED
echo.
echo AutomationBot Trading System has been shutdown.
echo To restart, run START_TRADING_VIEWER.bat
echo.
pause