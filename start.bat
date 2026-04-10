@echo off
echo OER AI Agent - Web Application
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

echo Starting web application...
echo Open http://localhost:5000 in your browser
echo.

python app.py
pause
