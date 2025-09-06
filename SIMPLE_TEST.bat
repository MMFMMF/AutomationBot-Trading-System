@echo off
echo Simple test starting...
echo Current directory: %CD%
echo.

echo Testing Python...
python --version
echo Error level: %errorlevel%
echo.

echo Testing file existence...
if exist "enhanced_comprehensive_viewer.py" echo VIEWER FILE EXISTS
if exist "api\simple_modular_routes.py" echo BACKEND FILE EXISTS
echo.

echo Testing backend import...
python -c "from api.simple_modular_routes import create_simple_modular_app; print('Import successful')"
echo.

echo Test completed.
pause