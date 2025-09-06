@echo off
setlocal EnableDelayedExpansion
title DEBUG - AutomationBot Startup
color 0E
cls

echo ===============================================================================
echo                    DEBUG MODE - AUTOMATIONBOT STARTUP TEST
echo ===============================================================================
echo.
echo This debug script will show exactly what happens during startup.
echo Press any key to continue...
pause >nul

echo.
echo [DEBUG] Current directory: %CD%
echo [DEBUG] Script location: %~dp0
echo.

echo [TEST 1] Changing to script directory...
cd /d "%~dp0"
echo [DEBUG] New directory: %CD%
echo.

echo [TEST 2] Checking if files exist...
if exist "enhanced_comprehensive_viewer.py" (
    echo [PASS] enhanced_comprehensive_viewer.py EXISTS
) else (
    echo [FAIL] enhanced_comprehensive_viewer.py NOT FOUND
)

if exist "api\simple_modular_routes.py" (
    echo [PASS] api\simple_modular_routes.py EXISTS
) else (
    echo [FAIL] api\simple_modular_routes.py NOT FOUND
)
echo.

echo [TEST 3] Testing Python commands...
echo [DEBUG] Testing 'python --version'...
python --version 2>&1
set PYTHON_ERROR=!errorlevel!
echo [DEBUG] Error level: !PYTHON_ERROR!
echo.

if !PYTHON_ERROR! equ 0 (
    echo [PASS] Python command works
    set "PYTHON_CMD=python"
) else (
    echo [DEBUG] Testing 'py --version'...
    py --version 2>&1
    set PY_ERROR=!errorlevel!
    echo [DEBUG] Error level: !PY_ERROR!
    
    if !PY_ERROR! equ 0 (
        echo [PASS] Py command works
        set "PYTHON_CMD=py"
    ) else (
        echo [FAIL] No working Python command found
        echo.
        pause
        exit /b 1
    )
)

echo.
echo [TEST 4] Testing module imports...
echo [DEBUG] Testing tkinter import...
!PYTHON_CMD! -c "import tkinter; print('tkinter OK')" 2>&1
echo [DEBUG] Tkinter error level: !errorlevel!

echo [DEBUG] Testing backend module import...
!PYTHON_CMD! -c "from api.simple_modular_routes import create_simple_modular_app; print('Backend module OK')" 2>&1
echo [DEBUG] Backend error level: !errorlevel!

echo.
echo [TEST 5] All tests completed - ready to try startup
echo.
echo If all tests show [PASS], then double-click START_TRADING_VIEWER.bat
echo If any test shows [FAIL], that's the problem that needs to be fixed.
echo.
pause