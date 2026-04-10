@echo off
echo OER AI Agent - Test
echo.
echo Running test. No API key needed.
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

python test_simple.py
echo.
pause
