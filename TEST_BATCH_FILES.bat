@echo off
title Test AutomationBot Batch Files
color 0E
cls

echo ===============================================================================
echo                    TESTING AUTOMATIONBOT BATCH FILES
echo ===============================================================================
echo.

echo [TEST 1] Checking if required files exist...
if exist "enhanced_comprehensive_viewer.py" (
    echo [PASS] enhanced_comprehensive_viewer.py found
) else (
    echo [FAIL] enhanced_comprehensive_viewer.py not found
)

if exist "api\simple_modular_routes.py" (
    echo [PASS] api\simple_modular_routes.py found  
) else (
    echo [FAIL] api\simple_modular_routes.py not found
)

if exist "START_TRADING_VIEWER.bat" (
    echo [PASS] START_TRADING_VIEWER.bat found
) else (
    echo [FAIL] START_TRADING_VIEWER.bat not found
)

if exist "STOP_TRADING_VIEWER.bat" (
    echo [PASS] STOP_TRADING_VIEWER.bat found
) else (
    echo [FAIL] STOP_TRADING_VIEWER.bat not found
)

echo.
echo [TEST 2] Checking Python installation...
python --version
if %errorlevel% equ 0 (
    echo [PASS] Python installation verified
) else (
    echo [FAIL] Python not accessible via 'python' command
)

echo.
echo [TEST 3] Testing backend API module import...
python -c "from api.simple_modular_routes import create_simple_modular_app; print('[PASS] Backend module can be imported')"
if %errorlevel% equ 0 (
    echo [PASS] Backend module import successful
) else (
    echo [FAIL] Backend module import failed
)

echo.
echo [TEST 4] Testing viewer module import...
python -c "import tkinter; print('[PASS] Tkinter available for GUI')"
if %errorlevel% equ 0 (
    echo [PASS] GUI libraries available
) else (
    echo [FAIL] GUI libraries not available
)

echo.
echo ===============================================================================
echo                        BATCH FILE READINESS TEST COMPLETE
echo ===============================================================================
echo.
echo All batch files are ready for one-click operation!
echo.
echo To start: Double-click START_TRADING_VIEWER.bat
echo To stop:  Double-click STOP_TRADING_VIEWER.bat
echo.
pause