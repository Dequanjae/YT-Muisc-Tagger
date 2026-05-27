@echo off
title Music Suite 2-in-1
echo ========================================
echo   Launching Music Suite 2-in-1...
echo ========================================
echo.

REM ---- Navigate to script's own directory ----
cd /d "%~dp0"

REM ---- Check for Python ----
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Python is not installed or not in your PATH.
    echo Download it from: https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during install.
    echo.
    pause
    exit /b 1
)
echo Using Python:
python --version

REM ---- Check for FFmpeg ----
where ffmpeg >nul 2>nul
if %errorlevel% neq 0 (
    echo.
    echo WARNING: ffmpeg is not installed or not in your PATH.
    echo   Downloading and format conversion will not work without it.
    echo   Download from: https://www.gyan.dev/ffmpeg/builds/
    echo.
)

REM ---- Create & activate virtual environment ----
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)
call .venv\Scripts\activate.bat

REM ---- Install / update dependencies ----
echo Checking dependencies...
pip install -r requirements.txt --quiet --upgrade

REM ---- Launch the app ----
echo.
echo Starting server and opening browser...
echo   -^> http://localhost:8000
echo.
python combined_app.py

echo.
echo Server stopped.
pause
